import os, json, uuid
from datetime import datetime

DATA_DIR = "student_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

SUBJECTS = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü"]

HW_STATUSES = {"pending": "📋 Bekliyor", "submitted": "📤 Teslim Edildi", "graded": "✅ Notlandı", "late": "⏰ Geç Teslim"}
PR_STATUSES = {"not_started": "⏳ Başlanmadı", "in_progress": "🔧 Devam Ediyor", "submitted": "📤 Teslim Edildi", "graded": "✅ Notlandı"}


def path(sid):
    return os.path.join(DATA_DIR, f"{sid}.json")


def load_all():
    students = []
    for f in os.listdir(DATA_DIR):
        if not f.endswith(".json") or f == "changelog.json":
            continue
        try:
            with open(os.path.join(DATA_DIR, f), encoding="utf-8") as fh:
                students.append(json.load(fh))
        except Exception:
            pass
    students.sort(key=lambda s: (s.get("class_name", ""), s.get("name", "")))
    return students


def load(sid):
    p = path(sid)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save(student):
    with open(path(student["id"]), "w", encoding="utf-8") as f:
        json.dump(student, f, ensure_ascii=False, indent=2)


def new_student():
    s = {
        "id": str(uuid.uuid4()),
        "name": "",
        "class_name": "",
        "grades": [],
        "homeworks": [],
        "projects": [],
        "exams": [],
        "behavior": [],
        "observation": "",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save(s)
    return s


def delete_student(sid):
    p = path(sid)
    if os.path.exists(p):
        os.remove(p)


def to_student(data):
    s = dict(data)
    s.setdefault("homeworks", [])
    s.setdefault("projects", [])
    s.setdefault("exams", [])
    s.setdefault("grades", [])
    s.setdefault("behavior", [])
    s.setdefault("observation", "")
    return s