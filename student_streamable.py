import json
import os
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

# --- EKSTRA AI KÜTÜPHANELERİ (Opsiyonel) ---
try:
    import openai
except ImportError:
    openai = None
try:
    import anthropic
except ImportError:
    anthropic = None
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# --- GÖRSELLEŞTİRME (Rich) ---
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.prompt import Prompt, FloatPrompt

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# --- KONFIGÜRASYON ---
class Config:
    DATA_DIR = "student_data"
    OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    TIMEOUT = 60


# --- VERİ MODELLERİ ---
@dataclass
class Grade:
    subject: str
    score: float
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


@dataclass
class BehaviorNote:
    note: str
    type: str  # positive, negative, neutral
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


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
    behavior_notes: List[BehaviorNote] = field(default_factory=list)
    ai_insights: List[AIInsight] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        # Hata Toleransı: Zorunlu alan kontrolü
        REQUIRED_KEYS = ["id", "name", "class_name"]
        if not all(k in data for k in REQUIRED_KEYS):
            raise ValueError(f"Eksik veri: {REQUIRED_KEYS} alanları zorunludur.")

        grades = [Grade(**g) for g in data.get("grades", [])]
        notes = [BehaviorNote(**n) for n in data.get("behavior_notes", [])]
        insights = [AIInsight(**i) for i in data.get("ai_insights", [])]

        clean_data = {k: v for k, v in data.items() if k in cls.__annotations__}

        return cls(
            **{**clean_data,
               "grades": grades,
               "behavior_notes": notes,
               "ai_insights": insights}
        )


# --- İŞ MANTIĞI (Manager) ---
class StudentManager:
    def __init__(self):
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

    def _get_path(self, student_id: str) -> str:
        return os.path.join(Config.DATA_DIR, f"{student_id}.json")

    def save_student(self, student: Student):
        student.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self._get_path(student.id), 'w', encoding='utf-8') as f:
            json.dump(student.to_dict(), f, ensure_ascii=False, indent=2)

    def load_student(self, student_id: str) -> Optional[Student]:
        path = self._get_path(student_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Student.from_dict(data)
        except Exception as e:
            print(f"❌ Dosya okuma hatası ({student_id}): {e}")
            return None

    def get_all_students(self) -> List[Student]:
        students = []
        if not os.path.exists(Config.DATA_DIR):
            return []
        for f in os.listdir(Config.DATA_DIR):
            if f.endswith('.json'):
                student = self.load_student(f.replace('.json', ''))
                if student:
                    students.append(student)
        return students


# --- GÜNCELLENMİŞ AI SERVİSİ (Çoklu Sağlayıcı) ---
class AIService:
    def __init__(self):
        self.provider = "Ollama"
        self.model = Config.DEFAULT_MODEL
        self.api_key = None
        self.console = Console() if RICH_AVAILABLE else None

    def set_provider_config(self, provider: str, model: str, api_key: str = None):
        """Arayüzden gelen ayarları uygular"""
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def check_connection(self) -> bool:
        """Sadece Ollama için ping atar, diğerleri için True döner (API key kontrolü streaming sırasında yapılır)"""
        if self.provider == "Ollama":
            try:
                response = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=3)
                return response.status_code == 200
            except:
                return False
        return True

    def prepare_student_prompt(self, student: Student) -> str:
        summary = f"Öğrenci: {student.name} ({student.class_name})\n\nAKADEMİK:\n"
        if not student.grades:
            summary += "Henüz not girişi yok.\n"

        subjects = {}
        for g in student.grades:
            subjects.setdefault(g.subject, []).append(g.score)

        for subj, scores in subjects.items():
            avg = sum(scores) / len(scores)
            summary += f"- {subj}: Ort {avg:.1f} (Notlar: {scores})\n"

        summary += "\nDAVRANIŞ:\n"
        for note in student.behavior_notes[-5:]:
            summary += f"- [{note.type.upper()}] {note.note}\n"

        return summary

    def generate_streaming_response(self, prompt: str, system_prompt: str):
        """Seçilen sağlayıcıya göre streaming yanıt üretir"""
        full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
            # 1. OLLAMA
            if self.provider == "Ollama":
                payload = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {"temperature": 0.3, "num_ctx": 2048}
                }
                with requests.post(f"{Config.OLLAMA_URL}/api/generate", json=payload, stream=True,
                                   timeout=Config.TIMEOUT) as r:
                    for line in r.iter_lines():
                        if line:
                            body = json.loads(line)
                            yield body.get('response', '')

            # 2. OPENAI (ChatGPT)
            elif self.provider == "OpenAI":
                if not openai: raise ImportError("OpenAI kütüphanesi yüklü değil.")
                client = openai.OpenAI(api_key=self.api_key)
                stream = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content

            # 3. ANTHROPIC (Claude)
            elif self.provider == "Anthropic":
                if not anthropic: raise ImportError("Anthropic kütüphanesi yüklü değil.")
                client = anthropic.Anthropic(api_key=self.api_key)
                with client.messages.stream(
                        max_tokens=1024,
                        system=system_prompt,
                        messages=[{"role": "user", "content": prompt}],
                        model=self.model
                ) as stream:
                    for text in stream.text_stream:
                        yield text

            # 4. GOOGLE (Gemini)
            elif self.provider == "Google":
                if not genai: raise ImportError("Google Generative AI kütüphanesi yüklü değil.")
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model)
                response = model.generate_content(full_prompt, stream=True)
                for chunk in response:
                    yield chunk.text

        except Exception as e:
            yield f"\n❌ HATA ({self.provider}): {str(e)}"


# --- CLI ARAYÜZÜ (Opsiyonel Test İçin) ---
if __name__ == "__main__":
    print("Bu dosya bir modüldür. Arayüz için 'streamlit run app.py' çalıştırın.")