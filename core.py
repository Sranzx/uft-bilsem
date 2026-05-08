import os, json, uuid, csv
from datetime import datetime, date
from io import StringIO

DATA_DIR = "student_data"
os.makedirs(DATA_DIR, exist_ok=True)

SUBJECTS = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü"]
HW_STATUSES = {"pending": "📋 Bekliyor", "submitted": "📤 Teslim Edildi", "graded": "✅ Notlandı", "late": "⏰ Geç Teslim"}
PR_STATUSES = {"not_started": "⏳ Başlanmadı", "in_progress": "🔧 Devam Ediyor", "submitted": "📤 Teslim Edildi", "graded": "✅ Notlandı"}


def load_all():
    out = []
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith(".json") or f in ("changelog.json", "settings.json"):
            continue
        try:
            with open(os.path.join(DATA_DIR, f), encoding="utf-8") as fh:
                out.append(json.load(fh))
        except Exception:
            pass
    return sorted(out, key=lambda s: (s.get("class_name", ""), s.get("name", "")))


def load(sid):
    p = os.path.join(DATA_DIR, f"{sid}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def save(s):
    s["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(DATA_DIR, f"{s['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def new_student():
    s = {"id": str(uuid.uuid4()), "name": "", "class_name": "", "grades": [], "homeworks": [],
         "projects": [], "exams": [], "behavior": [], "observation": ""}
    save(s)
    return s


def delete_student(sid):
    p = os.path.join(DATA_DIR, f"{sid}.json")
    if os.path.exists(p):
        os.remove(p)


def hw_alerts(students):
    today = date.today()
    out = []
    for s in students:
        for h in (s.get("homeworks") or []):
            if h.get("status") in ("pending",) and h.get("due_date"):
                try:
                    due = date.fromisoformat(h["due_date"])
                    diff = (due - today).days
                    if diff <= 7:
                        out.append((diff, s, h))
                except Exception:
                    pass
    out.sort()
    return out


def export_csv(students):
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["Ad", "Sınıf", "Not Ort.", "Ödev", "Bekleyen", "Notlanan", "Proje", "Sınav"])
    for s in students:
        grades = s.get("grades", [])
        avg = sum(g["score"] for g in grades) / len(grades) if grades else 0
        hw = s.get("homeworks") or []
        pending = sum(1 for h in hw if h.get("status") == "pending")
        w.writerow([s.get("name", ""), s.get("class_name", ""), f"{avg:.1f}",
                    len(hw), pending, sum(1 for h in hw if h.get("status") == "graded"),
                    len(s.get("projects") or []), len(s.get("exams") or [])])
    return buf.getvalue()


def export_hw_csv(students):
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["Öğrenci", "Sınıf", "Ödev", "Ders", "Teslim", "Durum", "Not", "Gün Kaldı"])
    for s in students:
        for h in (s.get("homeworks") or []):
            days = ""
            if h.get("due_date"):
                try:
                    days = str((date.fromisoformat(h["due_date"]) - date.today()).days)
                except Exception:
                    pass
            pct = f"{h['grade']/h['max_grade']*100:.0f}%" if h.get("grade") else "-"
            w.writerow([s.get("name", ""), s.get("class_name", ""), h.get("title", ""),
                        h.get("subject", ""), h.get("due_date", ""), h.get("status", ""),
                        pct, days])
    return buf.getvalue()