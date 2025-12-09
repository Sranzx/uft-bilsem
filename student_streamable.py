import json
import os
import requests
import PyPDF2
from docx import Document
from datetime import datetime
# 'Any' modülünü burada aktif olarak kullanacağız
from typing import List, Optional, Generator, Dict, Any
from dataclasses import dataclass, field, asdict

# --- 1. KÜTÜPHANE İMPORTLARI (PYCHARM DOSTU VERSİYON) ---
# Değişkenleri önce 'Any' tipiyle tanımlıyoruz.
# Bu, PyCharm'a "Bu değişken None olabilir ama modül de olabilir, hata verme" der.

openai: Any = None
anthropic: Any = None
genai: Any = None

try:
    import openai
except ImportError:
    pass  # Zaten yukarıda None olarak tanımlı, bir şey yapmaya gerek yok.

try:
    import anthropic
except ImportError:
    pass

try:
    import google.generativeai as genai
except ImportError:
    pass


class Config:
    DATA_DIR = "student_data"
    OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    TIMEOUT = 60


@dataclass
class Grade:
    subject: str
    score: float
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


@dataclass
class BehaviorNote:
    note: str
    type: str
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
    file_content: str = ""
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        required_keys = {"id", "name", "class_name"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"Eksik anahtarlar: {required_keys - data.keys()}")

        grades = [Grade(**g) for g in data.get("grades", [])]
        notes = [BehaviorNote(**n) for n in data.get("behavior_notes", [])]
        insights = [AIInsight(**i) for i in data.get("ai_insights", [])]

        valid_keys = {k for k in data if k in cls.__annotations__}
        filtered_data = {k: data[k] for k in valid_keys}

        # file_content manuel kontrol
        file_content = data.get("file_content", "")

        return cls(
            **filtered_data,
            grades=grades,
            behavior_notes=notes,
            ai_insights=insights
        )


class FileHandler:
    @staticmethod
    def extract_text_from_file(uploaded_file) -> str:
        text = ""
        try:
            file_type = uploaded_file.name.split('.')[-1].lower()

            if file_type == 'pdf':
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"

            elif file_type in ['docx', 'doc']:
                doc = Document(uploaded_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"

            elif file_type == 'txt':
                text = uploaded_file.getvalue().decode("utf-8")

            else:
                return f"Desteklenmeyen dosya formatı: {file_type}"

            return text[:15000] + ("..." if len(text) > 15000 else "")

        except Exception as e:
            return f"Dosya okunurken hata oluştu: {str(e)}"


class StudentManager:
    def __init__(self):
        os.makedirs(Config.DATA_DIR, exist_ok=True)

    def _get_path(self, student_id: str) -> str:
        return os.path.join(Config.DATA_DIR, f"{student_id}.json")

    def save_student(self, student: Student) -> None:
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
        except Exception:
            return None

    def get_all_students(self) -> List[Student]:
        students = []
        if not os.path.exists(Config.DATA_DIR):
            return []

        for filename in os.listdir(Config.DATA_DIR):
            if filename.endswith('.json'):
                student_id = filename.replace('.json', '')
                student = self.load_student(student_id)
                if student:
                    students.append(student)
        return students


class AIService:
    def __init__(self):
        self.provider = "Ollama"
        self.model = Config.DEFAULT_MODEL
        self.api_key = None

    def configure(self, provider: str, model: str, api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def check_connection(self) -> bool:
        if self.provider == "Ollama":
            try:
                response = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=3)
                return response.status_code == 200
            except requests.RequestException:
                return False
        return True

    def get_ollama_models(self) -> List[str]:
        if self.provider != "Ollama":
            return [self.model]
        try:
            response = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                return models if models else [Config.DEFAULT_MODEL]
            return [Config.DEFAULT_MODEL]
        except Exception:
            return [Config.DEFAULT_MODEL]

    def prepare_prompt(self, student: Student) -> str:
        summary = [f"Öğrenci: {student.name} ({student.class_name})", ""]

        if student.grades:
            summary.append("AKADEMİK PERFORMANS:")
            subjects = {}
            for grade in student.grades:
                subjects.setdefault(grade.subject, []).append(grade.score)

            for subject, scores in subjects.items():
                avg = sum(scores) / len(scores)
                summary.append(f"- {subject}: Ortalama {avg:.1f} (Notlar: {scores})")
        else:
            summary.append("AKADEMİK PERFORMANS: Veri yok.")

        if student.file_content:
            summary.append(f"\nYÜKLENEN DOSYA İÇERİĞİ:\n{student.file_content[:2000]}...")

        if student.behavior_notes:
            summary.append("\nDAVRANIŞ KAYITLARI:")
            for note in student.behavior_notes[-5:]:
                summary.append(f"- [{note.type.upper()}] {note.note} ({note.date})")

        return "\n".join(summary)

    def generate_stream(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        full_prompt = f"{system_prompt}\n\nVERİLER:\n{prompt}"

        try:
            if self.provider == "Ollama":
                yield from self._stream_ollama(full_prompt)
            elif self.provider == "OpenAI":
                yield from self._stream_openai(full_prompt, system_prompt)
            elif self.provider == "Anthropic":
                yield from self._stream_anthropic(full_prompt, system_prompt)
            elif self.provider == "Google":
                yield from self._stream_google(full_prompt)
            else:
                yield f"Hata: Bilinmeyen sağlayıcı {self.provider}"
        except Exception as e:
            yield f"Yanıt oluşturma hatası: {str(e)}"

    def _stream_ollama(self, prompt: str) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.7, "num_ctx": 4096}
        }
        try:
            with requests.post(f"{Config.OLLAMA_URL}/api/generate", json=payload, stream=True,
                               timeout=Config.TIMEOUT) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            body = json.loads(line)
                            yield body.get('response', '')
                else:
                    yield f"Ollama API Hatası: {response.status_code}"
        except Exception as e:
            yield f"Ollama Bağlantı Hatası: {str(e)}"

    def _stream_openai(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        if openai is None:
            yield "Hata: OpenAI kütüphanesi yüklü değil (pip install openai)."
            return

        try:
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
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content

        except Exception as e:
            yield f"OpenAI API Hatası: {str(e)}"

    def _stream_anthropic(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        if anthropic is None:
            yield "Hata: Anthropic kütüphanesi yüklü değil."
            return

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            with client.messages.stream(
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"Anthropic Hatası: {str(e)}"

    def _stream_google(self, prompt: str) -> Generator[str, None, None]:
        if genai is None:
            yield "Hata: Google Generative AI kütüphanesi yüklü değil."
            return

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                yield chunk.text
        except Exception as e:
            yield f"Google AI Hatası: {str(e)}"