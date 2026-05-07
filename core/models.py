from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class Grade:
    subject: str
    score: float
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


@dataclass
class Homework:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    subject: str = ""
    assigned_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    due_date: str = ""
    status: str = "pending"
    file_content: str = ""
    grade: Optional[float] = None
    max_grade: float = 100.0
    feedback: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    subject: str = ""
    start_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    due_date: str = ""
    status: str = "not_started"
    file_content: str = ""
    grade: Optional[float] = None
    max_grade: float = 100.0
    feedback: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class Exam:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    subject: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    score: float = 0.0
    max_score: float = 100.0
    notes: str = ""
    exam_type: str = "exam"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class AIInsight:
    analysis: str
    model: str
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class Student:
    id: str
    name: str
    class_name: str
    enrollment_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    grades: List[Grade] = field(default_factory=list)
    homeworks: List[Homework] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    exams: List[Exam] = field(default_factory=list)
    behavior_notes: List[str] = field(default_factory=list)
    observation: str = ""
    file_content: str = ""
    ai_insights: List[AIInsight] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise ValueError("Veri formatı geçersiz")

        grades = []
        for g in data.get("grades", []):
            try:
                grades.append(Grade(**{k: v for k, v in g.items() if k in Grade.__annotations__}))
            except Exception:
                continue

        homeworks = []
        for h in data.get("homeworks", []):
            try:
                hw_data = {k: v for k, v in h.items() if k in Homework.__annotations__}
                homeworks.append(Homework(**hw_data))
            except Exception:
                continue

        projects = []
        for p in data.get("projects", []):
            try:
                proj_data = {k: v for k, v in p.items() if k in Project.__annotations__}
                projects.append(Project(**proj_data))
            except Exception:
                continue

        exams = []
        for e in data.get("exams", []):
            try:
                exam_data = {k: v for k, v in e.items() if k in Exam.__annotations__}
                exams.append(Exam(**exam_data))
            except Exception:
                continue

        insights = []
        for i in data.get("ai_insights", []):
            try:
                insight_data = {k: v for k, v in i.items() if k in AIInsight.__annotations__}
                insights.append(AIInsight(**insight_data))
            except Exception:
                continue

        simple_data = {}
        exclude = {"grades", "homeworks", "projects", "exams", "ai_insights", "behavior_notes"}
        for k, v in data.items():
            if k in cls.__annotations__ and k not in exclude:
                simple_data[k] = v

        if "class" in data and "class_name" not in simple_data:
            simple_data["class_name"] = data["class"]

        simple_data.setdefault("name", "İsimsiz Öğrenci")
        simple_data.setdefault("class_name", "")
        simple_data.setdefault("file_content", "")
        simple_data.setdefault("observation", "")

        behavior = data.get("behavior_notes", [])
        if behavior and isinstance(behavior[0], dict):
            behavior = [b.get("note", str(b)) for b in behavior]

        return cls(
            **simple_data,
            grades=grades,
            homeworks=homeworks,
            projects=projects,
            exams=exams,
            behavior_notes=behavior,
            ai_insights=insights
        )


HOMEWORK_STATUSES = {
    "pending": "📋 Bekliyor",
    "submitted": "📤 Teslim Edildi",
    "graded": "✅ Notlandı",
    "late": "⏰ Geç Teslim"
}

PROJECT_STATUSES = {
    "not_started": "⏳ Başlanmadı",
    "in_progress": "🔧 Devam Ediyor",
    "submitted": "📤 Teslim Edildi",
    "graded": "✅ Notlandı"
}

EXAM_TYPES = {
    "exam": "📝 Sınav",
    "quiz": "❓ Quiz",
    "test": "📋 Test",
    "oral": "🎤 Sözlü"
}

DEFAULT_SUBJECTS = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü"]
