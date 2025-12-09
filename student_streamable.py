import json
import os
import requests
import PyPDF2
from docx import Document
from datetime import datetime
from typing import List, Optional, Generator, Dict, Any
from dataclasses import dataclass, field, asdict

# --- Kütüphane Yüklemeleri (Hata Önleyici) ---
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
        # --- OTOMATİK DÜZELTME BLOĞU (ESKİ VERİLER İÇİN) ---
        # Eski JSON'larda 'class' olabilir, biz 'class_name' istiyoruz.
        if "class" in data and "class_name" not in data:
            data["class_name"] = data["class"]

        # 'class' anahtarını data'dan silelim ki dataclass hata vermesin
        if "class" in data:
            del data["class"]

        # Eksik ID varsa oluştur
        if "id" not in data:
            import uuid
            data["id"] = str(uuid.uuid4())

        # Gerekli anahtarları kontrol et
        required_keys = {"name", "class_name"}
        if not required_keys.issubset(data.keys()):
            # Hangi anahtar eksikse onu söyle (Debug için)
            missing = required_keys - data.keys()
            raise ValueError(f"Veri eksik: {missing}")

        # Alt nesneleri oluştur
        grades = [Grade(**g) for g in data.get("grades", [])]
        notes = [BehaviorNote(**n) for n in data.get("behavior_notes", [])]
        insights = [AIInsight(**i) for i in data.get("ai_insights", [])]

        # Sınıf yapısına uymayan gereksiz key'leri temizle
        valid_keys = {k for k in data if k in cls.__annotations__}
        filtered_data = {k: data[k] for k in valid_keys}

        # file_content yoksa boş string ata
        if "file_content" not in filtered_data:
            filtered_data["file_content"] = ""

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
                return f"Desteklenmeyen format: {file_type}"
            return text[:15000] + ("..." if len(text) > 15000 else "")
        except Exception as e:
            return f"Hata: {str(e)}"


class StudentManager:
    def __init__(self):
        # Klasör yoksa oluştur (Mutlaka çalışmalı)
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)
            print(f"📁 Veri klasörü oluşturuldu: {os.path.abspath(Config.DATA_DIR)}")

    def _get_path(self, student_id: str) -> str:
        return os.path.join(Config.DATA_DIR, f"{student_id}.json")

    def save_student(self, student: Student) -> None:
        student.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self._get_path(student.id), 'w', encoding='utf-8') as f:
                json.dump(student.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"✅ Kayıt başarılı: {student.name}")
        except Exception as e:
            print(f"❌ Kayıt hatası: {e}")

    def load_student(self, student_id: str) -> Optional[Student]:
        path = self._get_path(student_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Student.from_dict(data)
        except Exception as e:
            # HATA GİZLEME! Terminale hatayı bas ki neden yüklenmediğini görelim.
            print(f"⚠️ Dosya yüklenemedi ({student_id}): {e}")
            return None

    def get_all_students(self) -> List[Student]:
        students = []
        if not os.path.exists(Config.DATA_DIR):
            return []

        # Klasördeki tüm JSON'ları tara
        for filename in os.listdir(Config.DATA_DIR):
            if filename.endswith('.json'):
                student_id = filename.replace('.json', '')
                student = self.load_student(student_id)
                if student:
                    students.append(student)

        # İsme göre sırala
        students.sort(key=lambda x: x.name)
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
        # Prompt hazırlama mantığı
        summary = [f"Öğrenci: {student.name} ({student.class_name})", ""]
        # ... (Geri kalan prompt mantığı aynı) ...
        return "\n".join(summary)

    def generate_stream(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        full_prompt = f"{system_prompt}\n\nVERİLER:\n{prompt}"
        try:
            if self.provider == "Ollama":
                yield from self._stream_ollama(full_prompt)
            # ... Diğer sağlayıcılar ...
            else:
                yield f"Hata: Bilinmeyen sağlayıcı {self.provider}"
        except Exception as e:
            yield f"Hata: {str(e)}"

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
                    yield f"API Hatası: {response.status_code}"
        except Exception as e:
            yield f"Bağlantı Hatası: {str(e)}"

    # Diğer stream fonksiyonları (OpenAI vb.) aynı kalabilir...
    # (Önceki kodunuzdaki gibi)
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