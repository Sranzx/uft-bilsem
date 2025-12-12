import json
import os
import requests
import PyPDF2
from docx import Document
from datetime import datetime
from typing import List, Optional, Generator, Dict, Any
from dataclasses import dataclass, field, asdict

# --- Kütüphane Yüklemeleri ---
openai: Any = None
anthropic: Any = None
genai: Any = None

try:
    import openai
except ImportError:
    pass

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
        # 1. ESKİ VERİ ONARIMI (Migration)
        # Eski dosyalarda 'class' anahtarı olabilir, bunu 'class_name' yapalım.
        if "class" in data and "class_name" not in data:
            data["class_name"] = data["class"]

        # ID yoksa oluştur
        if "id" not in data:
            import uuid
            data["id"] = str(uuid.uuid4())

        # 2. ALT NESNELERİ GÜVENLİ OLUŞTURMA
        # Grade nesnesini oluştururken hata çıkarsa program çökmesin, o notu atlasın.
        grades = []
        for g in data.get("grades", []):
            try:
                # Sadece Grade sınıfının tanıdığı parametreleri gönder
                valid_g = {k: v for k, v in g.items() if k in Grade.__annotations__}
                grades.append(Grade(**valid_g))
            except:
                pass  # Bozuk not verisi varsa atla

        notes = []
        for n in data.get("behavior_notes", []):
            try:
                valid_n = {k: v for k, v in n.items() if k in BehaviorNote.__annotations__}
                notes.append(BehaviorNote(**valid_n))
            except:
                pass

        insights = []
        for i in data.get("ai_insights", []):
            try:
                valid_i = {k: v for k, v in i.items() if k in AIInsight.__annotations__}
                insights.append(AIInsight(**valid_i))
            except:
                pass

        # 3. ANA NESNEYİ OLUŞTURMA
        # Student sınıfının beklediği anahtarları ayıkla
        # Karmaşık listeleri (grades vb.) hariç tutuyoruz, onları yukarıda elle yaptık.
        exclude_fields = {"grades", "behavior_notes", "ai_insights"}

        simple_data = {}
        for k, v in data.items():
            if k in cls.__annotations__ and k not in exclude_fields:
                simple_data[k] = v

        # Eksik kalan zorunlu alanlar varsa boş doldur (Hata vermemesi için)
        if "name" not in simple_data: simple_data["name"] = "İsimsiz Öğrenci"
        if "class_name" not in simple_data: simple_data["class_name"] = ""
        if "file_content" not in simple_data: simple_data["file_content"] = ""

        # Nihai nesneyi döndür
        return cls(
            **simple_data,
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
            return text[:15000]
        except Exception as e:
            return f"Hata: {str(e)}"


class StudentManager:
    def __init__(self):
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

    def _get_path(self, student_id: str) -> str:
        return os.path.join(Config.DATA_DIR, f"{student_id}.json")

    def save_student(self, student: Student) -> None:
        student.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self._get_path(student.id), 'w', encoding='utf-8') as f:
                json.dump(student.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"Kayıt OK: {student.name}")
        except Exception as e:
            print(f"Kayıt Hatası: {e}")

    def load_student(self, student_id: str) -> Optional[Student]:
        path = self._get_path(student_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Hata olsa bile düzeltmeye çalışarak yükle
            return Student.from_dict(data)
        except Exception as e:
            print(f"⚠️ Dosya Bozuk ({student_id}): {e}")
            return None

    def get_all_students(self) -> List[Student]:
        students = []
        if not os.path.exists(Config.DATA_DIR):
            return []

        for filename in os.listdir(Config.DATA_DIR):
            if filename.endswith('.json'):
                student_id = filename.replace('.json', '')
                try:
                    student = self.load_student(student_id)
                    if student:
                        students.append(student)
                except:
                    continue  # Çok kritik hata varsa o dosyayı atla

        students.sort(key=lambda x: x.name)
        return students


class AIService:
    # (Bu kısım aynı kalabilir, sadece yapıyı koruyun)
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
            except:
                return False
        return True

    def get_ollama_models(self) -> List[str]:
        if self.provider != "Ollama": return [self.model]
        try:
            r = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m['name'] for m in r.json().get('models', [])]
                return models if models else [Config.DEFAULT_MODEL]
            return [Config.DEFAULT_MODEL]
        except:
            return [Config.DEFAULT_MODEL]

    def generate_stream(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        full = f"{system_prompt}\n\nVERİLER:\n{prompt}"
        try:
            if self.provider == "Ollama":
                yield from self._stream_ollama(full)
            else:
                yield f"Hata: {self.provider} pasif."
        except Exception as e:
            yield f"Hata: {e}"

    def _stream_ollama(self, prompt: str) -> Generator[str, None, None]:
        payload = {"model": self.model, "prompt": prompt, "stream": True, "options": {"temperature": 0.7}}
        try:
            with requests.post(f"{Config.OLLAMA_URL}/api/generate", json=payload, stream=True,
                               timeout=Config.TIMEOUT) as r:
                if r.status_code == 200:
                    for line in r.iter_lines():
                        if line:
                            yield json.loads(line).get('response', '')
                else:
                    yield f"API Hata: {r.status_code}"
        except Exception as e:
            yield f"Bağlantı Hatası: {str(e)}"