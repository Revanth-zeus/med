from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
from pathlib import Path
import random

try:
    from learner_profile import LearnerProfileManager, QuestionAttempt, ExamRecord
except ImportError:
    LearnerProfileManager = None
    QuestionAttempt = None
    ExamRecord = None

class ExamQuestion(BaseModel):
    """Single question in exam"""
    question_id: str
    topic: str
    difficulty: str
    question_type: str
    skill_ids: List[str]
    question_data: dict
    user_answer: Optional[str] = None
    correct_answer: str
    is_correct: Optional[bool] = None
    time_spent_seconds: Optional[int] = None
    timestamp: Optional[datetime] = None

class ExamSession(BaseModel):
    """Complete exam session"""
    session_id: str
    learner_id: str
    mode: str  # "practice", "timed", "adaptive"
    total_questions: int
    time_limit_minutes: Optional[int] = None
    questions: List[ExamQuestion] = []
    current_question_index: int = 0
    start_time: datetime
    end_time: Optional[datetime] = None
    score: Optional[float] = None
    status: str = "in_progress"  # "in_progress", "completed", "abandoned"
    
class ExamSessionManager:
    """Manage exam sessions with adaptive logic and learner profile integration"""
    
    def __init__(self, learner_manager: LearnerProfileManager, data_dir: str = "exam_sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, ExamSession] = {}
        self.learner_manager = learner_manager
        self._load_sessions()
    
    def _load_sessions(self):
        """Load existing sessions"""
        for session_file in self.data_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    session = ExamSession(**data)
                    self.sessions[session.session_id] = session
            except Exception as e:
                print(f"Error loading session {session_file}: {e}")
    
    def _save_session(self, session: ExamSession):
        """Save session to disk"""
        filepath = self.data_dir / f"{session.session_id}.json"
        with open(filepath, 'w') as f:
            json.dump(session.dict(), f, indent=2, default=str)
    
    def create_session(
        self,
        learner_id: str,
        mode: str,
        total_questions: int,
        time_limit_minutes: Optional[int] = None,
        focus_skills: Optional[List[str]] = None
    ) -> ExamSession:
        """Create new exam session"""
        session_id = f"exam_{learner_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = ExamSession(
            session_id=session_id,
            learner_id=learner_id,
            mode=mode,
            total_questions=total_questions,
            time_limit_minutes=time_limit_minutes,
            start_time=datetime.now()
        )
        
        self.sessions[session_id] = session
        self._save_session(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[ExamSession]:
        """Get exam session"""
        return self.sessions.get(session_id)
    
    def get_learner_sessions(self, learner_id: str) -> List[ExamSession]:
        """Get all sessions for a learner"""
        return [s for s in self.sessions.values() if s.learner_id == learner_id]
    
    def add_question_to_session(
        self,
        session_id: str,
        question_id: str,
        topic: str,
        difficulty: str,
        question_type: str,
        skill_ids: List[str],
        question_data: dict,
        correct_answer: str
    ):
        """Add generated question to session"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Ensure skill_ids is not empty - use topic-based fallback
        if not skill_ids:
            skill_ids = [f"topic_{topic.lower().replace(' ', '_')}"]
        
        question = ExamQuestion(
            question_id=question_id,
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            skill_ids=skill_ids,
            question_data=question_data,
            correct_answer=correct_answer
        )
        
        session.questions.append(question)
        self._save_session(session)
    
    def submit_answer(
        self,
        session_id: str,
        question_index: int,
        user_answer: str,
        time_spent_seconds: int
    ) -> Dict:
        """Submit answer and record to learner profile"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if question_index >= len(session.questions):
            raise ValueError(f"Question index {question_index} out of range")
        
        question = session.questions[question_index]
        question.user_answer = user_answer
        question.time_spent_seconds = time_spent_seconds
        question.timestamp = datetime.now()
        
        # Determine correctness
        question.is_correct = (user_answer == question.correct_answer)
        
        print(f"📝 Recording attempt: topic={question.topic}, correct={question.is_correct}, skills={question.skill_ids}")
        
        # Ensure we have skill_ids - fallback to topic-based if empty
        skill_ids = question.skill_ids if question.skill_ids else [f"topic_{question.topic.lower().replace(' ', '_')}"]
        
        # Record to learner profile
        if QuestionAttempt:
            attempt = QuestionAttempt(
                question_id=question.question_id,
                skill_ids=skill_ids,
                topic=question.topic,
                difficulty=question.difficulty,
                question_type=question.question_type,
                correct=question.is_correct,
                timestamp=question.timestamp,
                time_spent_seconds=time_spent_seconds,
                exam_session_id=session_id
            )
            
            try:
                self.learner_manager.record_attempt(session.learner_id, attempt)
                print(f"✅ Attempt recorded successfully for learner {session.learner_id}")
            except Exception as e:
                print(f"❌ Error recording attempt: {e}")
        
        self._save_session(session)
        
        return {
            "is_correct": question.is_correct,
            "correct_answer": question.correct_answer,
            "rationale": question.question_data.get("rationale", "")
        }
    
    def complete_session(self, session_id: str) -> Dict:
        """Complete exam session and calculate final score"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.end_time = datetime.now()
        session.status = "completed"
        
        # Calculate score
        total = len(session.questions)
        correct = sum(1 for q in session.questions if q.is_correct)
        session.score = (correct / total * 100) if total > 0 else 0
        
        self._save_session(session)
        
        # Calculate duration
        duration = session.end_time - session.start_time
        duration_minutes = duration.total_seconds() / 60
        
        # Record exam completion to learner profile
        if ExamRecord and self.learner_manager:
            try:
                topics_tested = list(set(q.topic for q in session.questions))
                skills_tested = list(set(
                    skill for q in session.questions 
                    for skill in (q.skill_ids if q.skill_ids else [f"topic_{q.topic.lower().replace(' ', '_')}"])
                ))
                
                exam_record = ExamRecord(
                    exam_id=session_id,
                    mode=session.mode,
                    total_questions=total,
                    correct_answers=correct,
                    score=session.score,
                    duration_minutes=round(duration_minutes, 2),
                    completed_at=session.end_time,
                    topics_tested=topics_tested,
                    skills_tested=skills_tested
                )
                
                self.learner_manager.record_exam_completion(session.learner_id, exam_record)
                print(f"✅ Exam record saved: {session_id}")
            except Exception as e:
                print(f"❌ Error recording exam completion: {e}")
        
        return {
            "score": session.score,
            "correct": correct,
            "total": total,
            "duration_minutes": duration_minutes
        }
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get detailed session summary"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Difficulty performance
        difficulty_perf = {
            "beginner": {"correct": 0, "total": 0},
            "intermediate": {"correct": 0, "total": 0},
            "advanced": {"correct": 0, "total": 0}
        }
        
        # Skill performance
        skill_perf = {}
        
        # Topic performance
        topic_perf = {}
        
        for question in session.questions:
            # Difficulty breakdown
            diff = question.difficulty
            if diff in difficulty_perf:
                difficulty_perf[diff]["total"] += 1
                if question.is_correct:
                    difficulty_perf[diff]["correct"] += 1
            
            # Skill breakdown
            skill_ids = question.skill_ids if question.skill_ids else [f"topic_{question.topic.lower().replace(' ', '_')}"]
            for skill_id in skill_ids:
                if skill_id not in skill_perf:
                    skill_perf[skill_id] = {"correct": 0, "total": 0}
                skill_perf[skill_id]["total"] += 1
                if question.is_correct:
                    skill_perf[skill_id]["correct"] += 1
            
            # Topic breakdown
            topic = question.topic
            if topic not in topic_perf:
                topic_perf[topic] = {"correct": 0, "total": 0}
            topic_perf[topic]["total"] += 1
            if question.is_correct:
                topic_perf[topic]["correct"] += 1
        
        return {
            "session_id": session_id,
            "mode": session.mode,
            "score": session.score,
            "difficulty_performance": difficulty_perf,
            "skill_performance": skill_perf,
            "topic_performance": topic_perf
        }
    
    def get_adaptive_next_difficulty(self, session_id: str) -> str:
        """Calculate next difficulty based on recent performance"""
        session = self.sessions.get(session_id)
        if not session or len(session.questions) < 3:
            return "intermediate"
        
        # Look at last 3 answered questions
        recent = [q for q in session.questions if q.is_correct is not None][-3:]
        if not recent:
            return "intermediate"
        
        correct_count = sum(1 for q in recent if q.is_correct)
        current_diff = recent[-1].difficulty if recent else "intermediate"
        
        if correct_count >= 2:  # Doing well
            if current_diff == "beginner":
                return "intermediate"
            elif current_diff == "intermediate":
                return "advanced"
            return "advanced"
        elif correct_count <= 1:  # Struggling
            if current_diff == "advanced":
                return "intermediate"
            elif current_diff == "intermediate":
                return "beginner"
            return "beginner"
        
        return current_diff