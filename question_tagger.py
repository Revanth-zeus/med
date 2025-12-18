from typing import List, Dict
from skills_ontology import SkillsOntology, Skill
import re

class QuestionTagger:
    """Auto-tag questions with relevant skills"""
    
    def __init__(self, skills_ontology: SkillsOntology):
        self.ontology = skills_ontology
    
    def extract_keywords(self, question_data: Dict) -> List[str]:
        """Extract keywords from question content"""
        keywords = []
        
        # Extract from topic
        if 'topic' in question_data:
            keywords.extend(question_data['topic'].lower().split())
        
        # Extract from scenario
        if 'scenario' in question_data.get('data', {}):
            scenario = question_data['data']['scenario'].lower()
            # Extract medical terms (simplified)
            medical_terms = re.findall(r'\b[a-z]{4,}\b', scenario)
            keywords.extend(medical_terms)
        
        # Extract from question text
        if 'question' in question_data.get('data', {}):
            question = question_data['data']['question'].lower()
            keywords.extend(re.findall(r'\b[a-z]{4,}\b', question))
        
        # Remove duplicates
        return list(set(keywords))
    
    def tag_question(self, question_data: Dict) -> List[Dict]:
        """Tag question with relevant skills"""
        keywords = self.extract_keywords(question_data)
        matching_skills = self.ontology.search_skills_by_keywords(keywords)
        
        # Score each skill by keyword overlap
        skill_scores = []
        for skill in matching_skills:
            overlap = len(set(keywords) & set([k.lower() for k in skill.keywords]))
            confidence = min(overlap / len(skill.keywords), 1.0)
            
            if confidence > 0.3:  # Threshold
                skill_scores.append({
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "category": skill.category.value,
                    "confidence": round(confidence, 2),
                    "matched_keywords": list(set(keywords) & set([k.lower() for k in skill.keywords]))
                })
        
        # Sort by confidence
        skill_scores.sort(key=lambda x: x['confidence'], reverse=True)
        
        return skill_scores
    
    def get_competencies_from_skills(self, skill_ids: List[str]) -> List[Dict]:
        """Get competencies that include these skills"""
        matching_comps = []
        
        for comp in self.ontology.get_all_competencies():
            overlap = set(skill_ids) & set(comp.skills)
            if overlap:
                matching_comps.append({
                    "competency_id": comp.id,
                    "competency_name": comp.name,
                    "matching_skills": list(overlap),
                    "coverage": len(overlap) / len(comp.skills)
                })
        
        return matching_comps