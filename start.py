from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Any, Dict
import json
import requests
import xml.etree.ElementTree as ET
import re
import random
import os
from datetime import datetime
from fastapi import UploadFile, File

# ============== APP INITIALIZATION (IMMEDIATE - for fast port binding) ==============
app = FastAPI(title="MedLearn AI", version="2.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("✅ FastAPI app created!")

# ============== LAZY SERVICE INITIALIZATION ==============
# Services are initialized on first use, not at startup
_services = {}

def get_genai():
    if 'genai' not in _services:
        import google.generativeai as genai
        genai.configure(api_key="AIzaSyCYWLN5pGRTQ6FqbV5zWgelThz4bmPUkC4")
        _services['genai'] = genai
        print("✅ Gemini API configured")
    return _services['genai']

def get_model():
    if 'model' not in _services:
        _services['model'] = get_genai().GenerativeModel("gemini-2.0-flash-exp")
        print("✅ Gemini model loaded")
    return _services['model']

def get_skills_ontology():
    if 'skills' not in _services:
        from skills_ontology import SkillsOntology
        _services['skills'] = SkillsOntology()
    return _services['skills']

def get_question_tagger():
    if 'tagger' not in _services:
        from question_tagger import QuestionTagger
        _services['tagger'] = QuestionTagger(get_skills_ontology())
    return _services['tagger']

def get_doc_processor():
    if 'doc' not in _services:
        try:
            from doc_pro import DocumentProcessor
            _services['doc'] = DocumentProcessor()
            print("✅ Document processor ready")
        except Exception as e:
            print(f"⚠️ Doc processor error: {e}")
            _services['doc'] = None
    return _services['doc']

def get_rag_service():
    if 'rag' not in _services:
        try:
            from rag_service import RAGService
            _services['rag'] = RAGService()
            print("✅ RAG service connected")
        except Exception as e:
            print(f"⚠️ RAG service unavailable: {e}")
            _services['rag'] = None
    return _services['rag']

def get_drive_service():
    if 'drive' not in _services:
        try:
            from google_drive import GoogleDriveService
            _services['drive'] = GoogleDriveService()
            print("✅ Google Drive connected")
        except Exception as e:
            print(f"⚠️ Drive unavailable (normal for cloud): {e}")
            _services['drive'] = None
    return _services['drive']

def get_learner_manager():
    if 'learner' not in _services:
        from learner_profile import LearnerProfileManager
        _services['learner'] = LearnerProfileManager()
        print("✅ Learner manager ready")
    return _services['learner']

def get_exam_manager():
    if 'exam' not in _services:
        from exam_session import ExamSessionManager
        _services['exam'] = ExamSessionManager(learner_manager=get_learner_manager())
        print("✅ Exam manager ready")
    return _services['exam']

def get_recommendation_engine():
    if 'rec' not in _services:
        from recommendation_engine import RecommendationEngine
        _services['rec'] = RecommendationEngine(get_learner_manager(), get_skills_ontology())
        print("✅ Recommendation engine ready")
    return _services['rec']

# Backward compatibility aliases (these use lazy loading now)
model = None  # Use get_model()
rag_service = None  # Use get_rag_service()
doc_processor = None  # Use get_doc_processor()
drive_service = None  # Use get_drive_service()
skills_ontology = None  # Use get_skills_ontology()
question_tagger = None  # Use get_question_tagger()
genai = None  # Use get_genai()

# Optimal threshold
RELEVANCE_THRESHOLD = 0.55


# ============== PUBMED HELPER FUNCTIONS (for AI Tutor) ==============
def search_pubmed_articles(search_terms: List[str], max_results: int = 5) -> List[str]:
    """Search PubMed for article IDs - used by AI Tutor"""
    try:
        query = " OR ".join([f'"{term}"[Title/Abstract]' for term in search_terms])
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"PubMed search error: {e}")
    return []


def fetch_pubmed_details(pmids: List[str]) -> List[Dict]:
    """Fetch article details from PubMed - used by AI Tutor"""
    if not pmids:
        return []
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml"
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            articles = []
            for article in root.findall(".//PubmedArticle"):
                try:
                    title_elem = article.find(".//ArticleTitle")
                    abstract_elem = article.find(".//AbstractText")
                    pmid_elem = article.find(".//PMID")
                    articles.append({
                        "pmid": pmid_elem.text if pmid_elem is not None else "",
                        "title": title_elem.text if title_elem is not None else "No title",
                        "abstract": abstract_elem.text if abstract_elem is not None else ""
                    })
                except:
                    continue
            return articles
    except Exception as e:
        print(f"PubMed fetch error: {e}")
    return []


# ============== DIFFICULTY NORMALIZATION ==============
def normalize_difficulty(difficulty: str) -> str:
    """Normalize difficulty input to one of: beginner, intermediate, advanced."""
    d = difficulty.lower().strip()
    
    if d in ["beginner", "easy", "simple", "basic", "novice", "entry", "level1", "level 1", "l1", "1"]:
        return "beginner"
    
    if d in ["intermediate", "medium", "mid", "moderate", "middle", "average", "level2", "level 2", "l2", "2"]:
        return "intermediate"
    
    if d in ["advanced", "hard", "difficult", "tough", "expert", "complex", "challenging", "level3", "level 3", "l3", "3"]:
        return "advanced"
    
    return "intermediate"


# ============== QUESTION TYPE NORMALIZATION ==============
def normalize_question_type(q_type: str) -> str:
    """Normalize question type input."""
    q = q_type.lower().strip()
    
    # Standard multiple choice
    if q in ["mcq", "multiple choice", "multiple-choice", "standard", "traditional"]:
        return "mcq"
    
    # Select All That Apply
    if q in ["sata", "select all", "select-all", "select all that apply", "multiple select"]:
        return "sata"
    
    # Matrix / Grid
    if q in ["matrix", "grid", "table", "matrix multiple choice"]:
        return "matrix"
    
    # Cloze / Drop-down
    if q in ["cloze", "dropdown", "drop-down", "fill in", "fill-in", "drop down cloze"]:
        return "cloze"
    
    # Highlight / Hot spot
    if q in ["highlight", "hotspot", "hot spot", "highlight text"]:
        return "highlight"
    
    # Bowtie (Clinical Judgment)
    if q in ["bowtie", "bow tie", "bow-tie", "clinical judgment"]:
        return "bowtie"
    
    return "mcq"


# ============== RANDOMIZATION FOR DIVERSITY ==============
def get_random_patient_demographics(difficulty: str) -> dict:
    """Generate random patient demographics based on difficulty level."""
    
    age_ranges = {
        "beginner": (22, 40),       # Young adults - fewer comorbidities
        "intermediate": (50, 70),   # Middle-aged to older - chronic disease
        "advanced": (72, 92)        # Elderly/geriatric - complex cases
    }
    
    age_range = age_ranges.get(difficulty, (30, 70))
    age = random.randint(age_range[0], age_range[1])
    gender = random.choice(["male", "female"])
    
    return {"age": age, "gender": gender}


def get_random_clinical_context(difficulty: str) -> dict:
    """Generate random clinical context for scenario diversity."""
    
    locations = {
        "beginner": ["emergency department", "urgent care clinic", "medical-surgical unit", "outpatient clinic"],
        "intermediate": ["emergency department", "medical-surgical unit", "step-down unit", "telemetry unit", "long-term care facility"],
        "advanced": ["intensive care unit (ICU)", "emergency department", "step-down unit", "post-anesthesia care unit (PACU)", "cardiac care unit (CCU)"]
    }
    
    infection_sources = {
        "beginner": ["community-acquired"],
        "intermediate": ["community-acquired", "healthcare-associated"],
        "advanced": ["community-acquired", "healthcare-associated", "hospital-acquired", "ventilator-associated"]
    }
    
    comorbidity_pools = {
        "beginner": [],
        "intermediate": [
            "Type 2 Diabetes Mellitus", "COPD", "Chronic Kidney Disease (Stage 3)",
            "Asthma", "Hypothyroidism", "Obesity (BMI 34)", "Osteoarthritis"
        ],
        "advanced": [
            "Chronic Heart Failure (EF 35%)", "Chronic Kidney Disease (Stage 4)",
            "Type 2 Diabetes Mellitus", "Atrial Fibrillation", "Cirrhosis (Child-Pugh B)",
            "COPD (on home oxygen)", "End-Stage Renal Disease (on dialysis)",
            "Systemic Lupus Erythematosus", "Rheumatoid Arthritis (on immunosuppressants)",
            "Recent hip replacement (POD 3)", "History of DVT/PE (on anticoagulation)"
        ]
    }
    
    medication_pools = {
        "beginner": [],
        "intermediate": [
            "metformin 1000mg BID", "lisinopril 10mg daily", "amlodipine 5mg daily",
            "atorvastatin 40mg daily", "levothyroxine 75mcg daily", "omeprazole 20mg daily"
        ],
        "advanced": [
            "warfarin 5mg daily (INR 2.8)", "metformin 1000mg BID", "lisinopril 20mg daily",
            "digoxin 0.125mg daily", "furosemide 40mg BID", "metoprolol 50mg BID",
            "apixaban 5mg BID", "prednisone 10mg daily", "tacrolimus 2mg BID",
            "insulin glargine 30 units at bedtime", "carvedilol 25mg BID"
        ]
    }
    
    location = random.choice(locations.get(difficulty, locations["intermediate"]))
    infection_source = random.choice(infection_sources.get(difficulty, ["community-acquired"]))
    
    comorbidity_pool = comorbidity_pools.get(difficulty, [])
    if difficulty == "intermediate" and comorbidity_pool:
        comorbidities = random.sample(comorbidity_pool, 1)
    elif difficulty == "advanced" and comorbidity_pool:
        comorbidities = random.sample(comorbidity_pool, random.randint(2, 3))
    else:
        comorbidities = []
    
    medication_pool = medication_pools.get(difficulty, [])
    if difficulty == "advanced" and medication_pool:
        medications = random.sample(medication_pool, random.randint(2, 4))
    elif difficulty == "intermediate" and medication_pool:
        medications = random.sample(medication_pool, random.randint(1, 2))
    else:
        medications = []
    
    return {
        "location": location,
        "infection_source": infection_source,
        "comorbidities": comorbidities,
        "medications": medications
    }


# ============== DATA MODELS ==============
class QuestionRequest(BaseModel):
    topic: str
    difficulty: Optional[str] = "intermediate"
    question_type: Optional[str] = "mcq"
    use_hospital_policies: bool = True


class PubMedArticle(BaseModel):
    pmid: str
    title: str
    abstract: str
    authors: str
    journal: str
    pub_date: str
    relevance_score: float = 0.0


class Citation(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    pub_date: str
    relevance: str
    url: str


# ============== QUESTION TYPE MODELS ==============

# Standard MCQ Response
class MCQQuestion(BaseModel):
    scenario: str
    question: str
    options: dict
    correct_answer: str
    rationale: str
    incorrect_rationales: dict
    topic: str
    difficulty: str
    question_type: str = "mcq"
    citations: Optional[List[Citation]] = []
    citation_note: Optional[str] = None


# SATA Response
class SATAQuestion(BaseModel):
    scenario: str
    question: str
    options: dict
    correct_answers: List[str]
    rationale: str
    option_rationales: dict
    topic: str
    difficulty: str
    question_type: str = "sata"
    citations: Optional[List[Citation]] = []
    citation_note: Optional[str] = None


# Matrix Response
class MatrixQuestion(BaseModel):
    scenario: str
    question: str
    row_items: List[str]
    column_options: List[str]
    correct_matrix: dict
    rationale: str
    topic: str
    difficulty: str
    question_type: str = "matrix"
    citations: Optional[List[Citation]] = []
    citation_note: Optional[str] = None


# Cloze/Dropdown Response
class ClozeQuestion(BaseModel):
    scenario: str
    question_template: str
    blanks: dict
    correct_answers: dict
    rationale: str
    topic: str
    difficulty: str
    question_type: str = "cloze"
    citations: Optional[List[Citation]] = []
    citation_note: Optional[str] = None


# Highlight Response
class HighlightQuestion(BaseModel):
    scenario: str
    question: str
    text_passage: str
    correct_highlights: List[str]
    rationale: str
    topic: str
    difficulty: str
    question_type: str = "highlight"
    citations: Optional[List[Citation]] = []
    citation_note: Optional[str] = None


# Bowtie Response
class BowtieQuestion(BaseModel):
    scenario: str
    condition: str
    causes: List[str]
    correct_causes: List[str]
    interventions: List[str]
    correct_interventions: List[str]
    rationale: str
    topic: str
    difficulty: str
    question_type: str = "bowtie"
    citations: Optional[List[Citation]] = []
    citation_note: Optional[str] = None


# Union type for all question responses
QuestionResponse = Union[
    MCQQuestion,
    SATAQuestion,
    MatrixQuestion,
    ClozeQuestion,
    HighlightQuestion,
    BowtieQuestion
]


# Response wrapper with metadata
class GeneratedQuestionResponse(BaseModel):
    success: bool = True
    question_type: str
    data: dict
    citations: List[Citation] = []
    citation_note: Optional[str] = None
    

# ============== NEW MODELS FOR PHASE 2 ==============
class DocumentSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    file_filter: Optional[str] = None


class PolicyAlignedQuestionRequest(BaseModel):
    topic: str
    difficulty: Optional[str] = "intermediate"
    question_type: Optional[str] = "mcq"
    use_hospital_policies: bool = True


# ============== PUBMED FUNCTIONS ==============
def get_search_terms(topic: str) -> dict:
    """Get optimized search and match terms for topic."""
    topic_lower = topic.lower().strip()
    
    topic_db = {
        "sepsis": {
            "search": ["sepsis nursing", "sepsis management", "septic shock treatment"],
            "match": ["sepsis", "septic", "septicemia", "severe sepsis", "septic shock"]
        },
        "pneumonia": {
            "search": ["pneumonia nursing care", "pneumonia treatment", "community acquired pneumonia"],
            "match": ["pneumonia", "respiratory infection", "lung infection", "cap", "hospital acquired pneumonia"]
        },
        "heart failure": {
            "search": ["heart failure nursing", "heart failure management", "congestive heart failure"],
            "match": ["heart failure", "cardiac failure", "chf", "congestive", "hfref", "hfpef"]
        },
        "diabetes": {
            "search": ["diabetes nursing care", "diabetes management", "diabetic patient care"],
            "match": ["diabetes", "diabetic", "hyperglycemia", "hypoglycemia", "glucose", "insulin"]
        },
        "hypertension": {
            "search": ["hypertension nursing", "hypertension management", "blood pressure control"],
            "match": ["hypertension", "hypertensive", "high blood pressure", "blood pressure"]
        },
        "stroke": {
            "search": ["stroke nursing care", "acute stroke management", "cerebrovascular accident"],
            "match": ["stroke", "cva", "cerebrovascular", "ischemic stroke", "hemorrhagic stroke", "tpa"]
        },
        "copd": {
            "search": ["copd nursing", "copd exacerbation", "chronic obstructive pulmonary"],
            "match": ["copd", "chronic obstructive", "emphysema", "chronic bronchitis"]
        },
        "myocardial infarction": {
            "search": ["myocardial infarction nursing", "acute mi treatment", "stemi management"],
            "match": ["myocardial infarction", "mi", "heart attack", "stemi", "nstemi", "acute coronary"]
        },
        "asthma": {
            "search": ["asthma nursing care", "asthma management", "asthma exacerbation"],
            "match": ["asthma", "asthmatic", "bronchospasm", "wheezing", "inhaler"]
        },
        "renal failure": {
            "search": ["acute kidney injury nursing", "renal failure management", "dialysis nursing"],
            "match": ["renal failure", "kidney failure", "aki", "ckd", "dialysis", "creatinine"]
        }
    }
    
    for key, value in topic_db.items():
        if key in topic_lower or topic_lower in key:
            return value
    
    return {
        "search": [f"{topic_lower} nursing", f"{topic_lower} treatment", f"{topic_lower} management"],
        "match": [topic_lower] + topic_lower.split()
    }


def calculate_relevance(title: str, abstract: str, match_terms: List[str]) -> float:
    """Calculate relevance score."""
    title_lower = title.lower()
    abstract_lower = abstract.lower()
    
    score = 0.0
    for term in match_terms:
        if term in title_lower:
            score += 0.25
        if term in abstract_lower:
            score += 0.15
    
    return min(score, 1.0)


def search_pubmed_multiple(search_queries: List[str], max_per_query: int = 5) -> List[str]:
    """Search PubMed with multiple queries."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    all_pmids = set()
    
    for query in search_queries:
        params = {
            "db": "pubmed",
            "term": f"{query} AND English[Language]",
            "retmax": max_per_query,
            "retmode": "json",
            "sort": "relevance"
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pmids = data.get("esearchresult", {}).get("idlist", [])
                all_pmids.update(pmids)
        except Exception:
            continue
    
    return list(all_pmids)[:15]


def fetch_articles(pmids: List[str]) -> List[PubMedArticle]:
    """Fetch article details from PubMed."""
    if not pmids:
        return []
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        articles = []
        
        for article in root.findall(".//PubmedArticle"):
            try:
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                title_elem = article.find(".//ArticleTitle")
                title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""
                
                abstract_parts = article.findall(".//AbstractText")
                abstract = " ".join(["".join(a.itertext()) for a in abstract_parts]).strip()
                
                if not title or len(abstract) < 100:
                    continue
                
                authors_list = []
                for author in article.findall(".//Author")[:4]:
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None and lastname.text:
                        name = f"{forename.text} {lastname.text}" if forename is not None else lastname.text
                        authors_list.append(name)
                authors = ", ".join(authors_list)
                if len(article.findall(".//Author")) > 4:
                    authors += " et al."
                
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else "Unknown"
                
                year_elem = article.find(".//PubDate/Year")
                pub_date = year_elem.text if year_elem is not None else "Unknown"
                
                articles.append(PubMedArticle(
                    pmid=pmid, title=title, abstract=abstract[:2000],
                    authors=authors if authors else "Unknown",
                    journal=journal, pub_date=pub_date
                ))
            except Exception:
                continue
        
        return articles
    except Exception:
        return []


def get_relevant_citations(topic: str, max_citations: int = 3) -> List[PubMedArticle]:
    """Get relevant PubMed citations."""
    terms = get_search_terms(topic)
    pmids = search_pubmed_multiple(terms["search"], max_per_query=5)
    articles = fetch_articles(pmids)
    
    relevant = []
    for article in articles:
        score = calculate_relevance(article.title, article.abstract, terms["match"])
        if score >= RELEVANCE_THRESHOLD:
            article.relevance_score = score
            relevant.append(article)
    
    relevant.sort(key=lambda x: x.relevance_score, reverse=True)
    return relevant[:max_citations]


# ============== NGN QUESTION TYPE PROMPTS ==============

def get_ngn_format_instructions(question_type: str) -> str:
    """Get format-specific instructions for NGN question types."""
    
    formats = {
        "mcq": """
=== MCQ FORMAT ===
Standard multiple-choice with ONE correct answer.

OUTPUT JSON:
{
    "scenario": "Clinical scenario",
    "question": "Question stem",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct_answer": "A, B, C, or D",
    "rationale": "Why correct",
    "incorrect_rationales": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "topic": "...",
    "difficulty": "...",
    "question_type": "mcq"
}
""",

        "sata": """
=== SELECT ALL THAT APPLY (SATA) FORMAT ===
Multiple correct answers possible. Student must select ALL correct options.
MUST have 5-6 options with 2-4 correct answers.

OUTPUT JSON:
{
    "scenario": "Clinical scenario",
    "question": "Which of the following interventions are appropriate? SELECT ALL THAT APPLY.",
    "options": {
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option",
        "E": "Fifth option",
        "F": "Sixth option (optional)"
    },
    "correct_answers": ["A", "C", "E"],
    "rationale": "Overall rationale explaining the correct combination",
    "option_rationales": {
        "A": "Why A is correct/incorrect",
        "B": "Why B is correct/incorrect",
        "C": "Why C is correct/incorrect",
        "D": "Why D is correct/incorrect",
        "E": "Why E is correct/incorrect",
        "F": "Why F is correct/incorrect (if included)"
    },
    "topic": "...",
    "difficulty": "...",
    "question_type": "sata"
}
""",

        "matrix": """
=== MATRIX / GRID FORMAT ===
Table format where student matches row items to column categories.
Creates a grid with 4-5 row items and 2-3 column options.

OUTPUT JSON:
{
    "scenario": "Clinical scenario",
    "question": "For each assessment finding, indicate whether it is Expected, Unexpected, or Requires Immediate Attention.",
    "row_items": [
        "Heart rate 88 bpm",
        "Blood pressure 88/52 mmHg",
        "Temperature 101.5°F",
        "Oxygen saturation 98%",
        "Respiratory rate 28"
    ],
    "column_options": ["Expected", "Unexpected", "Requires Immediate Attention"],
    "correct_matrix": {
        "Heart rate 88 bpm": "Expected",
        "Blood pressure 88/52 mmHg": "Requires Immediate Attention",
        "Temperature 101.5°F": "Unexpected",
        "Oxygen saturation 98%": "Expected",
        "Respiratory rate 28": "Unexpected"
    },
    "rationale": "Explanation of each classification",
    "topic": "...",
    "difficulty": "...",
    "question_type": "matrix"
}
""",

        "cloze": """
=== CLOZE / DROP-DOWN FORMAT ===
CRITICAL: This is a fill-in-the-blank format with dropdown selections.
MUST contain 3-5 blanks within a clinical statement.
Each blank MUST have 3-4 DIFFERENT choices that are clinically plausible.

CRITICAL: USE DIFFERENT TEMPLATES FOR EACH DIFFICULTY LEVEL:

FOR BEGINNER - Use SYMPTOM RECOGNITION template:
"The nurse observes [BLANK1: symptom/sign options]. This indicates [BLANK2: interpretation options]. The expected vital sign finding would be [BLANK3: vital sign options]."
- Focus: Basic recognition, expected findings, simple interpretation
- NO medication decisions, NO lab interpretations

FOR INTERMEDIATE - Use PRIORITY/ACTION template:
"Given the patient's [BLANK1: comorbidity options], the nurse prioritizes [BLANK2: assessment/intervention options]. The medication [BLANK3: drug options] should be [BLANK4: action options] because of [BLANK5: reason options]."
- Focus: Priority decisions, medication considerations, clinical reasoning
- MUST include medication-related blanks

FOR ADVANCED - Use LAB/MEDICATION SYNTHESIS template:
"The [BLANK1: lab value options] combined with the patient's [BLANK2: medication options] suggests a risk for [BLANK3: complication options]. The nurse should [BLANK4: intervention options] and monitor for [BLANK5: adverse effect options]."
- Focus: Lab interpretation, medication interactions, complication prediction
- MUST include specific lab values and medication interactions

OUTPUT JSON:
{
    "scenario": "Clinical scenario appropriate for difficulty level",
    "question_template": "Template string with [BLANK1], [BLANK2], etc. - USE THE TEMPLATE MATCHING THE DIFFICULTY LEVEL",
    "blanks": {
        "BLANK1": ["option 1", "option 2", "option 3", "option 4"],
        "BLANK2": ["option 1", "option 2", "option 3", "option 4"],
        "BLANK3": ["option 1", "option 2", "option 3", "option 4"]
    },
    "correct_answers": {
        "BLANK1": "correct option",
        "BLANK2": "correct option",
        "BLANK3": "correct option"
    },
    "rationale": "Explanation of correct selections",
    "topic": "...",
    "difficulty": "...",
    "question_type": "cloze"
}
""",

        "highlight": """
=== HIGHLIGHT / HOT SPOT FORMAT ===
Student must identify specific information within a text passage.
Provide a clinical note/passage with key findings to highlight.

OUTPUT JSON:
{
    "scenario": "Context for why the nurse is reviewing this information",
    "question": "Highlight the assessment findings that require immediate nursing intervention.",
    "text_passage": "Nurse's Note: 0800 - Patient is a 68-year-old male admitted with pneumonia. Vital signs: T 101.8°F, HR 118, BP 86/54, RR 28, SpO2 88% on room air. Patient appears confused and lethargic. Skin is warm and flushed. Urine output has been 20mL over the past 2 hours. Patient states he feels 'okay' but family reports he has been increasingly confused since yesterday. Lungs with crackles in bilateral bases. IV access established in right forearm.",
    "correct_highlights": [
        "BP 86/54",
        "SpO2 88% on room air",
        "confused and lethargic",
        "Urine output has been 20mL over the past 2 hours"
    ],
    "rationale": "These findings indicate hemodynamic instability, hypoxemia, altered mental status, and oliguria - all signs of sepsis/septic shock requiring immediate intervention",
    "topic": "...",
    "difficulty": "...",
    "question_type": "highlight"
}
""",

        "bowtie": """
=== BOWTIE / CLINICAL JUDGMENT FORMAT ===
Tests clinical reasoning: Causes → Condition → Interventions
Student identifies what LED to the condition and what to DO about it.

OUTPUT JSON:
{
    "scenario": "Detailed clinical scenario with assessment findings, labs, and history",
    "condition": "The primary condition/problem (center of bowtie)",
    "causes": [
        "Potential cause 1",
        "Potential cause 2",
        "Potential cause 3",
        "Potential cause 4 (distractor)",
        "Potential cause 5 (distractor)"
    ],
    "correct_causes": ["Potential cause 1", "Potential cause 3"],
    "interventions": [
        "Intervention option 1",
        "Intervention option 2",
        "Intervention option 3",
        "Intervention option 4 (distractor)",
        "Intervention option 5 (distractor)"
    ],
    "correct_interventions": ["Intervention option 1", "Intervention option 2"],
    "rationale": "Explanation connecting causes to condition to interventions",
    "topic": "...",
    "difficulty": "...",
    "question_type": "bowtie"
}
"""
    }
    
    return formats.get(question_type, formats["mcq"])


# ============== PROMPT BUILDERS ==============

def build_prompt(topic: str, difficulty: str, question_type: str = "mcq") -> str:
    """Build prompt with strict constraints and NGN format instructions."""
    
    demographics = get_random_patient_demographics(difficulty)
    context = get_random_clinical_context(difficulty)
    
    age = demographics["age"]
    gender = demographics["gender"]
    location = context["location"]
    infection_source = context["infection_source"]
    comorbidities = context["comorbidities"]
    medications = context["medications"]
    
    comorbidity_str = ", ".join(comorbidities) if comorbidities else "none"
    medication_str = ", ".join(medications) if medications else "none"
    
    # Get NGN format instructions
    format_instructions = get_ngn_format_instructions(question_type)
    
    if difficulty == "beginner":
        constraints = f"""
=== BEGINNER LEVEL CONSTRAINTS ===

<INJECTED_PATIENT_VARIABLES>
- Patient Age: {age} years old (USE THIS EXACT AGE)
- Patient Gender: {gender} (USE THIS EXACT GENDER)
- Clinical Setting: {location}
- Infection Type: {infection_source}
</INJECTED_PATIENT_VARIABLES>

SCENARIO CONSTRAINTS:
- MUST use the exact age ({age}) and gender ({gender}) provided above.
- MUST set the scenario in: {location}
- MUST NOT include ANY comorbidities. Patient has ONLY {topic}.
- MUST be textbook/classic presentation with obvious symptoms.
- MUST have only ONE clearly abnormal vital sign.
- MUST be 2-3 sentences only.
- MUST NOT include any lab values.

QUESTION CONSTRAINTS:
- For MCQ/SATA: Ask about EXPECTED FINDINGS or INITIAL ASSESSMENT.
- Correct answers MUST be obviously correct to a nursing student.
- Distractors MUST be clearly wrong (related to different conditions).

FOR CLOZE QUESTIONS ONLY:
BEGINNER templates MUST test basic recognition of symptoms and expected findings.
- Template focus: Symptoms, expected findings, basic monitoring
- REQUIRED TEMPLATE STRUCTURE: "The nurse observes [BLANK1: symptom/sign]. This indicates [BLANK2: interpretation]. The expected finding would be [BLANK3: vital sign or assessment]."
- Blanks should test: symptom recognition, basic interpretation, expected findings
- DO NOT use priority/action templates - those are for intermediate
- DO NOT use lab interpretation templates - those are for advanced
"""

    elif difficulty == "intermediate":
        constraints = f"""
=== INTERMEDIATE LEVEL CONSTRAINTS ===

<INJECTED_PATIENT_VARIABLES>
- Patient Age: {age} years old (USE THIS EXACT AGE)
- Patient Gender: {gender} (USE THIS EXACT GENDER)
- Clinical Setting: {location}
- Infection Type: {infection_source}
- Comorbidities: {comorbidity_str}
- Home Medications: {medication_str}
</INJECTED_PATIENT_VARIABLES>

SCENARIO CONSTRAINTS:
- MUST use the exact age ({age}) and gender ({gender}) provided above.
- MUST set the scenario in: {location}
- MUST integrate these comorbidities into the patient history: {comorbidity_str}
- MUST integrate these home medications into the patient's chart: {medication_str}
- MUST have 2-3 abnormal vital signs that compete for attention.
- MUST be 4-5 sentences with vitals and brief history.
- MUST NOT include detailed lab values.

QUESTION CONSTRAINTS:
- For MCQ/SATA: Ask about PRIORITY intervention or BEST action.
- All options MUST be legitimate nursing interventions.
- Correct answer MUST require clinical reasoning.
- Consider how the comorbidity affects the decision.

FOR CLOZE QUESTIONS ONLY:
INTERMEDIATE templates MUST test clinical reasoning and priority decisions.
- Template focus: Priority assessment, nursing actions, medication considerations
- REQUIRED TEMPLATE STRUCTURE: "Given the patient's [BLANK1: comorbidity/condition], the nurse prioritizes [BLANK2: assessment or intervention]. The medication [BLANK3: specific drug] should be [BLANK4: held/administered/monitored] because of [BLANK5: clinical reason]."
- Blanks should test: priority identification, action sequencing, medication decisions
- MUST reference the patient's comorbidity ({comorbidity_str}) in one of the blanks
- MUST reference a medication decision in the template
- DO NOT use basic symptom recognition templates - those are for beginner
- DO NOT use lab interpretation templates - those are for advanced
"""

    else:  # advanced
        constraints = f"""
=== ADVANCED LEVEL CONSTRAINTS ===

<INJECTED_PATIENT_VARIABLES>
- Patient Age: {age} years old (USE THIS EXACT AGE)
- Patient Gender: {gender} (USE THIS EXACT GENDER)
- Clinical Setting: {location}
- Infection Type: {infection_source}
- Comorbidities: {comorbidity_str}
- Home Medications: {medication_str}
</INJECTED_PATIENT_VARIABLES>

SCENARIO CONSTRAINTS:
- MUST use the exact age ({age}) and gender ({gender}) provided above.
- MUST set the scenario in: {location}
- MUST integrate ALL these comorbidities: {comorbidity_str}
- MUST integrate ALL these medications and make them relevant: {medication_str}
- MUST include 3-4 specific lab values with numbers.
- MUST show evolving or deteriorating condition.
- MUST be 6-8 sentences with comprehensive clinical picture.
- MUST create a clinical dilemma where medication/comorbidity complicates treatment.

QUESTION CONSTRAINTS:
- Ask about NEXT action based on guidelines, OR lab/medication interaction, OR MOST CONCERNING finding.
- MUST NOT ask simple "first intervention" questions.
- All options MUST be clinically valid interventions.
- Correct answer MUST require synthesis of labs + meds + comorbidities.
- MUST create dilemma (e.g., fluid vs CHF, Metformin and AKI, anticoagulation and bleeding).

FOR CLOZE QUESTIONS ONLY:
ADVANCED templates MUST test complex synthesis of labs, medications, and complications.
- Template focus: Lab interpretation, medication interactions, complication identification
- REQUIRED TEMPLATE STRUCTURE: "The [BLANK1: specific lab value with number] combined with the patient's [BLANK2: medication from their list] suggests a risk for [BLANK3: specific complication]. The nurse should [BLANK4: specific intervention] and monitor for [BLANK5: adverse effect or sign]."
- Blanks MUST test: lab value interpretation, medication effect understanding, complication prediction
- MUST include at least one blank about a specific lab value (lactate, creatinine, potassium, etc.)
- MUST include at least one blank about medication interaction or contraindication
- MUST include at least one blank about a complication requiring synthesis of multiple factors
- DO NOT use basic symptom recognition templates - those are for beginner
- DO NOT use simple priority templates - those are for intermediate
"""

    return f"""You are an expert NCLEX-NGN question writer. Generate ONE nursing examination question.

TOPIC: {topic}
DIFFICULTY: {difficulty}
QUESTION TYPE: {question_type}

CRITICAL INSTRUCTION: You MUST generate a {question_type.upper()} format question, NOT any other format.
{"For CLOZE: Vary the blanks based on difficulty - do not use the same template for all difficulties." if question_type == "cloze" else ""}

{constraints}

{format_instructions}

CRITICAL RULES:
1. MUST use the exact patient variables provided (age, gender, location, comorbidities, medications).
2. MUST follow the {question_type.upper()} format EXACTLY as specified above.
3. MUST match the {difficulty} level requirements.
4. All clinical content MUST be accurate.
5. DO NOT generate MCQ format if {question_type.upper()} was requested.

Generate the JSON now:"""


def build_prompt_with_citations(topic: str, difficulty: str, question_type: str, articles: List[PubMedArticle]) -> str:
    """Build prompt with citations."""
    
    evidence = "\n".join([
        f"Source {i+1}: {a.title} ({a.authors}, {a.pub_date}) - {a.abstract[:400]}..."
        for i, a in enumerate(articles)
    ])
    
    base_prompt = build_prompt(topic, difficulty, question_type)
    
    evidence_section = f"""
=== MEDICAL EVIDENCE ===
{evidence}

Use these sources to ensure clinical accuracy. Reference in rationale where applicable.
"""
    
    # Insert before the format instructions
    return base_prompt.replace("CRITICAL RULES:", evidence_section + "\nCRITICAL RULES:")


# ============== RESPONSE VALIDATION ==============

def validate_question_response(data: dict, question_type: str) -> dict:
    """
    Validate the LLM response against the expected schema for the question type.
    Returns validated/cleaned data or raises ValueError.
    """
    
    # Required fields per question type
    required_fields = {
        "mcq": ["scenario", "question", "options", "correct_answer", "rationale"],
        "sata": ["scenario", "question", "options", "correct_answers", "rationale"],
        "matrix": ["scenario", "question", "row_items", "column_options", "correct_matrix", "rationale"],
        "cloze": ["scenario", "question_template", "blanks", "correct_answers", "rationale"],
        "highlight": ["scenario", "question", "text_passage", "correct_highlights", "rationale"],
        "bowtie": ["scenario", "condition", "causes", "correct_causes", "interventions", "correct_interventions", "rationale"]
    }
    
    fields = required_fields.get(question_type, required_fields["mcq"])
    
    # Check for missing required fields
    missing = [f for f in fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields for {question_type}: {missing}")
    
    # Type-specific validation
    if question_type == "mcq":
        if not isinstance(data.get("options"), dict) or len(data["options"]) < 4:
            raise ValueError("MCQ must have at least 4 options")
        if data.get("correct_answer") not in data["options"]:
            raise ValueError(f"Correct answer '{data.get('correct_answer')}' not in options")
    
    elif question_type == "sata":
        if not isinstance(data.get("correct_answers"), list) or len(data["correct_answers"]) < 2:
            raise ValueError("SATA must have at least 2 correct answers")
        for ans in data["correct_answers"]:
            if ans not in data.get("options", {}):
                raise ValueError(f"Correct answer '{ans}' not in options")
    
    elif question_type == "matrix":
        if not isinstance(data.get("row_items"), list) or len(data["row_items"]) < 3:
            raise ValueError("Matrix must have at least 3 row items")
        if not isinstance(data.get("column_options"), list) or len(data["column_options"]) < 2:
            raise ValueError("Matrix must have at least 2 column options")
    
    elif question_type == "cloze":
        if not isinstance(data.get("blanks"), dict) or len(data["blanks"]) < 2:
            raise ValueError("Cloze must have at least 2 blanks")
        if not isinstance(data.get("correct_answers"), dict):
            raise ValueError("Cloze correct_answers must be a dict")
    
    elif question_type == "highlight":
        if not isinstance(data.get("correct_highlights"), list) or len(data["correct_highlights"]) < 1:
            raise ValueError("Highlight must have at least 1 correct highlight")
        if not data.get("text_passage"):
            raise ValueError("Highlight must have a text_passage")
    
    elif question_type == "bowtie":
        if not isinstance(data.get("causes"), list) or len(data["causes"]) < 3:
            raise ValueError("Bowtie must have at least 3 causes")
        if not isinstance(data.get("interventions"), list) or len(data["interventions"]) < 3:
            raise ValueError("Bowtie must have at least 3 interventions")
        if not isinstance(data.get("correct_causes"), list) or len(data["correct_causes"]) < 1:
            raise ValueError("Bowtie must have at least 1 correct cause")
        if not isinstance(data.get("correct_interventions"), list) or len(data["correct_interventions"]) < 1:
            raise ValueError("Bowtie must have at least 1 correct intervention")
    
    # Ensure question_type is set correctly
    data["question_type"] = question_type
    
    return data



# ============== MANAGER INITIALIZATION (LAZY) ==============
# Managers now use lazy loading via get_learner_manager(), get_exam_manager(), get_recommendation_engine()
learner_manager = None  # Use get_learner_manager()
exam_manager = None  # Use get_exam_manager()
recommendation_engine = None  # Use get_recommendation_engine()

# ============== EXAM SESSION ENDPOINTS ==============

class ExamCreateRequest(BaseModel):
    learner_id: str
    mode: str
    total_questions: int
    time_limit_minutes: Optional[int] = None
    focus_topic: Optional[str] = None

@app.post("/api/exam/create")
def create_exam_session(request: ExamCreateRequest):
    """Create new exam session"""
    session = get_exam_manager().create_session(
        request.learner_id, 
        request.mode, 
        request.total_questions, 
        request.time_limit_minutes
    )
    return {
        "success": True,
        "session_id": session.session_id,
        "mode": request.mode,
        "total_questions": request.total_questions,
        "time_limit_minutes": request.time_limit_minutes,
        "focus_topic": request.focus_topic
    }

@app.get("/api/exam/{session_id}")
def get_exam_session(session_id: str):
    """Get exam session details"""
    session = get_exam_manager().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "success": True,
        "session": session.dict()
    }

@app.post("/api/exam/{session_id}/question")
async def add_question_to_exam(session_id: str, request: QuestionRequest):
    """Generate and add question to exam session"""
    
    # Check if adaptive mode
    session = get_exam_manager().get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Use adaptive difficulty if in adaptive mode
    if session.mode == "adaptive":
        request.difficulty = get_exam_manager().get_adaptive_next_difficulty(session_id)
    
    # Generate question
    question_response = await generate_question_complete(request)
    
    # Add to session
    question_id = f"q_{session_id}_{len(session.questions)+1}"
    get_exam_manager().add_question_to_session(
        session_id=session_id,
        question_id=question_id,
        topic=request.topic,
        difficulty=question_response['difficulty'],
        question_type=question_response['question_type'],
        skill_ids=[tag['skill_id'] for tag in question_response.get('skill_tags', [])],
        question_data=question_response['data'],
        correct_answer=question_response['data'].get('correct_answer')
    )
    
    return question_response

class ExamSubmitRequest(BaseModel):
    question_index: int
    user_answer: str
    time_spent_seconds: int

@app.post("/api/exam/{session_id}/submit")
def submit_exam_answer(session_id: str, request: ExamSubmitRequest):
    """Submit answer for exam question"""
    result = get_exam_manager().submit_answer(
        session_id, request.question_index, request.user_answer, request.time_spent_seconds
    )
    return {
        "success": True,
        **result
    }

# @app.post("/api/exam/{session_id}/complete")
# def complete_exam(session_id: str):
#     """Complete exam session"""
#     result = get_exam_manager().complete_session(session_id)
    
#     # Update learner profile with exam results
#     session = get_exam_manager().get_session(session_id)
#     if session:
#         for question in session.questions:
#             if question.timestamp:
#                 attempt = QuestionAttempt(
#                     question_id=question.question_id,
#                     skill_ids=question.skill_ids,
#                     topic=question.topic,
#                     difficulty=question.difficulty,
#                     question_type=question.question_type,
#                     correct=question.is_correct,
#                     timestamp=question.timestamp,
#                     time_spent_seconds=question.time_spent_seconds
#                 )
#                 get_learner_manager().record_attempt(session.learner_id, attempt)
    
#     return {
#         "success": True,
#         **result
#     }


@app.post("/api/exam/{session_id}/complete")
def complete_exam(session_id: str):
    """Complete exam session"""
    result = get_exam_manager().complete_session(session_id)
    
    # Attempts are already recorded in submit_answer endpoint!
    # No need to duplicate - exam_session.py records each attempt when submitted
    
    return {
        "success": True,
        **result
    }

@app.get("/api/exam/{session_id}/summary")
def get_exam_summary(session_id: str):
    """Get detailed exam summary"""
    summary = get_exam_manager().get_session_summary(session_id)
    return {
        "success": True,
        **summary
    }

@app.get("/api/learner/{learner_id}/exams")
def get_learner_exams(learner_id: str):
    """Get all exams for learner"""
    sessions = exam_manager.get_learner_sessions(learner_id)
    return {
        "success": True,
        "count": len(sessions),
        "sessions": [s.dict() for s in sessions]
    }

# ============== RECOMMENDATION ENDPOINTS ==============

@app.get("/api/learner/{learner_id}/recommendations")
def get_recommendations(learner_id: str):
    """Get personalized study recommendations"""
    recommendations = get_recommendation_engine().get_recommended_topics(learner_id)
    return {
        "success": True,
        "count": len(recommendations),
        "recommendations": recommendations
    }

@app.get("/api/learner/{learner_id}/recommendations/full")
def get_full_recommendations(learner_id: str):
    """Get comprehensive recommendations data"""
    data = get_recommendation_engine().get_comprehensive_recommendations(learner_id)
    return {
        "success": True,
        **data
    }

@app.get("/api/learner/{learner_id}/weak-skills")
def get_weak_skills(learner_id: str):
    """Get skills that need improvement"""
    weak_skills = get_recommendation_engine().get_weak_skills(learner_id)
    return {
        "success": True,
        "count": len(weak_skills),
        "weak_skills": weak_skills
    }

@app.get("/api/learner/{learner_id}/weak-topics")
def get_weak_topics(learner_id: str):
    """Get topics that need improvement"""
    weak_topics = get_recommendation_engine().get_weak_topics(learner_id)
    return {
        "success": True,
        "count": len(weak_topics),
        "weak_topics": weak_topics
    }

@app.get("/api/learner/{learner_id}/strong-topics")
def get_strong_topics(learner_id: str):
    """Get topics where learner excels"""
    strong_topics = recommendation_engine.get_strong_topics(learner_id)
    return {
        "success": True,
        "count": len(strong_topics),
        "strong_topics": strong_topics
    }

@app.post("/api/learner/{learner_id}/focused-exam")
def generate_focused_exam(learner_id: str, num_questions: int = 10):
    """Generate exam focused on weak areas"""
    exam_plan = get_recommendation_engine().generate_focused_exam(learner_id, num_questions)
    return {
        "success": True,
        **exam_plan
    }

@app.get("/api/learner/{learner_id}/milestone")
def get_next_milestone(learner_id: str):
    """Get learner's next milestone"""
    milestone = get_recommendation_engine().get_next_milestone(learner_id)
    return {
        "success": True,
        **milestone
    }
# ============== LEARNER PROFILE ENDPOINTS ==============

@app.post("/api/learner/create")
def create_learner(learner_id: str, name: str, role: str):
    """Create new learner profile"""
    profile = get_learner_manager().create_profile(learner_id, name, role)
    return {
        "success": True,
        "profile": profile.dict()
    }

@app.get("/api/learner/{learner_id}")
def get_learner_profile(learner_id: str):
    """Get learner profile"""
    profile = get_learner_manager().get_profile(learner_id)
    if not profile:
        raise HTTPException(404, "Learner not found")
    return {
        "success": True,
        "profile": profile.dict()
    }

@app.post("/api/learner/{learner_id}/attempt")
def record_attempt(learner_id: str, attempt: Dict):
    """Record question attempt"""
    try:
        attempt_obj = QuestionAttempt(
            question_id=attempt['question_id'],
            skill_ids=attempt['skill_ids'],
            topic=attempt['topic'],
            difficulty=attempt['difficulty'],
            question_type=attempt['question_type'],
            correct=attempt['correct'],
            timestamp=datetime.now(),
            time_spent_seconds=attempt.get('time_spent_seconds')
        )
        get_learner_manager().record_attempt(learner_id, attempt_obj)
        return {"success": True, "message": "Attempt recorded"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/learner/{learner_id}/performance")
def get_performance(learner_id: str):
    """Get learner performance summary"""
    profile = get_learner_manager().get_profile(learner_id)
    if not profile:
        raise HTTPException(404, "Learner not found")
    
    # Use the new comprehensive method
    perf_data = get_learner_manager().get_all_performance_data(learner_id)
    
    return {
        "success": True,
        "total_attempts": perf_data.get('total_questions', 0),
        "skills_practiced": perf_data.get('skills_practiced', 0),
        "topics_practiced": perf_data.get('topics_practiced', 0),
        "overall_accuracy": perf_data.get('overall_accuracy', 0),
        "exams_completed": perf_data.get('exams_completed', 0),
        "skill_performance": perf_data.get('skill_performance', {}),
        "topic_performance": perf_data.get('topic_performance', {}),
        "gaps": perf_data.get('skill_gaps', []),
        "strengths": perf_data.get('skill_strengths', []),
        "topic_strengths": perf_data.get('topic_strengths', []),
        "topic_weaknesses": perf_data.get('topic_weaknesses', []),
        "recent_exams": perf_data.get('recent_exams', [])
    }

@app.get("/api/learner/{learner_id}/radar")
def get_radar_data(learner_id: str, skill_ids: str):
    """Get radar chart data for specific skills"""
    skill_list = skill_ids.split(',')
    data = get_learner_manager().get_radar_chart_data(learner_id, skill_list)
    return {
        "success": True,
        "chart_data": data
    }

    

@app.post("/generate-question-with-skills-and-policies")
async def generate_question_complete(request: QuestionRequest):
    """Generate question with PubMed, policies, AND skill tagging"""
    
    print("\n" + "="*50)
    print(f"🎯 GENERATING QUESTION FOR: {request.topic}")
    print("="*50)
    
    # Normalize inputs
    difficulty = request.difficulty.lower()
    question_type = request.question_type.lower()
    topic = request.topic
    use_policies = getattr(request, 'use_hospital_policies', True)
    
    print(f"\n📚 STEP 1: Searching PubMed for '{topic}'...")
    citations = []
    evidence_context = ""
    try:
        terms = get_search_terms(topic)
        print(f"   Search terms: {terms['search']}")
        pmids = search_pubmed_multiple(terms['search'], max_per_query=5)
        print(f"   Found {len(pmids)} PMIDs")
        if pmids:
            articles = fetch_articles(pmids)
            print(f"   Fetched {len(articles)} full articles")
            if articles:
                for article in articles:
                    score = calculate_relevance(article.title, article.abstract, terms['match'])
                    article.relevance_score = score
                relevant = [a for a in articles if a.relevance_score >= RELEVANCE_THRESHOLD]
                print(f"   Filtered to {len(relevant)} relevant articles (>{RELEVANCE_THRESHOLD:.0%})")
                
                if relevant:
                    relevant.sort(key=lambda x: x.relevance_score, reverse=True)
                    top_articles = relevant[:3]
                    
                    citations = [
                        {
                            "pmid": a.pmid,
                            "title": a.title,
                            "authors": a.authors,
                            "journal": a.journal,
                            "pub_date": a.pub_date,
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/",
                            "relevance": f"{a.relevance_score:.0%}"
                        }
                        for a in top_articles
                    ]
                    
                    print(f"   ✅ Created {len(citations)} formatted citations")
                    evidence_context = "\n\n=== EVIDENCE-BASED MEDICAL LITERATURE ===\n"
                    for idx, cite in enumerate(citations, 1):
                        evidence_context += f"\n[Source {idx}] {cite['title']}\n"
                        evidence_context += f"Authors: {cite['authors']}\n"
                        evidence_context += f"Journal: {cite['journal']} ({cite['pub_date']})\n"
                        evidence_context += f"Relevance: {cite['relevance']}\n"
                    print(f"   ✅ Built evidence context")
            else:
                print("   ⚠️ Could not fetch article details")
        else:
            print("   ⚠️ No PMIDs found")
    except Exception as e:
        print(f"   ❌ PubMed error: {e}")
        import traceback
        traceback.print_exc()
    






    
    # ============== STEP 2: POLICY SEARCH ==============
    print(f"\n📋 STEP 2: Searching Hospital Policies...")
    policy_context = ""
    policy_citations = []
    
    if use_policies and rag_service:
        try:
            policy_query = f"{topic} protocol guidelines management"
            policy_results = get_rag_service().search(policy_query, limit=3)
            
            if policy_results:
                print(f"✅ Found {len(policy_results)} policy results")
                policy_context = "\n\n=== HOSPITAL POLICY CONTEXT ===\n"
                for idx, result in enumerate(policy_results, 1):
                    policy_context += f"\n[Policy {idx}] {result['filename']} - {result['section']}\n"
                    policy_context += f"{result['content']}\n"
                    
                    policy_citations.append({
                        "filename": result['filename'],
                        "section": result['section'],
                        "relevance": result['relevance_score']
                    })
        except Exception as e:
            print(f"⚠️ Policy search error: {e}")
    
    # ============== STEP 3: BUILD COMPREHENSIVE CONTEXT ==============
    print(f"\n🔨 STEP 3: Building prompt context...")
    full_context = evidence_context + policy_context
    print(f"✅ Total context length: {len(full_context)} characters")
    
    # ============== STEP 4: GENERATE QUESTION ==============
    print(f"\n🤖 STEP 4: Generating question with Gemini...")
    
    # Build detailed prompt
    prompt = f"""You are an expert NCLEX-NGN question writer. Create a {difficulty}-level {question_type.upper()} question about: {topic}

{full_context}

DIFFICULTY GUIDELINES:
- Beginner: Basic recall, definition-based, simple application
- Intermediate: Clinical reasoning, multi-step thinking, priority setting
- Advanced: Complex synthesis, multiple comorbidities, critical decision-making

CRITICAL REQUIREMENTS:
1. Create a realistic clinical scenario with specific patient details (age, vitals, symptoms)
2. Include relevant lab values or diagnostic findings when appropriate
3. All answer options must be clinically plausible
4. Rationale must explain WHY the correct answer is right AND why others are incorrect
5. Use evidence from the sources provided above when applicable
6. Return ONLY valid JSON with no markdown formatting

JSON OUTPUT FORMAT:
{{
  "scenario": "Detailed clinical case with patient demographics and presentation",
  "question": "Clear, specific question stem",
  "options": {{"A": "option 1", "B": "option 2", "C": "option 3", "D": "option 4"}},
  "correct_answer": "A",
  "rationale": "Comprehensive explanation citing evidence and clinical reasoning"
}}
"""

    # Add question-type specific instructions
    if question_type == "sata":
        prompt += '\n\nSATA FORMAT: Use 5-6 options, return: "correct_answers": ["A", "C", "E"]'
    elif question_type == "matrix":
        prompt += '\n\nMATRIX FORMAT: Return "row_items": [...], "column_options": [...], "correct_matrix": {"item1": "column1"}'
    elif question_type == "cloze":
        prompt += '\n\nCLOZE FORMAT: Return "question_template": "text with [Blank1] [Blank2]", "blanks": {"Blank1": ["opt1", "opt2"]}, "correct_answers": {"Blank1": "opt1"}'
    elif question_type == "highlight":
        prompt += '\n\nHIGHLIGHT FORMAT: Return "text_passage": "full text", "correct_highlights": ["phrase to highlight"]'
    elif question_type == "bowtie":
        prompt += '\n\nBOWTIE FORMAT: Return "condition": "diagnosis", "correct_causes": ["cause1"], "correct_interventions": ["intervention1"]'
    
    try:
        # Generate with Gemini
        response = get_model().generate_content(prompt)
        print(f"✅ Received response from Gemini")
        
        # Extract JSON from response
        import re
        text = response.text
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Find JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            question_json = json.loads(match.group(0))
        else:
            question_json = json.loads(text)
        
        print(f"✅ Parsed JSON successfully")
        
        # Add policy alignment note if applicable
        if policy_citations and 'rationale' in question_json:
            policy_note = f"\n\n📋 Policy Alignment: This question aligns with {policy_citations[0]['section']} of {policy_citations[0]['filename']}"
            question_json['rationale'] += policy_note
        
        # ============== STEP 5: BUILD RESPONSE ==============
        print(f"\n📦 STEP 5: Building final response...")
        
        question_data = {
            "success": True,
            "question_type": question_type,
            "difficulty": difficulty,
            "topic": topic,
            "data": question_json,
            "citations": citations,  # ← CRITICAL: PubMed citations
            "policy_citations": policy_citations,
            "citation_note": None
        }
        
        # Create citation note
        if citations or policy_citations:
            note_parts = []
            if citations:
                note_parts.append(f"{len(citations)} PubMed citation(s)")
            if policy_citations:
                note_parts.append(f"{len(policy_citations)} hospital policy reference(s)")
            question_data["citation_note"] = f"Generated with {' + '.join(note_parts)}"
        
        print(f"✅ Citations included: {len(citations)} PubMed + {len(policy_citations)} policies")
        
        # ============== STEP 6: ADD SKILL TAGGING ==============
        print(f"\n🎯 STEP 6: Auto-tagging skills...")
        
        skill_tags = get_question_tagger().tag_question(question_data)
        skill_ids = [tag['skill_id'] for tag in skill_tags]
        competencies = get_question_tagger().get_competencies_from_skills(skill_ids)
        
        print(f"✅ Tagged with {len(skill_tags)} skills and {len(competencies)} competencies")
        
        # ============== FINAL RESPONSE ==============
        print(f"\n✅ GENERATION COMPLETE!")
        print("="*50 + "\n")
        
        return {
            **question_data,
            "skill_tags": skill_tags,
            "competencies": competencies
        }
        
    except Exception as e:
        print(f"❌ Error in generation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error generating question: {str(e)}")
# ============== SKILLS ONTOLOGY ENDPOINTS ==============

@app.get("/api/skills/all")
def get_all_skills():
    """Get all clinical skills"""
    return {
        "success": True,
        "count": len(get_skills_ontology().skills),
        "skills": [skill.dict() for skill in get_skills_ontology().skills.values()]
    }

@app.get("/api/skills/category/{category}")
def get_skills_by_category(category: str):
    """Get skills by category"""
    try:
        cat = SkillCategory(category)
        skills = get_skills_ontology().get_skills_by_category(cat)
        return {
            "success": True,
            "category": category,
            "count": len(skills),
            "skills": [skill.dict() for skill in skills]
        }
    except ValueError:
        raise HTTPException(400, f"Invalid category: {category}")

@app.get("/api/skills/role/{role}")
def get_skills_by_role(role: str):
    """Get skills required for a role"""
    try:
        role_enum = ClinicalRole(role)
        skills = get_skills_ontology().get_skills_by_role(role_enum)
        return {
            "success": True,
            "role": role,
            "count": len(skills),
            "skills": [skill.dict() for skill in skills]
        }
    except ValueError:
        raise HTTPException(400, f"Invalid role: {role}")

@app.get("/api/competencies/all")
def get_all_competencies():
    """Get all competencies"""
    comps = get_skills_ontology().get_all_competencies()
    return {
        "success": True,
        "count": len(comps),
        "competencies": [comp.dict() for comp in comps]
    }

@app.get("/api/skills/tree")
def get_skill_tree():
    """Get hierarchical skill tree"""
    return {
        "success": True,
        "tree": get_skills_ontology().get_skill_tree()
    }




# ============== API ENDPOINTS ==============
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "1.0.1",
        "relevance_threshold": f"{RELEVANCE_THRESHOLD:.0%}"
    }


@app.get("/diagnostics")
def diagnostics():
    """Detailed system diagnostics"""
    diag = {
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check RAG service
    try:
        rag = get_rag_service()
        if rag and rag.client:
            diag["services"]["rag"] = {
                "status": "connected",
                "is_cloud": rag.is_cloud,
                "has_embedding_model": rag.embedding_model is not None,
                "weaviate_url": os.environ.get("WEAVIATE_URL", "not set")[:50] + "..." if os.environ.get("WEAVIATE_URL") else "not set",
                "weaviate_api_key": "set" if os.environ.get("WEAVIATE_API_KEY") else "not set"
            }
        else:
            diag["services"]["rag"] = {
                "status": "disconnected",
                "reason": "Client is None"
            }
    except Exception as e:
        diag["services"]["rag"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check other services
    try:
        diag["services"]["genai"] = {"status": "ready" if get_genai() else "not loaded"}
    except Exception as e:
        diag["services"]["genai"] = {"status": "error", "error": str(e)}
    
    try:
        diag["services"]["learner"] = {"status": "ready" if get_learner_manager() else "not loaded"}
    except Exception as e:
        diag["services"]["learner"] = {"status": "error", "error": str(e)}
    
    return diag


@app.get("/")
def root():
    """Serve the frontend HTML"""
    return FileResponse("index_s.html")

@app.get("/style_s.css")
def serve_css():
    """Serve CSS file"""
    return FileResponse("style_s.css")

@app.get("/app_s.js")
def serve_js():
    """Serve JavaScript file"""
    return FileResponse("app_s.js")

@app.get("/api/info")
def api_info():
    """API information - moved from root"""
    return {
        "service": "MedLearn AI",
        "version": "1.0.1",
        "description": "AI-powered NCLEX-NGN question generator with PubMed citations",
        "features": [
            "6 NGN Question Types (MCQ, SATA, Matrix, Cloze, Highlight, Bowtie)",
            "PubMed citation integration with 55% relevance threshold",
            "Difficulty-based patient demographics and clinical complexity",
            "Randomized scenarios for diversity",
            "Response validation with Pydantic models"
        ],
        "question_types": {
            "mcq": "Standard multiple choice (1 correct answer)",
            "sata": "Select All That Apply (multiple correct)",
            "matrix": "Matrix/Grid matching",
            "cloze": "Fill-in-the-blank with dropdowns",
            "highlight": "Highlight text in passage",
            "bowtie": "Clinical judgment (causes → condition → interventions)"
        },
        "response_structure": {
            "success": "boolean - whether generation succeeded",
            "question_type": "string - the normalized question type",
            "data": "object - the question data matching the type schema",
            "citations": "array - PubMed citations if available",
            "citation_note": "string - note if no citations found"
        },
        "difficulty_mappings": {
            "beginner": ["beginner", "easy", "simple", "basic", "1"],
            "intermediate": ["intermediate", "medium", "mid", "moderate", "2"],
            "advanced": ["advanced", "hard", "difficult", "tough", "3"]
        }
    }


@app.get("/search-pubmed")
def search_endpoint(topic: str, max_results: int = 5):
    """Search PubMed."""
    articles = get_relevant_citations(topic, max_citations=max_results)
    return {
        "topic": topic,
        "found": len(articles),
        "articles": [
            {
                "pmid": a.pmid,
                "title": a.title,
                "authors": a.authors,
                "journal": a.journal,
                "year": a.pub_date,
                "relevance": f"{a.relevance_score:.0%}",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/"
            }
            for a in articles
        ]
    }
# ============== PHASE 2: GOOGLE DRIVE & RAG ENDPOINTS ==============

@app.get("/api/drive/files")
def list_drive_files():
    """List all PDF, DOCX, PPTX files from Google Drive"""
    if not get_drive_service():
        raise HTTPException(503, "Google Drive service not initialized")
    
    try:
        files = get_drive_service().list_files()
        return {
            "success": True,
            "count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(500, f"Error listing files: {e}")


@app.post("/api/drive/index/{file_id}")
def index_drive_file(file_id: str):
    """Download and index a specific file from Google Drive"""
    if not get_drive_service() or not rag_service:
        raise HTTPException(503, "Services not initialized")
    
    try:
        # Get file metadata
        metadata = get_drive_service().get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(404, "File not found")
        
        # Download file
        file_bytes = get_drive_service().download_file(file_id)
        if not file_bytes:
            raise HTTPException(500, "Failed to download file")
        
        # Process document
        processed = get_doc_processor().process_document(
            file_bytes,
            metadata['mimeType'],
            metadata['name']
        )
        
        # Index into Weaviate
        indexed_count = get_rag_service().index_document(
            file_id,
            metadata['name'],
            metadata['mimeType'],
            processed['smart_chunks']
        )
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": metadata['name'],
            "chunks_indexed": indexed_count,
            "metadata": processed['metadata']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error indexing file: {e}")


@app.post("/api/documents/search")
def search_documents(request: DocumentSearchRequest):
    """Semantic search across indexed hospital documents"""
    if not get_rag_service():
        raise HTTPException(503, "RAG service not initialized")
    
    try:
        results = get_rag_service().search(
            request.query,
            request.limit,
            request.file_filter
        )
        
        return {
            "success": True,
            "query": request.query,
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(500, f"Search error: {e}")


@app.get("/api/documents/indexed")
def list_indexed_documents():
    """List all indexed documents in RAG system"""
    if not get_rag_service():
        raise HTTPException(503, "RAG service not initialized")
    
    try:
        files = get_rag_service().get_all_indexed_files()
        return {
            "success": True,
            "count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.delete("/api/documents/{file_id}")
def delete_indexed_document(file_id: str):
    """Remove document from RAG index by file_id"""
    if not get_rag_service():
        raise HTTPException(503, "RAG service not initialized")
    
    try:
        deleted = get_rag_service().delete_document(file_id)
        return {
            "success": True,
            "file_id": file_id,
            "chunks_deleted": deleted
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")

@app.delete("/api/documents/by-name/{filename}")
def delete_document_by_filename(filename: str):
    """Remove document from RAG index by filename"""
    if not get_rag_service():
        raise HTTPException(503, "RAG service not initialized")
    
    try:
        deleted = get_rag_service().delete_by_filename(filename)
        if deleted > 0:
            return {
                "success": True,
                "filename": filename,
                "chunks_deleted": deleted
            }
        else:
            raise HTTPException(404, f"Document '{filename}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.post("/generate-question-with-policies", response_model=GeneratedQuestionResponse)
def generate_with_policies(request: PolicyAlignedQuestionRequest):
    """
    Generate NCLEX question aligned with hospital policies
    Uses RAG to find relevant policy sections
    """
    if not get_rag_service():
        raise HTTPException(503, "RAG service not initialized")
    
    try:
        difficulty = normalize_difficulty(request.difficulty)
        question_type = normalize_question_type(request.question_type)
        
        # Search for relevant hospital policies
        policy_context = ""
        policy_citations = []
        
        if request.use_hospital_policies:
            policy_results = get_rag_service().search(
                f"{request.topic} protocol guidelines management",
                limit=3
            )
            
            if policy_results:
                policy_context = "\n\n=== HOSPITAL POLICY CONTEXT ===\n"
                for idx, result in enumerate(policy_results, 1):
                    policy_context += f"\nPolicy Source {idx} ({result['filename']} - {result['section']}):\n"
                    policy_context += f"{result['content'][:500]}...\n"
                    
                    policy_citations.append({
                        "filename": result['filename'],
                        "section": result['section'],
                        "relevance_score": f"{result['relevance_score']:.0%}"
                    })
        
        # Get PubMed citations
        pubmed_articles = get_relevant_citations(request.topic, max_citations=3)
        
        # Build prompt with both PubMed and policy context
        if pubmed_articles:
            prompt = build_prompt_with_citations(request.topic, difficulty, question_type, pubmed_articles)
        else:
            prompt = build_prompt(request.topic, difficulty, question_type)
        
        # Inject policy context
        if policy_context:
            prompt = prompt.replace(
                "CRITICAL RULES:",
                policy_context + "\n\nIMPORTANT: Align question with hospital policies above when applicable.\n\nCRITICAL RULES:"
            )
        
        # Generate question
        response = get_model().generate_content(
            prompt,
            generation_config=get_genai().GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=3500,
                response_mime_type="application/json"
            )
        )
        
        data = json.loads(response.text)
        validated_data = validate_question_response(data, question_type)
        
        # Prepare citations
        citation_data = [
            Citation(
                pmid=a.pmid,
                title=a.title,
                authors=a.authors,
                journal=a.journal,
                pub_date=a.pub_date,
                relevance=f"{a.relevance_score:.0%}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/"
            )
            for a in pubmed_articles
        ]
        
        # Add policy alignment note to rationale
        if policy_citations:
            policy_note = "\n\n📋 Policy Alignment: This question aligns with "
            policy_note += ", ".join([f"{p['section']} of {p['filename']}" for p in policy_citations])
            validated_data['rationale'] += policy_note
        
        return GeneratedQuestionResponse(
            success=True,
            question_type=question_type,
            data=validated_data,
            citations=citation_data,
            citation_note=f"Generated with {len(policy_citations)} hospital policy references" if policy_citations else None
        )
    
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Parse error: {e}")
    except ValueError as e:
        raise HTTPException(422, f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.post("/generate-question", response_model=GeneratedQuestionResponse)
def generate_question(request: QuestionRequest):
    """Generate NCLEX question (any type) without citations."""
    try:
        difficulty = normalize_difficulty(request.difficulty)
        question_type = normalize_question_type(request.question_type)
        
        prompt = build_prompt(request.topic, difficulty, question_type)
        
        response = get_model().generate_content(
            prompt,
            generation_config=get_genai().GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=3000,
                response_mime_type="application/json"
            )
        )
        
        data = json.loads(response.text)
        
        # Validate against the appropriate model
        validated_data = validate_question_response(data, question_type)
        
        return GeneratedQuestionResponse(
            success=True,
            question_type=question_type,
            data=validated_data,
            citations=[],
            citation_note=None
        )
    
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Parse error: {e}")
    except ValueError as e:
        raise HTTPException(422, f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.post("/generate-question-with-citations", response_model=GeneratedQuestionResponse)
def generate_with_citations(request: QuestionRequest):
    """Generate NCLEX question (any type) with PubMed citations."""
    try:
        difficulty = normalize_difficulty(request.difficulty)
        question_type = normalize_question_type(request.question_type)
        
        articles = get_relevant_citations(request.topic, max_citations=3)
        
        citation_note = None
        citation_data = []
        
        if articles:
            prompt = build_prompt_with_citations(request.topic, difficulty, question_type, articles)
            citation_data = [
                Citation(
                    pmid=a.pmid,
                    title=a.title,
                    authors=a.authors,
                    journal=a.journal,
                    pub_date=a.pub_date,
                    relevance=f"{a.relevance_score:.0%}",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/"
                )
                for a in articles
            ]
        else:
            prompt = build_prompt(request.topic, difficulty, question_type)
            citation_note = f"No PubMed articles met the {RELEVANCE_THRESHOLD:.0%} relevance threshold for '{request.topic}'."
        
        response = get_model().generate_content(
            prompt,
            generation_config=get_genai().GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=3500,
                response_mime_type="application/json"
            )
        )
        
        data = json.loads(response.text)
        
        # Validate against the appropriate model
        validated_data = validate_question_response(data, question_type)
        
        return GeneratedQuestionResponse(
            success=True,
            question_type=question_type,
            data=validated_data,
            citations=citation_data,
            citation_note=citation_note
        )
    
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Parse error: {e}")
    except ValueError as e:
        raise HTTPException(422, f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


# ============== FILE UPLOAD ENDPOINT ==============
@app.post("/api/upload-and-index")
async def upload_and_index(file: UploadFile = File(...)):
    """
    Upload file and index it for RAG
    Works without Google Drive - indexes directly to Weaviate
    """
    # Check if RAG service is available
    rag = get_rag_service()
    doc_proc = get_doc_processor()
    
    if not rag or not rag.client:
        raise HTTPException(503, "RAG service not available. Please configure WEAVIATE_URL and WEAVIATE_API_KEY.")
    
    if not doc_proc:
        raise HTTPException(503, "Document processor not available")
    
    # Validate file type
    allowed_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'application/msword',  # .doc
        'application/vnd.ms-powerpoint'  # .ppt
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Invalid file type. Allowed: PDF, DOCX, PPTX")
    
    try:
        print(f"\n{'='*50}")
        print(f"📤 UPLOADING: {file.filename}")
        print(f"{'='*50}")
        
        # Read file content
        print("   📥 Reading file...")
        file_bytes = await file.read()
        file_size_kb = len(file_bytes) / 1024
        print(f"   ✅ File size: {file_size_kb:.1f} KB")
        
        # Generate a unique file ID (since we're not using Drive)
        import uuid
        file_id = f"upload_{uuid.uuid4().hex[:12]}"
        
        # Try to upload to Google Drive if available (optional)
        drive = get_drive_service()
        if drive:
            try:
                print("   ☁️ Uploading to Google Drive...")
                uploaded_file = drive.upload_file(file_bytes, file.filename, file.content_type)
                if uploaded_file and uploaded_file.get('id'):
                    file_id = uploaded_file['id']
                    print(f"   ✅ Uploaded to Drive: {file_id}")
            except Exception as drive_error:
                print(f"   ⚠️ Drive upload skipped: {drive_error}")
        else:
            print("   ℹ️ Google Drive not configured - indexing directly")
        
        # Process document
        print("   📄 Processing document...")
        processed = doc_proc.process_document(
            file_bytes,
            file.content_type,
            file.filename
        )
        num_chunks = len(processed.get('smart_chunks', []))
        print(f"   ✅ Created {num_chunks} chunks")
        
        # Index into Weaviate
        print("   🔍 Indexing into Weaviate...")
        indexed_count = rag.index_document(
            file_id,
            file.filename,
            file.content_type,
            processed['smart_chunks']
        )
        
        print(f"{'='*50}")
        print(f"✅ UPLOAD COMPLETE: {file.filename}")
        print(f"   Chunks indexed: {indexed_count}")
        print(f"{'='*50}\n")
        
        return {
            "success": True,
            "message": "File uploaded and indexed successfully",
            "file_id": file_id,
            "filename": file.filename,
            "chunks_indexed": indexed_count,
            "metadata": processed.get('metadata', {}),
            "drive_link": uploaded_file.get('webViewLink', '')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Upload error: {e}")


# ============== AUTHORING CO-PILOT ENDPOINTS ==============

class ModuleRequest(BaseModel):
    title: str
    questions: List[Dict]
    audience: str = "student"
    style: str = "plain"
    include_spanish: bool = False

class TranslationRequest(BaseModel):
    text: str
    target_language: str = "spanish"

@app.post("/api/authoring/generate-module")
async def generate_micro_module(request: ModuleRequest):
    """Generate a micro-learning module from selected questions"""
    try:
        # Extract unique topics from questions
        topics = list(set(q.get('topic', 'Clinical Practice') for q in request.questions))
        main_topic = topics[0] if topics else 'Clinical Practice'
        
        # Determine audience-appropriate language
        audience_context = "nursing student with basic clinical knowledge" if request.audience == "student" else "experienced registered nurse with advanced clinical expertise"
        style_context = "clear, simple explanations avoiding complex jargon" if request.style == "plain" else "professional medical terminology and detailed clinical reasoning"
        
        # Generate module using Gemini
        prompt = f"""Create a comprehensive micro-learning module for a {audience_context}.
        
Title: {request.title}
Topics Covered: {', '.join(topics)}
Writing Style: {style_context}
Number of Practice Questions: {len(request.questions)}

Generate a structured learning module with:

1. LEARNING OBJECTIVES (3-5 specific, measurable objectives using action verbs like "identify", "demonstrate", "apply", "analyze")

2. TEACHING CONTENT (comprehensive educational content covering):
   - Key concepts and definitions
   - Pathophysiology/mechanism (if applicable)
   - Assessment findings
   - Nursing interventions
   - Patient safety considerations

3. CLINICAL PEARLS (5-7 practical tips that experienced nurses would share, focusing on real-world application)

Format your response as JSON:
{{
    "learning_objectives": ["objective 1", "objective 2", ...],
    "teaching_content": [
        {{"topic": "Topic Name", "content": "Detailed educational content..."}}
    ],
    "clinical_pearls": ["pearl 1", "pearl 2", ...]
}}
"""
        
        response = get_model().generate_content(prompt)
        response_text = response.text
        
        # Clean up response
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        module_data = json.loads(response_text.strip())
        
        # Add Spanish summary if requested
        spanish_summary = None
        if request.include_spanish:
            spanish_prompt = f"Translate this brief summary to Spanish: This module covers {main_topic} including assessment, interventions, and clinical decision-making for nursing practice."
            spanish_response = get_model().generate_content(spanish_prompt)
            spanish_summary = spanish_response.text
        
        return {
            "success": True,
            "module": {
                "title": request.title,
                "learning_objectives": module_data.get("learning_objectives", []),
                "teaching_content": module_data.get("teaching_content", []),
                "clinical_pearls": module_data.get("clinical_pearls", []),
                "questions": request.questions,
                "spanish_summary": spanish_summary
            }
        }
        
    except json.JSONDecodeError as e:
        # Fallback with basic structure
        return {
            "success": True,
            "module": {
                "title": request.title,
                "learning_objectives": [
                    f"Identify key assessment findings related to {main_topic}",
                    f"Apply evidence-based interventions for {main_topic}",
                    f"Demonstrate critical thinking in {main_topic} scenarios"
                ],
                "teaching_content": [{
                    "topic": main_topic,
                    "content": f"This module provides comprehensive education on {main_topic}. Healthcare providers should understand the pathophysiology, recognize clinical manifestations, and implement appropriate nursing interventions."
                }],
                "clinical_pearls": [
                    "Always assess vital signs in the context of the patient's baseline",
                    "Document thoroughly and communicate changes promptly",
                    "When in doubt, escalate to a more experienced provider",
                    "Patient education is essential for positive outcomes",
                    "Consider cultural and individual factors in care planning"
                ],
                "questions": request.questions,
                "spanish_summary": None
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Module generation error: {str(e)}")

@app.post("/api/authoring/translate")
async def translate_text(request: TranslationRequest):
    """Translate text to Spanish"""
    try:
        prompt = f"""Translate the following medical/nursing education text to Spanish. 
Maintain medical terminology accuracy while making it accessible.

Text to translate:
{request.text}

Provide only the Spanish translation, no additional text."""

        response = get_model().generate_content(prompt)
        
        return {
            "success": True,
            "original": request.text,
            "translation": response.text.strip(),
            "language": request.target_language
        }
        
    except Exception as e:
        raise HTTPException(500, f"Translation error: {str(e)}")

@app.post("/api/authoring/batch-generate")
async def batch_generate_questions(
    topic: str,
    count: int = 10,
    audience: str = "student",
    style: str = "plain"
):
    """Generate multiple questions from a topic with balanced distribution"""
    try:
        question_types = ['mcq', 'sata', 'matrix', 'cloze', 'highlight', 'bowtie']
        difficulties = ['beginner', 'intermediate', 'advanced']
        
        generated = []
        
        for i in range(count):
            q_type = question_types[i % len(question_types)]
            difficulty = difficulties[i % len(difficulties)]
            
            # Use existing question generation logic
            request = QuestionRequest(
                topic=topic,
                difficulty=difficulty,
                question_type=q_type,
                num_citations=2,
                use_policies=True
            )
            
            # Generate question (simplified - you may want to call the full generation endpoint)
            generated.append({
                "id": f"batch_{i}_{datetime.now().timestamp()}",
                "type": q_type,
                "difficulty": difficulty,
                "topic": topic
            })
        
        return {
            "success": True,
            "count": len(generated),
            "questions": generated
        }
        
    except Exception as e:
        raise HTTPException(500, f"Batch generation error: {str(e)}")


# ============================================
# AI TUTOR ENDPOINT
# ============================================

class TutorRequest(BaseModel):
    question: str
    conversation_history: Optional[List[dict]] = []

@app.post("/api/tutor/ask")
async def ask_tutor(request: TutorRequest):
    """
    AI Tutor - Educational Q&A powered by RAG (PubMed + Hospital Docs)
    Returns explanations with citations for learning purposes.
    """
    try:
        question = request.question
        citations = []
        context_parts = []
        
        print(f"\n{'='*50}")
        print(f"🤖 AI TUTOR QUERY: {question[:100]}...")
        print(f"{'='*50}")
        
        # Step 1: Search hospital policies/documents (RAG)
        hospital_context = ""
        if get_rag_service():
            print("📚 Searching hospital documents...")
            try:
                rag_results = get_rag_service().search(question, limit=3)
                if rag_results:
                    for i, result in enumerate(rag_results):
                        if result.get('relevance_score', 0) > 0.5:
                            hospital_context += f"\n[Hospital Document: {result['filename']}]\n{result['content'][:500]}...\n"
                            citations.append({
                                "type": "hospital",
                                "source": result['filename'],
                                "section": result.get('section', 'General'),
                                "relevance": round(result.get('relevance_score', 0) * 100)
                            })
                    print(f"   ✅ Found {len(citations)} relevant hospital documents")
            except Exception as e:
                print(f"   ⚠️ RAG search error: {e}")
        
        # Step 2: Search PubMed for evidence
        pubmed_context = ""
        print("📄 Searching PubMed...")
        try:
            # Use existing search function
            search_terms = [question.replace("?", "")]
            pubmed_ids = search_pubmed_articles(search_terms, max_results=5)
            
            if pubmed_ids:
                articles = fetch_pubmed_details(pubmed_ids[:3])
                for article in articles:
                    if article.get('abstract'):
                        pubmed_context += f"\n[PubMed: {article.get('title', 'Unknown')[:100]}]\n{article.get('abstract', '')[:400]}...\n"
                        citations.append({
                            "type": "pubmed",
                            "source": article.get('title', 'PubMed Article')[:80],
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/" if article.get('pmid') else None
                        })
                print(f"   ✅ Found {len(articles)} PubMed articles")
        except Exception as e:
            print(f"   ⚠️ PubMed search error: {e}")
        
        # Step 3: Build context for Gemini
        context = ""
        if hospital_context:
            context += f"\n## Hospital Policies & Documents:\n{hospital_context}\n"
        if pubmed_context:
            context += f"\n## PubMed Research Evidence:\n{pubmed_context}\n"
        
        # Step 4: Build conversation history
        history_text = ""
        if request.conversation_history:
            for msg in request.conversation_history[-4:]:  # Last 2 exchanges
                role = "Student" if msg.get('role') == 'user' else "Tutor"
                history_text += f"{role}: {msg.get('content', '')[:200]}\n"
        
        # Step 5: Generate response with Gemini
        print("🧠 Generating response with Gemini...")
        
        tutor_prompt = f"""You are an AI Tutor for nursing and medical education. Your role is to help students understand clinical concepts.

IMPORTANT GUIDELINES:
1. This is FOR EDUCATIONAL PURPOSES ONLY - always remind students this is not medical advice
2. Explain concepts clearly using the evidence provided
3. Use simple language but maintain clinical accuracy
4. Reference the sources when explaining (e.g., "According to recent research..." or "Hospital policy states...")
5. Be encouraging and supportive
6. If you don't know something, say so honestly

CONTEXT FROM SOURCES:
{context if context else "No specific sources found. Use your general medical knowledge but note this to the student."}

CONVERSATION HISTORY:
{history_text if history_text else "This is a new conversation."}

STUDENT'S QUESTION:
{question}

Provide a clear, educational response. Structure your answer with:
1. Direct answer to the question
2. Explanation of the underlying concepts
3. Clinical relevance (why this matters in practice)
4. Brief summary

Keep your response focused and around 200-300 words unless the topic requires more detail."""

        response = get_model().generate_content(
            tutor_prompt,
            generation_config=get_genai().GenerationConfig(
                temperature=0.7,
                max_output_tokens=1000
            )
        )
        
        answer = response.text
        
        # Add educational disclaimer
        answer += "\n\n*📚 Remember: This information is for educational and training purposes only. Always consult clinical guidelines and supervising clinicians for patient care decisions.*"
        
        print(f"✅ Tutor response generated ({len(answer)} chars)")
        print(f"   Citations: {len(citations)} sources")
        print(f"{'='*50}\n")
        
        return {
            "success": True,
            "answer": answer,
            "citations": citations,
            "sources_used": {
                "hospital_docs": len([c for c in citations if c['type'] == 'hospital']),
                "pubmed": len([c for c in citations if c['type'] == 'pubmed'])
            }
        }
        
    except Exception as e:
        print(f"❌ Tutor error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Tutor error: {str(e)}")


# ============== RUN ==============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
