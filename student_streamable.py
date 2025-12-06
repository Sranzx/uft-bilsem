import json
import os
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

# --- GÖRSELLEŞTİRME VE UI (Rich Kütüphanesi) ---
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich.prompt import Prompt, FloatPrompt, IntPrompt
    from rich.layout import Layout
    from rich.live import Live

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Daha iyi bir deneyim için 'pip install rich' komutunu çalıştırın.")


# --- KONFIGÜRASYON ---
class Config:
    DATA_DIR = "student_data"
    OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    TIMEOUT = 60
    DEBUG = False


# --- VERİ MODELLERİ (Dataclasses) ---
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
        # Nested objeleri düzgün geri yüklemek için
        grades = [Grade(**g) for g in data.get("grades", [])]
        notes = [BehaviorNote(**n) for n in data.get("behavior_notes", [])]
        insights = [AIInsight(**i) for i in data.get("ai_insights", [])]

        # Gereksiz alanları temizle
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
        self.console = Console() if RICH_AVAILABLE else None
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
            if self.console: self.console.print(f"[red]❌ Dosya okuma hatası: {e}[/red]")
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


# --- AI SERVİSİ (Ollama) ---
class AIService:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.model = Config.DEFAULT_MODEL
        self.is_connected = self.check_connection()

    def check_connection(self) -> bool:
        try:
            response = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=3)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                # Model var mı kontrol et, yoksa ilkini seç
                if not any(self.model in m for m in models) and models:
                    self.model = models[0]
                return True
        except:
            return False
        return False

    def generate_streaming_response(self, prompt: str, system_prompt: str) -> str:
        """Kelimeleri canlı olarak (streaming) getirir"""
        full_response = ""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,  # Streaming aktif
            "options": {"temperature": 0.3, "num_ctx": 2048}
        }

        try:
            with requests.post(f"{Config.OLLAMA_URL}/api/generate", json=payload, stream=True,
                               timeout=Config.TIMEOUT) as r:
                if r.status_code != 200:
                    return f"❌ Hata: {r.status_code}"

                # Rich Live Display kullanarak akıcı yazı efekti
                if RICH_AVAILABLE:
                    with Live(Panel("", title="🤖 AI Düşünüyor...", border_style="blue"), refresh_per_second=10) as live:
                        for line in r.iter_lines():
                            if line:
                                body = json.loads(line)
                                token = body.get('response', '')
                                full_response += token
                                if body.get('done'):
                                    break
                                live.update(Panel(Markdown(full_response), title=f"🤖 {self.model} Analizi",
                                                  border_style="green"))
                else:
                    # Rich yoksa basit streaming
                    print("🤖 AI Analiz Yapıyor: ", end="", flush=True)
                    for line in r.iter_lines():
                        if line:
                            body = json.loads(line)
                            token = body.get('response', '')
                            full_response += token
                            print(token, end="", flush=True)
                    print()

            return full_response
        except Exception as e:
            return f"❌ Bağlantı hatası: {str(e)}"

    def prepare_student_prompt(self, student: Student) -> str:
        summary = f"Öğrenci: {student.name} ({student.class_name})\n\nAKADEMİK:\n"
        if not student.grades:
            summary += "Henüz not girişi yok.\n"

        # Notları ders bazında grupla
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


# --- KULLANICI ARAYÜZÜ (CLI) ---
class AppInterface:
    def __init__(self):
        self.manager = StudentManager()
        self.ai = AIService()
        self.console = Console() if RICH_AVAILABLE else None

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        if RICH_AVAILABLE:
            self.clear()
            title = "[bold cyan]🎓 OLLAMA AI STUDENT ANALYTICS v2.0[/bold cyan]"
            status = "[green]● ÇEVRİMİÇİ[/green]" if self.ai.is_connected else "[red]● ÇEVRİMDIŞI[/red]"
            model = f"[yellow]{self.ai.model}[/yellow]"

            grid = Table.grid(expand=True)
            grid.add_column(justify="left")
            grid.add_column(justify="right")
            grid.add_row(title, f"{status} | Model: {model}")
            self.console.print(Panel(grid, style="blue"))
        else:
            print("--- AI ÖĞRENCİ SİSTEMİ v2.0 ---")

    def menu(self):
        while True:
            self.print_header()

            if RICH_AVAILABLE:
                table = Table(show_header=False, box=None)
                table.add_row("[bold magenta]1.[/] ➕ Yeni Öğrenci Ekle")
                table.add_row("[bold magenta]2.[/] 📚 Not Gir")
                table.add_row("[bold magenta]3.[/] 🧠 Davranış Notu Ekle")
                table.add_row("[bold magenta]4.[/] 🤖 AI Analiz & Rapor")
                table.add_row("[bold magenta]5.[/] 📋 Öğrenci Listesi")
                table.add_row("[bold magenta]6.[/] ⚙️  Ayarlar / Model")
                table.add_row("[bold magenta]0.[/] 🚪 Çıkış")
                self.console.print(table)
                choice = Prompt.ask("\n[bold yellow]Seçiminiz[/]", choices=["0", "1", "2", "3", "4", "5", "6"],
                                    default="0")
            else:
                print("1. Yeni Öğrenci\n2. Not Gir\n3. Davranış Ekle\n4. AI Analiz\n5. Liste\n0. Çıkış")
                choice = input("Seçim: ")

            if choice == "1":
                self.add_student()
            elif choice == "2":
                self.add_grade()
            elif choice == "3":
                self.add_behavior()
            elif choice == "4":
                self.analyze_student()
            elif choice == "5":
                self.list_students()
            elif choice == "6":
                self.settings()
            elif choice == "0":
                break

    def select_student(self) -> Optional[Student]:
        students = self.manager.get_all_students()
        if not students:
            self.console.print("[red]❌ Kayıtlı öğrenci yok![/red]")
            time.sleep(1.5)
            return None

        if RICH_AVAILABLE:
            table = Table(title="Öğrenci Seçimi")
            table.add_column("ID", style="cyan")
            table.add_column("Ad", style="green")
            table.add_column("Sınıf")
            for s in students:
                table.add_row(s.id, s.name, s.class_name)
            self.console.print(table)

            sid = Prompt.ask("Öğrenci ID")
        else:
            sid = input("Öğrenci ID: ")

        return self.manager.load_student(sid)

    def add_student(self):
        self.console.print("\n[bold]🆕 YENİ ÖĞRENCİ[/bold]")
        sid = Prompt.ask("ID")
        if self.manager.load_student(sid):
            self.console.print("[red]❌ Bu ID zaten kullanımda![/red]")
            time.sleep(2)
            return

        name = Prompt.ask("Ad Soyad")
        cls_name = Prompt.ask("Sınıf")

        student = Student(id=sid, name=name, class_name=cls_name)
        self.manager.save_student(student)
        self.console.print(f"[green]✅ {name} kaydedildi![/green]")
        time.sleep(1)

    def add_grade(self):
        student = self.select_student()
        if not student: return

        subject = Prompt.ask("Ders Adı")
        score = FloatPrompt.ask("Not (0-100)")

        student.grades.append(Grade(subject=subject, score=score))
        self.manager.save_student(student)
        self.console.print("[green]✅ Not kaydedildi![/green]")
        time.sleep(1)

    def add_behavior(self):
        student = self.select_student()
        if not student: return

        note = Prompt.ask("Gözlem Notu")
        b_type = Prompt.ask("Tür", choices=["positive", "negative", "neutral"], default="neutral")

        student.behavior_notes.append(BehaviorNote(note=note, type=b_type))
        self.manager.save_student(student)
        self.console.print("[green]✅ Gözlem kaydedildi![/green]")
        time.sleep(1)

    def analyze_student(self):
        if not self.ai.is_connected:
            self.console.print("[red]❌ Ollama bağlantısı yok! Önce 'ollama serve' çalıştırın.[/red]")
            Prompt.ask("Devam etmek için Enter...")
            return

        student = self.select_student()
        if not student: return

        student_data = self.ai.prepare_student_prompt(student)

        system_prompt = """Sen uzman bir pedagog ve eğitim danışmanısın.
        Verilen öğrenci verilerini analiz et. Çıktıyı Markdown formatında ver.
        Şunları içer: 
        1. **Genel Durum**: Kısa özet.
        2. **Akademik Analiz**: Güçlü/Zayıf yönler.
        3. **Davranışsal Analiz**: Varsa notlara dayalı yorum.
        4. **Öneriler**: Somut adımlar.
        Dil: Türkçe. Ton: Yapıcı ve profesyonel."""

        full_prompt = f"Lütfen şu öğrenciyi analiz et:\n{student_data}"

        # Streaming Analiz
        response = self.ai.generate_streaming_response(full_prompt, system_prompt)

        # Sonucu kaydet
        student.ai_insights.append(AIInsight(analysis=response, model=self.ai.model))
        self.manager.save_student(student)

        if RICH_AVAILABLE:
            self.console.print("\n[green]✅ Analiz tamamlandı ve profile kaydedildi.[/green]")
        Prompt.ask("Menüye dönmek için Enter...")

    def list_students(self):
        students = self.manager.get_all_students()
        if RICH_AVAILABLE:
            table = Table(title="Kayıtlı Öğrenciler")
            table.add_column("ID", justify="right", style="cyan", no_wrap=True)
            table.add_column("Ad Soyad", style="magenta")
            table.add_column("Sınıf", style="green")
            table.add_column("Ort.", justify="right")
            table.add_column("Son AI Analizi")

            for s in students:
                avg = 0
                if s.grades:
                    avg = sum(g.score for g in s.grades) / len(s.grades)

                last_ai = s.ai_insights[-1].date if s.ai_insights else "-"
                table.add_row(s.id, s.name, s.class_name, f"{avg:.1f}", last_ai)

            self.console.print(table)
        else:
            for s in students:
                print(f"{s.id} - {s.name}")

        Prompt.ask("\nDevam etmek için Enter...")

    def settings(self):
        self.console.print(Panel(f"Mevcut Model: [bold green]{self.ai.model}[/bold green]"))
        self.console.print("Modeller Ollama üzerinden çekilir.")

        if Confirm.ask("Bağlantıyı tekrar kontrol edeyim mi?"):
            status = self.ai.check_connection()
            if status:
                self.console.print("[green]✅ Bağlantı başarılı![/green]")
            else:
                self.console.print("[red]❌ Bağlantı başarısız![/red]")

        time.sleep(1)


# --- BAŞLATICI ---
if __name__ == "__main__":
    if RICH_AVAILABLE:
        from rich.prompt import Confirm
    app = AppInterface()
    try:
        app.menu()
    except KeyboardInterrupt:
        print("\n👋 Güle güle!")