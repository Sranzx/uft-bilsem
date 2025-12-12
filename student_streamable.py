# -*- coding: utf-8 -*-
import json
import os
import requests
import PyPDF2
from docx import Document
from datetime import datetime
from typing import List, Optional, Generator, Dict, Any
from dataclasses import dataclass, field, asdict

# Basit diff hesaplama için
from collections import defaultdict

# --- Kütüphane Yüklemeleri (opsiyonel) ---
openai = None
anthropic = None
genai = None

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
    CHANGELOG_FILE = "changelog.json"  # kayıtlı değişiklikler için merkezi dosya


@dataclass
class Grade:
    subject: str
    score: float
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


@dataclass
class BehaviorNote:
    note: str
    type: str = "genel"
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
        # Backwards compatibility / migration
        if "class" in data and "class_name" not in data:
            data["class_name"] = data["class"]

        if "id" not in data:
            import uuid
            data["id"] = str(uuid.uuid4())

        grades = []
        for g in data.get("grades", []):
            try:
                valid_g = {k: v for k, v in g.items() if k in Grade.__annotations__}
                grades.append(Grade(**valid_g))
            except:
                pass

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

        exclude_fields = {"grades", "behavior_notes", "ai_insights"}

        simple_data = {}
        for k, v in data.items():
            if k in cls.__annotations__ and k not in exclude_fields:
                simple_data[k] = v

        if "name" not in simple_data: simple_data["name"] = "İsimsiz Öğrenci"
        if "class_name" not in simple_data: simple_data["class_name"] = ""
        if "file_content" not in simple_data: simple_data["file_content"] = ""

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
                    text += (page.extract_text() or "") + "\n"
            elif file_type in ['docx', 'doc']:
                doc = Document(uploaded_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif file_type == 'txt':
                text = uploaded_file.getvalue().decode("utf-8")
            return text[:15000] + ("..." if len(text) > 15000 else "")
        except Exception as e:
            return f"Dosya hatası: {str(e)}"


class StudentManager:
    """
    Geliştirilmiş StudentManager:
    - Tekil öğrenci dosyaları (student_data/<id>.json)
    - Merkezî changelog: student_data/changelog.json
    - save_student: önce mevcut versiyon ile fark hesaplar, changelog'a yazar, sonra kaydeder.
    """

    def __init__(self):
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)
        self.changelog_path = os.path.join(Config.DATA_DIR, Config.CHANGELOG_FILE)
        # yükle changelog veya init et
        self._changelog = self._load_changelog()

    def _get_path(self, student_id: str) -> str:
        return os.path.join(Config.DATA_DIR, f"{student_id}.json")

    def _load_changelog(self) -> Dict[str, List[Dict[str, Any]]]:
        if not os.path.exists(self.changelog_path):
            return {}
        try:
            with open(self.changelog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_changelog(self) -> None:
        try:
            with open(self.changelog_path, 'w', encoding='utf-8') as f:
                json.dump(self._changelog, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _dict_for_diff(self, student: Student) -> Dict[str, Any]:
        """
        Student nesnesinin basit dict temsili.
        Sadece diff göstermek için gerekli alanlar alınır.
        """
        return {
            "id": student.id,
            "name": student.name,
            "class_name": student.class_name,
            "grades": [{ "subject": g.subject, "score": g.score, "date": g.date } for g in student.grades],
            "behavior_notes": [{ "note": b.note, "type": b.type, "date": b.date } for b in student.behavior_notes],
            "ai_insights_count": len(student.ai_insights),
            "file_content_snippet": (student.file_content or "")[:200]  # büyük içeriği gösterme
        }

    def _compute_diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Çok basit fark hesaplayıcı: alan bazında değişen değerleri döndürür.
        Notlar (grades) için subject'e göre karşılaştırma yapar.
        """
        diffs = []

        # Basit alanlar
        for key in ["name", "class_name", "file_content_snippet"]:
            old_v = old.get(key)
            new_v = new.get(key)
            if old_v != new_v:
                diffs.append({"field": key, "old": old_v, "new": new_v})

        # Grades - subject'e göre eşleştir
        old_grades = {g['subject']: g for g in old.get("grades", [])}
        new_grades = {g['subject']: g for g in new.get("grades", [])}

        # Ekleme / Güncelleme
        for subj, ng in new_grades.items():
            og = old_grades.get(subj)
            if not og:
                diffs.append({"field": "grades", "type": "added", "subject": subj, "new": ng})
            else:
                if og.get("score") != ng.get("score"):
                    diffs.append({"field": "grades", "type": "updated", "subject": subj, "old": og, "new": ng})

        # Silme
        for subj, og in old_grades.items():
            if subj not in new_grades:
                diffs.append({"field": "grades", "type": "removed", "subject": subj, "old": og})

        # Behavior notes - basit karşılaştırma (metin bazlı)
        old_beh = [b.get("note") for b in old.get("behavior_notes", [])]
        new_beh = [b.get("note") for b in new.get("behavior_notes", [])]
        # eklenenler
        for n in new_beh:
            if n not in old_beh:
                diffs.append({"field": "behavior_notes", "type": "added", "note": n})
        # silinenler
        for o in old_beh:
            if o not in new_beh:
                diffs.append({"field": "behavior_notes", "type": "removed", "note": o})

        # AI insights sayısı değiştiyse bilgi ekle
        if old.get("ai_insights_count") != new.get("ai_insights_count"):
            diffs.append({
                "field": "ai_insights_count",
                "old": old.get("ai_insights_count"),
                "new": new.get("ai_insights_count")
            })

        return diffs

    def save_student(self, student: Student) -> None:
        student.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = self._get_path(student.id)

        # Yüklü bir önceki versiyon var mı?
        prev_student = self.load_student(student.id)
        prev_snapshot = prev_student.to_dict() if prev_student else None

        # Diff hesapla
        prev_for_diff = self._dict_for_diff(prev_student) if prev_student else {}
        new_for_diff = self._dict_for_diff(student)
        diffs = self._compute_diff(prev_for_diff, new_for_diff)

        try:
            # Dosyaya yaz
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(student.to_dict(), f, ensure_ascii=False, indent=2)
            # Changelog'a ekle (sadece değişiklik varsa)
            if diffs:
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "student_id": student.id,
                    "diffs": diffs,
                    "prev_snapshot": prev_snapshot,
                    "new_snapshot": student.to_dict()
                }
                self._changelog.setdefault(student.id, []).append(entry)
                self._save_changelog()
        except Exception as e:
            print(f"Kayıt Hatası: {e}")

    def load_student(self, student_id: str) -> Optional[Student]:
        path = self._get_path(student_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Student.from_dict(data)
        except Exception as e:
            print(f"⚠️ Dosya Bozuk ({student_id}): {e}")
            return None

    def get_all_students(self) -> List[Student]:
        students = []
        if not os.path.exists(Config.DATA_DIR):
            return []

        for filename in os.listdir(Config.DATA_DIR):
            if filename.endswith('.json') and filename != Config.CHANGELOG_FILE:
                student_id = filename.replace('.json', '')
                try:
                    student = self.load_student(student_id)
                    if student:
                        students.append(student)
                except:
                    continue

        students.sort(key=lambda x: x.name)
        return students

    # Changelog API
    def get_changelog(self, student_id: str) -> List[Dict[str, Any]]:
        return self._changelog.get(student_id, [])

    def restore_from_changelog(self, student_id: str, entry_index: int) -> bool:
        """
        Seçili changelog entry'sindeki prev_snapshot ile geri yükleme yapar.
        entry_index: changelog listesinde hangi entry (0 en eski).
        """
        entries = self.get_changelog(student_id)
        if not entries or entry_index < 0 or entry_index >= len(entries):
            return False
        entry = entries[entry_index]
        prev = entry.get("prev_snapshot")
        if not prev:
            return False
        try:
            # Önce mevcut dosyayı yedek olarak changelog'a yeni bir entry ile sakla
            current = self.load_student(student_id)
            backup_entry = {
                "timestamp": datetime.now().isoformat(),
                "student_id": student_id,
                "diffs": [{"field": "restore", "description": f"Restore to entry {entry_index}"}],
                "prev_snapshot": current.to_dict() if current else None,
                "new_snapshot": prev
            }
            self._changelog.setdefault(student_id, []).append(backup_entry)
            self._save_changelog()

            # Restore et
            with open(self._get_path(student_id), 'w', encoding='utf-8') as f:
                json.dump(prev, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Geri yükleme hatası: {e}")
            return False


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
        # Basit fallback streaming (kullanıcı ortamına göre özelleştirilebilir)
        try:
            r = requests.post(f"{Config.OLLAMA_URL}/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": True
            }, timeout=Config.TIMEOUT, stream=True)
            # Basit stream okuma
            for chunk in r.iter_content(chunk_size=64):
                try:
                    text = chunk.decode('utf-8')
                    yield text
                except:
                    continue
        except Exception as e:
            yield f"Hata: {e}"