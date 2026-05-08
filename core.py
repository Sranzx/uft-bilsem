import os, json, uuid, csv, threading, time, hashlib
from datetime import datetime, date
from io import StringIO

DATA_DIR = "student_data"
os.makedirs(DATA_DIR, exist_ok=True)

def calculate_data_hash(data):
    """Calculate SHA256 hash of student data (excluding file_hash field)"""
    # Create a copy without hash for hash calculation
    data_for_hash = data.copy()
    if "file_hash" in data_for_hash:
        del data_for_hash["file_hash"]
    
    # Convert to JSON string with consistent ordering for hashing
    json_str = json.dumps(data_for_hash, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

def save_with_integrity(s):
    """Save student data with integrity hash"""
    s["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filepath = os.path.join(DATA_DIR, f"{s['id']}.json")
    
    # Calculate hash of data (without hash field)
    file_hash = calculate_data_hash(s)
    if file_hash:
        s["file_hash"] = file_hash
    
    # Write to temporary file first
    temp_file = filepath + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        
        # Write final file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        return True
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise e

def load_with_integrity(sid):
    """Load student data and verify integrity"""
    p = os.path.join(DATA_DIR, f"{sid}.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            
            # Verify integrity if hash exists
            if "file_hash" in data:
                stored_hash = data.pop("file_hash")  # Remove hash for calculation
                calculated_hash = calculate_data_hash(data)
                
                # Restore hash to data
                data["file_hash"] = stored_hash
                
                if calculated_hash != stored_hash:
                    # Hash mismatch - file may be corrupted
                    return None
            
            return data
        except Exception:
            return None
    return None

SUBJECTS = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü"]
HW_STATUSES = {"pending": "📋 Bekliyor", "submitted": "📤 Teslim Edildi", "graded": "✅ Notlandı", "late": "⏰ Geç Teslim"}
PR_STATUSES = {"not_started": "⏳ Başlanmadı", "in_progress": "🔧 Devam Ediyor", "submitted": "📤 Teslim Edildi", "graded": "✅ Notlandı"}


def load_all():
    out = []
    try:
        files = [f for f in os.listdir(DATA_DIR) 
                if f.endswith(".json") and f not in ("changelog.json", "settings.json")]
        for f in sorted(files):
            try:
                data = load_with_integrity(f[:-5])  # Remove .json extension
                if data is not None:
                    out.append(data)
            except Exception:
                pass
    except Exception:
        pass
    return sorted(out, key=lambda s: (s.get("class_name", ""), s.get("name", "")))


def load(sid):
    return load_with_integrity(sid)


def save(s):
    return save_with_integrity(s)


def validate_student_data(s):
    """Validate and clean student data"""
    # Ensure required fields exist with proper types
    if not isinstance(s.get("id"), str):
        s["id"] = str(uuid.uuid4())
    
    if not isinstance(s.get("name"), str):
        s["name"] = ""
        
    if not isinstance(s.get("class_name"), str):
        s["class_name"] = ""
        
    # Ensure lists are actually lists
    for field in ["grades", "homeworks", "projects", "exams", "behavior"]:
        if not isinstance(s.get(field), list):
            s[field] = []
    
    if not isinstance(s.get("observation"), str):
        s["observation"] = ""
        
    # Validate grades structure
    valid_grades = []
    for grade in s.get("grades", []):
        if isinstance(grade, dict) and "score" in grade and "subject" in grade:
            try:
                score = float(grade["score"])
                if 0 <= score <= 100:  # Assuming scores are 0-100
                    valid_grades.append({
                        "score": score,
                        "subject": str(grade["subject"]) if grade["subject"] else ""
                    })
            except (ValueError, TypeError):
                pass  # Skip invalid grade
    s["grades"] = valid_grades
    
    # Validate homeworks structure
    valid_homeworks = []
    for hw in s.get("homeworks", []):
        if isinstance(hw, dict) and "title" in hw:
            valid_homeworks.append({
                "title": str(hw.get("title", "")),
                "subject": str(hw.get("subject", "")),
                "due_date": str(hw.get("due_date", "")) if hw.get("due_date") else None,
                "status": str(hw.get("status", "pending")) if hw.get("status") in HW_STATUSES else "pending",
                "grade": float(hw["grade"]) if hw.get("grade") is not None else None,
                "max_grade": float(hw["max_grade"]) if hw.get("max_grade") is not None else 100.0
            })
    s["homeworks"] = valid_homeworks
    
    # Validate projects structure
    valid_projects = []
    for proj in s.get("projects", []):
        if isinstance(proj, dict) and "title" in proj:
            valid_projects.append({
                "title": str(proj.get("title", "")),
                "subject": str(proj.get("subject", "")),
                "due_date": str(proj.get("due_date", "")) if proj.get("due_date") else None,
                "status": str(proj.get("status", "not_started")) if proj.get("status") in PR_STATUSES else "not_started",
                "grade": float(proj["grade"]) if proj.get("grade") is not None else None,
                "max_grade": float(proj["max_grade"]) if proj.get("max_grade") is not None else 100.0
            })
    s["projects"] = valid_projects
    
    # Validate exams structure
    valid_exams = []
    for exam in s.get("exams", []):
        if isinstance(exam, dict) and "title" in exam:
            valid_exams.append({
                "title": str(exam.get("title", "")),
                "subject": str(exam.get("subject", "")),
                "date": str(exam.get("date", "")) if exam.get("date") else None,
                "score": float(exam["score"]) if exam.get("score") is not None else None,
                "max_score": float(exam["max_score"]) if exam.get("max_score") is not None else 100.0
            })
    s["exams"] = valid_exams
    
    # Validate behavior structure
    valid_behavior = []
    for behavior in s.get("behavior", []):
        if isinstance(behavior, dict) and "date" in behavior and "description" in behavior:
            valid_behavior.append({
                "date": str(behavior.get("date", "")) if behavior.get("date") else None,
                "description": str(behavior.get("description", "")),
                "type": str(behavior.get("type", "observation")) if behavior.get("type") in ["observation", "reward", "warning"] else "observation",
                "points": int(behavior["points"]) if behavior.get("points") is not None else 0
            })
    s["behavior"] = valid_behavior
    
    return s

def new_student():
    s = {"id": str(uuid.uuid4()), "name": "", "class_name": "", "grades": [],
         "homeworks": [], "projects": [], "exams": [], "behavior": [], "observation": ""}
    s = validate_student_data(s)
    save(s)
    return s


def delete_student(sid):
    """Delete a student file with error handling"""
    try:
        p = os.path.join(DATA_DIR, f"{sid}.json")
        if os.path.exists(p):
            os.remove(p)
            return True
        return False  # File didn't exist
    except Exception:
        return False  # Error occurred


def hw_alerts(students):
    """Get homework alerts with error handling"""
    try:
        today = date.today()
        out = []
        for s in students:
            # Validate student data
            if not isinstance(s, dict):
                continue
            homeworks = s.get("homeworks") or []
            if not isinstance(homeworks, list):
                continue
            for h in homeworks:
                # Validate homework data
                if not isinstance(h, dict):
                    continue
                if h.get("status") in ("pending",) and h.get("due_date"):
                    try:
                        due = date.fromisoformat(str(h["due_date"]))
                        diff = (due - today).days
                        if diff <= 7:
                            out.append((diff, s, h))
                    except Exception:
                        # Skip invalid date formats
                        pass
        out.sort()
        return out
    except Exception:
        # Return empty list on any error
        return []


def export_csv(students):
    """Export student data to CSV with error handling"""
    try:
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Ad", "Sınıf", "Not Ort.", "Ödev", "Bekleyen", "Notlanan", "Proje", "Sınav"])
        for s in students:
            # Validate student data
            if not isinstance(s, dict):
                continue
            grades = s.get("grades", [])
            if not isinstance(grades, list):
                grades = []
            # Calculate average grade
            avg = 0
            valid_grades = []
            for g in grades:
                if isinstance(g, dict) and "score" in g:
                    try:
                        valid_grades.append(float(g["score"]))
                    except (ValueError, TypeError):
                        pass
            if valid_grades:
                avg = sum(valid_grades) / len(valid_grades)
            hw = s.get("homeworks") or []
            if not isinstance(hw, list):
                hw = []
            pending = 0
            graded = 0
            for h in hw:
                if isinstance(h, dict) and h.get("status") == "pending":
                    pending += 1
                elif isinstance(h, dict) and h.get("status") == "graded":
                    graded += 1
            projects = s.get("projects") or []
            exams = s.get("exams") or []
            if not isinstance(projects, list):
                projects = []
            if not isinstance(exams, list):
                exams = []
            w.writerow([str(s.get("name", "")), str(s.get("class_name", "")), f"{avg:.1f}",
                        len(hw), pending, graded,
                        len(projects), len(exams)])
        return buf.getvalue()
    except Exception:
        # Return empty CSV with just headers on error
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Ad", "Sınıf", "Not Ort.", "Ödev", "Bekleyen", "Notlanan", "Proje", "Sınav"])
        return buf.getvalue()


def export_hw_csv(students):
    """Export homework data to CSV with error handling"""
    try:
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Öğrenci", "Sınıf", "Ödev", "Ders", "Teslim", "Durum", "Not", "Gün Kaldı"])
        for s in students:
            # Validate student data
            if not isinstance(s, dict):
                continue
            homeworks = s.get("homeworks") or []
            if not isinstance(homeworks, list):
                continue
            for h in homeworks:
                # Validate homework data
                if not isinstance(h, dict):
                    continue
                days = ""
                if h.get("due_date"):
                    try:
                        days = str((date.fromisoformat(str(h["due_date"])) - date.today()).days)
                    except Exception:
                        pass
                pct = "-"
                if h.get("grade") is not None and h.get("max_grade") is not None:
                    try:
                        grade_val = float(h["grade"])
                        max_grade_val = float(h["max_grade"])
                        if max_grade_val > 0:
                            pct = f"{grade_val/max_grade_val*100:.0f}%"
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass
                w.writerow([str(s.get("name", "")), str(s.get("class_name", "")), 
                           str(h.get("title", "")), str(h.get("subject", "")),
                           str(h.get("due_date", "")), str(h.get("status", "")),
                           pct, days])
        return buf.getvalue()
    except Exception:
        # Return empty CSV with just headers on error
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Öğrenci", "Sınıf", "Ödev", "Ders", "Teslim", "Durum", "Not", "Gün Kaldı"])
        return buf.getvalue()


