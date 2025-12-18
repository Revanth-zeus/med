from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel
import json

class ProficiencyLevel(str, Enum):
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ClinicalRole(str, Enum):
    RN = "Registered Nurse"
    LPN = "Licensed Practical Nurse"
    ICU_NURSE = "ICU Nurse"
    ER_NURSE = "Emergency Room Nurse"
    MED_SURG_NURSE = "Medical-Surgical Nurse"
    PICU_NURSE = "Pediatric ICU Nurse"
    NURSE_PRACTITIONER = "Nurse Practitioner"
    RESPIRATORY_THERAPIST = "Respiratory Therapist"
    PHYSICIAN = "Physician"

class SkillCategory(str, Enum):
    ASSESSMENT = "Clinical Assessment"
    INTERVENTION = "Clinical Intervention"
    MONITORING = "Patient Monitoring"
    MEDICATION = "Medication Management"
    COMMUNICATION = "Communication"
    CRITICAL_THINKING = "Critical Thinking"
    TECHNICAL = "Technical Skills"
    SAFETY = "Patient Safety"

class Skill(BaseModel):
    """Individual clinical skill"""
    id: str
    name: str
    description: str
    category: SkillCategory
    parent_skill: Optional[str] = None  # For skill hierarchy
    required_roles: List[ClinicalRole]
    proficiency_levels: List[ProficiencyLevel]
    keywords: List[str]  # For auto-tagging

class Competency(BaseModel):
    """Grouping of related skills"""
    id: str
    name: str
    description: str
    skills: List[str]  # Skill IDs
    roles: List[ClinicalRole]

class SkillsOntology:
    """Manages the clinical skills knowledge graph"""
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.competencies: Dict[str, Competency] = {}
        self._initialize_default_skills()
    
    def _initialize_default_skills(self):
        """Load predefined clinical skills for nursing"""
        
        # ARDS/Ventilator Management Skills
        ards_skills = [
            Skill(
                id="skill_ards_recognition",
                name="Recognize ARDS",
                description="Identify signs and symptoms of Acute Respiratory Distress Syndrome",
                category=SkillCategory.ASSESSMENT,
                required_roles=[ClinicalRole.ICU_NURSE, ClinicalRole.RESPIRATORY_THERAPIST],
                proficiency_levels=[ProficiencyLevel.BEGINNER, ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["ARDS", "respiratory distress", "hypoxemia", "bilateral infiltrates", "PaO2/FiO2"]
            ),
            Skill(
                id="skill_vent_setup",
                name="Ventilator Setup",
                description="Configure mechanical ventilator settings according to protocol",
                category=SkillCategory.TECHNICAL,
                required_roles=[ClinicalRole.ICU_NURSE, ClinicalRole.RESPIRATORY_THERAPIST],
                proficiency_levels=[ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["ventilator", "tidal volume", "PEEP", "FiO2", "plateau pressure", "ARDSnet"]
            ),
            Skill(
                id="skill_vent_monitoring",
                name="Ventilator Monitoring",
                description="Monitor and interpret ventilator parameters and patient response",
                category=SkillCategory.MONITORING,
                required_roles=[ClinicalRole.ICU_NURSE, ClinicalRole.RESPIRATORY_THERAPIST],
                proficiency_levels=[ProficiencyLevel.BEGINNER, ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["plateau pressure", "Pplat", "respiratory rate", "minute ventilation", "ABG", "pH"]
            ),
            Skill(
                id="skill_vent_weaning",
                name="Ventilator Weaning",
                description="Assess readiness and conduct spontaneous breathing trials",
                category=SkillCategory.INTERVENTION,
                required_roles=[ClinicalRole.ICU_NURSE, ClinicalRole.RESPIRATORY_THERAPIST],
                proficiency_levels=[ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["weaning", "spontaneous breathing trial", "SBT", "extubation", "PEEP"]
            ),
            Skill(
                id="skill_pbw_calculation",
                name="Calculate Predicted Body Weight",
                description="Calculate PBW for lung-protective ventilation",
                category=SkillCategory.ASSESSMENT,
                required_roles=[ClinicalRole.ICU_NURSE, ClinicalRole.RESPIRATORY_THERAPIST],
                proficiency_levels=[ProficiencyLevel.BEGINNER, ProficiencyLevel.INTERMEDIATE],
                keywords=["predicted body weight", "PBW", "tidal volume", "height", "calculation"]
            )
        ]
        
        # Sepsis Skills
        sepsis_skills = [
            Skill(
                id="skill_sepsis_recognition",
                name="Recognize Sepsis",
                description="Identify signs of sepsis and septic shock",
                category=SkillCategory.ASSESSMENT,
                required_roles=[ClinicalRole.RN, ClinicalRole.ICU_NURSE, ClinicalRole.ER_NURSE],
                proficiency_levels=[ProficiencyLevel.BEGINNER, ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["sepsis", "septic shock", "SIRS", "qSOFA", "infection", "hypotension"]
            ),
            Skill(
                id="skill_sepsis_management",
                name="Sepsis Management",
                description="Implement sepsis bundle and initial resuscitation",
                category=SkillCategory.INTERVENTION,
                required_roles=[ClinicalRole.RN, ClinicalRole.ICU_NURSE, ClinicalRole.ER_NURSE],
                proficiency_levels=[ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["sepsis bundle", "fluid resuscitation", "antibiotics", "crystalloid", "vasopressors"]
            )
        ]
        
        # Medication Skills
        med_skills = [
            Skill(
                id="skill_medication_admin",
                name="Medication Administration",
                description="Safely administer medications following 5 rights",
                category=SkillCategory.MEDICATION,
                required_roles=[ClinicalRole.RN, ClinicalRole.LPN, ClinicalRole.ICU_NURSE],
                proficiency_levels=[ProficiencyLevel.BEGINNER, ProficiencyLevel.INTERMEDIATE],
                keywords=["medication", "administration", "IV", "dosage", "drug"]
            ),
            Skill(
                id="skill_critical_drug_management",
                name="Critical Drug Management",
                description="Manage vasoactive and high-alert medications",
                category=SkillCategory.MEDICATION,
                required_roles=[ClinicalRole.ICU_NURSE, ClinicalRole.ER_NURSE],
                proficiency_levels=[ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.ADVANCED],
                keywords=["vasopressor", "inotrope", "sedation", "paralytic", "high-alert"]
            )
        ]
        
        # Add all skills
        all_skills = ards_skills + sepsis_skills + med_skills
        for skill in all_skills:
            self.skills[skill.id] = skill
        
        # Create competencies
        self.competencies["comp_critical_respiratory"] = Competency(
            id="comp_critical_respiratory",
            name="Critical Respiratory Care",
            description="Comprehensive management of critically ill respiratory patients",
            skills=[
                "skill_ards_recognition",
                "skill_vent_setup",
                "skill_vent_monitoring",
                "skill_vent_weaning",
                "skill_pbw_calculation"
            ],
            roles=[ClinicalRole.ICU_NURSE, ClinicalRole.RESPIRATORY_THERAPIST]
        )
        
        self.competencies["comp_sepsis_care"] = Competency(
            id="comp_sepsis_care",
            name="Sepsis Recognition and Management",
            description="Identification and initial management of sepsis",
            skills=[
                "skill_sepsis_recognition",
                "skill_sepsis_management",
                "skill_critical_drug_management"
            ],
            roles=[ClinicalRole.RN, ClinicalRole.ICU_NURSE, ClinicalRole.ER_NURSE]
        )
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID"""
        return self.skills.get(skill_id)
    
    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a category"""
        return [s for s in self.skills.values() if s.category == category]
    
    def get_skills_by_role(self, role: ClinicalRole) -> List[Skill]:
        """Get all skills required for a role"""
        return [s for s in self.skills.values() if role in s.required_roles]
    
    def get_competency(self, comp_id: str) -> Optional[Competency]:
        """Get competency by ID"""
        return self.competencies.get(comp_id)
    
    def get_all_competencies(self) -> List[Competency]:
        """Get all competencies"""
        return list(self.competencies.values())
    
    def search_skills_by_keywords(self, keywords: List[str]) -> List[Skill]:
        """Find skills matching keywords (for auto-tagging)"""
        keywords_lower = [k.lower() for k in keywords]
        matching_skills = []
        
        for skill in self.skills.values():
            # Check if any keyword matches skill keywords
            skill_keywords_lower = [k.lower() for k in skill.keywords]
            if any(kw in skill_keywords_lower for kw in keywords_lower):
                matching_skills.append(skill)
        
        return matching_skills
    
    def export_to_json(self, filepath: str):
        """Export ontology to JSON"""
        data = {
            "skills": {k: v.dict() for k, v in self.skills.items()},
            "competencies": {k: v.dict() for k, v in self.competencies.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_skill_tree(self) -> Dict:
        """Get hierarchical view of skills"""
        tree = {}
        for category in SkillCategory:
            tree[category.value] = [
                {
                    "id": skill.id,
                    "name": skill.name,
                    "roles": [r.value for r in skill.required_roles]
                }
                for skill in self.get_skills_by_category(category)
            ]
        return tree