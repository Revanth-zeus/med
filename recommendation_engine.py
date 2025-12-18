from typing import List, Dict
from learner_profile import LearnerProfileManager
from skills_ontology import SkillsOntology

class RecommendationEngine:
    """Generate personalized study recommendations"""
    
    def __init__(self, learner_manager: LearnerProfileManager, skills_ontology: SkillsOntology):
        self.learner_manager = learner_manager
        self.skills_ontology = skills_ontology
    
    def get_weak_skills(self, learner_id: str, threshold: float = 0.7) -> List[Dict]:
        """Identify skills below threshold - LOWERED THRESHOLD"""
        gaps = self.learner_manager.get_skill_gaps(learner_id)
        
        weak_skills = []
        for gap in gaps:
            # CHANGED: Accept any skill with accuracy < threshold (removed attempt minimum)
            if gap['accuracy'] < threshold:
                skill = self.skills_ontology.get_skill(gap['skill_id'])
                skill_name = skill.name if skill else gap['skill_id'].replace('skill_', '').replace('_', ' ').title()
                category = skill.category.value if skill else "General"
                
                weak_skills.append({
                    "skill_id": gap['skill_id'],
                    "skill_name": skill_name,
                    "category": category,
                    "accuracy": gap['accuracy'],
                    "attempts": gap['attempts'],
                    "improvement_needed": threshold - gap['accuracy']
                })
        
        weak_skills.sort(key=lambda x: x['accuracy'])
        return weak_skills[:5]
    
    def get_weak_topics(self, learner_id: str, threshold: float = 0.7) -> List[Dict]:
        """Identify topics where user needs improvement"""
        weaknesses = self.learner_manager.get_topic_weaknesses(learner_id)
        
        weak_topics = []
        for topic_info in weaknesses:
            if topic_info['accuracy'] < threshold:
                weak_topics.append({
                    "topic": topic_info['topic'],
                    "accuracy": topic_info['accuracy'],
                    "attempts": topic_info['attempts'],
                    "correct": topic_info['correct'],
                    "improvement_needed": threshold - topic_info['accuracy'],
                    "priority": "high" if topic_info['accuracy'] < 0.5 else "medium"
                })
        
        weak_topics.sort(key=lambda x: x['accuracy'])
        return weak_topics[:5]
    
    def get_strong_topics(self, learner_id: str, threshold: float = 0.7) -> List[Dict]:
        """Identify topics where user performs well"""
        strengths = self.learner_manager.get_topic_strengths(learner_id)
        
        strong_topics = []
        for topic_info in strengths:
            if topic_info['accuracy'] >= threshold:
                strong_topics.append({
                    "topic": topic_info['topic'],
                    "accuracy": topic_info['accuracy'],
                    "attempts": topic_info['attempts'],
                    "correct": topic_info['correct']
                })
        
        strong_topics.sort(key=lambda x: x['accuracy'], reverse=True)
        return strong_topics[:5]
    
    def get_recommended_topics(self, learner_id: str) -> List[Dict]:
        """Get recommended topics based on weak skills and topics"""
        weak_skills = self.get_weak_skills(learner_id)
        weak_topics = self.get_weak_topics(learner_id)
        
        recommendations = []
        
        # Add topic-based recommendations
        for topic_info in weak_topics:
            recommendations.append({
                "skill_name": topic_info['topic'],
                "recommended_topics": [topic_info['topic']],
                "current_accuracy": f"{topic_info['accuracy']*100:.0f}%",
                "target_accuracy": "80%",
                "recommended_questions": 5,
                "priority": topic_info['priority'],
                "type": "topic"
            })
        
        # Add skill-based recommendations
        for skill_info in weak_skills:
            skill = self.skills_ontology.get_skill(skill_info['skill_id'])
            if skill:
                topic_map = {
                    "skill_ards_recognition": ["ARDS", "respiratory distress"],
                    "skill_vent_setup": ["mechanical ventilation", "ventilator settings"],
                    "skill_vent_monitoring": ["ABG interpretation", "ventilator alarms"],
                    "skill_sepsis_recognition": ["sepsis", "septic shock"],
                    "skill_sepsis_management": ["sepsis bundle", "fluid resuscitation"],
                    "skill_medication_admin": ["medication safety", "IV administration"],
                    "skill_critical_drug_management": ["vasoactive drugs", "high-alert medications"]
                }
                
                topics = topic_map.get(skill_info['skill_id'], [skill.name])
                
                recommendations.append({
                    "skill_name": skill.name,
                    "recommended_topics": topics,
                    "current_accuracy": f"{skill_info['accuracy']*100:.0f}%",
                    "target_accuracy": "80%",
                    "recommended_questions": 5,
                    "priority": "high" if skill_info['accuracy'] < 0.5 else "medium",
                    "type": "skill"
                })
        
        # Remove duplicates and limit
        seen = set()
        unique_recs = []
        for rec in recommendations:
            key = rec['skill_name'].lower()
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
        
        return unique_recs[:8]
    
    def generate_focused_exam(self, learner_id: str, num_questions: int = 10) -> Dict:
        """Generate exam focused on weak areas"""
        weak_skills = self.get_weak_skills(learner_id)
        weak_topics = self.get_weak_topics(learner_id)
        
        if not weak_skills and not weak_topics:
            return {
                "focus": "comprehensive_review",
                "message": "Great job! No major gaps identified. This will be a comprehensive review.",
                "skill_distribution": {},
                "topic_distribution": {}
            }
        
        # Distribute questions across weak areas
        skill_distribution = {}
        topic_distribution = {}
        
        # Prioritize topics over skills since they're more specific
        total_weak = len(weak_topics) + len(weak_skills)
        questions_per_area = max(2, num_questions // max(total_weak, 1))
        
        for topic_info in weak_topics[:3]:
            topic_distribution[topic_info['topic']] = {
                "num_questions": questions_per_area,
                "current_accuracy": f"{topic_info['accuracy']*100:.0f}%"
            }
        
        for skill_info in weak_skills[:2]:
            skill_distribution[skill_info['skill_id']] = {
                "skill_name": skill_info['skill_name'],
                "num_questions": questions_per_area,
                "current_accuracy": f"{skill_info['accuracy']*100:.0f}%"
            }
        
        focus_areas = [t['topic'] for t in weak_topics[:3]] + [s['skill_name'] for s in weak_skills[:2]]
        
        return {
            "focus": "gap_remediation",
            "message": f"This exam focuses on your {len(focus_areas)} weakest areas: {', '.join(focus_areas)}",
            "skill_distribution": skill_distribution,
            "topic_distribution": topic_distribution,
            "recommended_topics": focus_areas
        }
    
    def get_next_milestone(self, learner_id: str) -> Dict:
        """Calculate next learning milestone"""
        profile = self.learner_manager.get_profile(learner_id)
        if not profile:
            return {
                "current": "Novice",
                "next": "Beginner",
                "progress": "0/3",
                "description": "Practice 3 different topics"
            }
        
        # Get performance data
        perf_data = self.learner_manager.get_all_performance_data(learner_id)
        
        total_questions = perf_data.get('total_questions', 0)
        topics_practiced = perf_data.get('topics_practiced', 0)
        exams_completed = perf_data.get('exams_completed', 0)
        overall_accuracy = perf_data.get('overall_accuracy', 0)
        
        milestones = [
            {
                "name": "Beginner",
                "check": lambda: total_questions >= 5,
                "progress": f"{min(total_questions, 5)}/5 questions",
                "description": "Answer 5 questions"
            },
            {
                "name": "Explorer",
                "check": lambda: topics_practiced >= 3,
                "progress": f"{min(topics_practiced, 3)}/3 topics",
                "description": "Practice 3 different topics"
            },
            {
                "name": "Committed",
                "check": lambda: exams_completed >= 3,
                "progress": f"{min(exams_completed, 3)}/3 exams",
                "description": "Complete 3 exams"
            },
            {
                "name": "Proficient",
                "check": lambda: total_questions >= 25 and overall_accuracy >= 70,
                "progress": f"{total_questions}/25 questions, {overall_accuracy:.0f}%/70% accuracy",
                "description": "Answer 25 questions with 70%+ accuracy"
            },
            {
                "name": "Expert",
                "check": lambda: total_questions >= 50 and overall_accuracy >= 85,
                "progress": f"{total_questions}/50 questions, {overall_accuracy:.0f}%/85% accuracy",
                "description": "Answer 50 questions with 85%+ accuracy"
            },
            {
                "name": "Master",
                "check": lambda: total_questions >= 100 and overall_accuracy >= 90,
                "progress": f"{total_questions}/100 questions, {overall_accuracy:.0f}%/90% accuracy",
                "description": "Answer 100 questions with 90%+ accuracy"
            }
        ]
        
        current_milestone = "Novice"
        next_milestone = milestones[0]
        
        for i, milestone in enumerate(milestones):
            if milestone["check"]():
                current_milestone = milestone["name"]
                if i + 1 < len(milestones):
                    next_milestone = milestones[i + 1]
                else:
                    next_milestone = None
            else:
                next_milestone = milestone
                break
        
        if next_milestone:
            return {
                "current": current_milestone,
                "next": next_milestone["name"],
                "progress": next_milestone["progress"],
                "description": next_milestone["description"]
            }
        else:
            return {
                "current": current_milestone,
                "next": "Master",
                "progress": "Complete",
                "description": "You've mastered all milestones!"
            }
    
    def get_comprehensive_recommendations(self, learner_id: str) -> Dict:
        """Get all recommendation data in one call"""
        profile = self.learner_manager.get_profile(learner_id)
        if not profile:
            return {
                "has_data": False,
                "message": "No profile found. Create a profile to get recommendations."
            }
        
        perf_data = self.learner_manager.get_all_performance_data(learner_id)
        
        if perf_data.get('total_questions', 0) == 0:
            return {
                "has_data": False,
                "message": "Complete some questions to get personalized recommendations."
            }
        
        return {
            "has_data": True,
            "overall_accuracy": perf_data.get('overall_accuracy', 0),
            "total_questions": perf_data.get('total_questions', 0),
            "exams_completed": perf_data.get('exams_completed', 0),
            "topics_practiced": perf_data.get('topics_practiced', 0),
            "milestone": self.get_next_milestone(learner_id),
            "weak_topics": self.get_weak_topics(learner_id),
            "strong_topics": self.get_strong_topics(learner_id),
            "weak_skills": self.get_weak_skills(learner_id),
            "recommendations": self.get_recommended_topics(learner_id),
            "focused_exam": self.generate_focused_exam(learner_id),
            "recent_exams": perf_data.get('recent_exams', [])
        }