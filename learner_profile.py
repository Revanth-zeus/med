from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
import json
from pathlib import Path

class QuestionAttempt(BaseModel):
    """Single question attempt"""
    question_id: str
    skill_ids: List[str]
    topic: str
    difficulty: str
    question_type: str
    correct: bool
    timestamp: datetime
    time_spent_seconds: Optional[int] = None
    exam_session_id: Optional[str] = None  # NEW: Track which exam this came from

class SkillPerformance(BaseModel):
    """Performance on a specific skill"""
    skill_id: str
    total_attempts: int
    correct_attempts: int
    accuracy: float
    last_attempted: datetime
    proficiency_level: str

class TopicPerformance(BaseModel):
    """Performance on a specific topic"""
    topic: str
    total_attempts: int
    correct_attempts: int
    accuracy: float
    last_attempted: datetime

class ExamRecord(BaseModel):
    """Record of a completed exam"""
    exam_id: str
    mode: str
    total_questions: int
    correct_answers: int
    score: float
    duration_minutes: float
    completed_at: datetime
    topics_tested: List[str]
    skills_tested: List[str]

class LearnerProfile(BaseModel):
    """Complete learner profile"""
    learner_id: str
    name: str
    role: str
    attempts: List[QuestionAttempt] = []
    skill_performance: Dict[str, SkillPerformance] = {}
    topic_performance: Dict[str, TopicPerformance] = {}  # NEW: Track by topic
    exam_history: List[ExamRecord] = []  # NEW: Track exam history
    created_at: datetime
    updated_at: datetime

class LearnerProfileManager:
    """Manage learner profiles and performance tracking"""
    
    def __init__(self, data_dir: str = "learner_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.profiles: Dict[str, LearnerProfile] = {}
        self._load_profiles()
    
    def _load_profiles(self):
        """Load existing profiles from disk"""
        for profile_file in self.data_dir.glob("*.json"):
            try:
                with open(profile_file, 'r') as f:
                    data = json.load(f)
                    # Handle migration for older profiles without new fields
                    if 'topic_performance' not in data:
                        data['topic_performance'] = {}
                    if 'exam_history' not in data:
                        data['exam_history'] = []
                    profile = LearnerProfile(**data)
                    self.profiles[profile.learner_id] = profile
            except Exception as e:
                print(f"Error loading profile {profile_file}: {e}")
    
    def _save_profile(self, profile: LearnerProfile):
        """Save profile to disk"""
        filepath = self.data_dir / f"{profile.learner_id}.json"
        with open(filepath, 'w') as f:
            json.dump(profile.dict(), f, indent=2, default=str)
    
    def create_profile(self, learner_id: str, name: str, role: str) -> LearnerProfile:
        """Create new learner profile"""
        if learner_id in self.profiles:
            return self.profiles[learner_id]
        
        profile = LearnerProfile(
            learner_id=learner_id,
            name=name,
            role=role,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.profiles[learner_id] = profile
        self._save_profile(profile)
        return profile
    
    def get_profile(self, learner_id: str) -> Optional[LearnerProfile]:
        """Get learner profile"""
        return self.profiles.get(learner_id)
    
    def record_attempt(self, learner_id: str, attempt: QuestionAttempt):
        """Record a question attempt"""
        profile = self.profiles.get(learner_id)
        if not profile:
            raise ValueError(f"Profile not found: {learner_id}")
        
        # Add attempt
        profile.attempts.append(attempt)
        
        # Update skill performance
        for skill_id in attempt.skill_ids:
            if skill_id not in profile.skill_performance:
                profile.skill_performance[skill_id] = SkillPerformance(
                    skill_id=skill_id,
                    total_attempts=0,
                    correct_attempts=0,
                    accuracy=0.0,
                    last_attempted=attempt.timestamp,
                    proficiency_level="novice"
                )
            
            perf = profile.skill_performance[skill_id]
            perf.total_attempts += 1
            if attempt.correct:
                perf.correct_attempts += 1
            perf.accuracy = perf.correct_attempts / perf.total_attempts
            perf.last_attempted = attempt.timestamp
            perf.proficiency_level = self._calculate_proficiency(
                perf.accuracy, 
                perf.total_attempts
            )
        
        # NEW: Update topic performance
        topic = attempt.topic.lower().strip()
        if topic:
            if topic not in profile.topic_performance:
                profile.topic_performance[topic] = TopicPerformance(
                    topic=topic,
                    total_attempts=0,
                    correct_attempts=0,
                    accuracy=0.0,
                    last_attempted=attempt.timestamp
                )
            
            topic_perf = profile.topic_performance[topic]
            topic_perf.total_attempts += 1
            if attempt.correct:
                topic_perf.correct_attempts += 1
            topic_perf.accuracy = topic_perf.correct_attempts / topic_perf.total_attempts
            topic_perf.last_attempted = attempt.timestamp
        
        profile.updated_at = datetime.now()
        self._save_profile(profile)
    
    def record_exam_completion(self, learner_id: str, exam_record: ExamRecord):
        """Record a completed exam"""
        profile = self.profiles.get(learner_id)
        if not profile:
            raise ValueError(f"Profile not found: {learner_id}")
        
        profile.exam_history.append(exam_record)
        profile.updated_at = datetime.now()
        self._save_profile(profile)
    
    def _calculate_proficiency(self, accuracy: float, attempts: int) -> str:
        """Calculate proficiency level"""
        if attempts < 2:
            return "novice"
        elif attempts < 4:
            return "beginner" if accuracy >= 0.5 else "novice"
        elif attempts < 8:
            if accuracy >= 0.8:
                return "advanced"
            elif accuracy >= 0.6:
                return "intermediate"
            else:
                return "beginner"
        else:
            if accuracy >= 0.85:
                return "expert"
            elif accuracy >= 0.75:
                return "advanced"
            elif accuracy >= 0.6:
                return "intermediate"
            else:
                return "beginner"
    
    def get_skill_gaps(self, learner_id: str) -> List[Dict]:
        """Identify skill gaps (low performance skills) - LOWERED THRESHOLDS"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return []
        
        gaps = []
        for skill_id, perf in profile.skill_performance.items():
            # CHANGED: Lowered threshold from 3 attempts to 1
            if perf.accuracy < 0.7 and perf.total_attempts >= 1:
                gaps.append({
                    "skill_id": skill_id,
                    "accuracy": perf.accuracy,
                    "attempts": perf.total_attempts,
                    "proficiency": perf.proficiency_level
                })
        
        gaps.sort(key=lambda x: x['accuracy'])
        return gaps
    
    def get_strengths(self, learner_id: str) -> List[Dict]:
        """Identify strengths (high performance skills) - LOWERED THRESHOLDS"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return []
        
        strengths = []
        for skill_id, perf in profile.skill_performance.items():
            # CHANGED: Lowered threshold from 5 attempts to 1, and 85% to 70%
            if perf.accuracy >= 0.7 and perf.total_attempts >= 1:
                strengths.append({
                    "skill_id": skill_id,
                    "accuracy": perf.accuracy,
                    "attempts": perf.total_attempts,
                    "proficiency": perf.proficiency_level
                })
        
        strengths.sort(key=lambda x: x['accuracy'], reverse=True)
        return strengths
    
    def get_topic_strengths(self, learner_id: str) -> List[Dict]:
        """Get topics where user performs well"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return []
        
        strengths = []
        for topic, perf in profile.topic_performance.items():
            if perf.accuracy >= 0.7 and perf.total_attempts >= 1:
                strengths.append({
                    "topic": topic.title(),
                    "accuracy": perf.accuracy,
                    "attempts": perf.total_attempts,
                    "correct": perf.correct_attempts
                })
        
        strengths.sort(key=lambda x: x['accuracy'], reverse=True)
        return strengths
    
    def get_topic_weaknesses(self, learner_id: str) -> List[Dict]:
        """Get topics where user needs improvement"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return []
        
        weaknesses = []
        for topic, perf in profile.topic_performance.items():
            if perf.accuracy < 0.7 and perf.total_attempts >= 1:
                weaknesses.append({
                    "topic": topic.title(),
                    "accuracy": perf.accuracy,
                    "attempts": perf.total_attempts,
                    "correct": perf.correct_attempts
                })
        
        weaknesses.sort(key=lambda x: x['accuracy'])
        return weaknesses
    
    def get_exam_history(self, learner_id: str, limit: int = 10) -> List[Dict]:
        """Get recent exam history"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return []
        
        # Return most recent exams first
        exams = sorted(
            profile.exam_history, 
            key=lambda x: x.completed_at, 
            reverse=True
        )[:limit]
        
        return [exam.dict() for exam in exams]
    
    def get_radar_chart_data(self, learner_id: str, skill_ids: List[str]) -> Dict:
        """Get data formatted for radar chart"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return {"labels": [], "data": []}
        
        labels = []
        data = []
        
        for skill_id in skill_ids:
            perf = profile.skill_performance.get(skill_id)
            if perf:
                labels.append(skill_id.replace('skill_', '').replace('_', ' ').title())
                data.append(round(perf.accuracy * 100, 1))
            else:
                labels.append(skill_id.replace('skill_', '').replace('_', ' ').title())
                data.append(0)
        
        return {
            "labels": labels,
            "data": data
        }
    
    def get_all_performance_data(self, learner_id: str) -> Dict:
        """Get comprehensive performance data for dashboard"""
        profile = self.profiles.get(learner_id)
        if not profile:
            return {}
        
        total_questions = len(profile.attempts)
        correct_questions = sum(1 for a in profile.attempts if a.correct)
        overall_accuracy = (correct_questions / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "total_questions": total_questions,
            "correct_questions": correct_questions,
            "overall_accuracy": round(overall_accuracy, 1),
            "skills_practiced": len(profile.skill_performance),
            "topics_practiced": len(profile.topic_performance),
            "exams_completed": len(profile.exam_history),
            "skill_performance": {k: v.dict() for k, v in profile.skill_performance.items()},
            "topic_performance": {k: v.dict() for k, v in profile.topic_performance.items()},
            "topic_strengths": self.get_topic_strengths(learner_id),
            "topic_weaknesses": self.get_topic_weaknesses(learner_id),
            "skill_strengths": self.get_strengths(learner_id),
            "skill_gaps": self.get_skill_gaps(learner_id),
            "recent_exams": self.get_exam_history(learner_id, 5)
        }