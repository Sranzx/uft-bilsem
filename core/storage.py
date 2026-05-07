import os
import json
from datetime import datetime
from typing import List, Optional, Set

from core.models import Student


class StudentRepository:
    IGNORED_FILES: Set[str] = {"changelog.json", "settings.json", "config.json", ".ds_store"}

    def __init__(self, data_dir: str = "student_data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _path(self, student_id: str) -> str:
        return os.path.join(self.data_dir, f"{student_id}.json")

    def save(self, student: Student) -> None:
        student.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = self._path(student.id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(student.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, student_id: str) -> Optional[Student]:
        path = self._path(student_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Student.from_dict(data)
        except Exception:
            return None

    def delete(self, student_id: str) -> bool:
        path = self._path(student_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_all(self) -> List[Student]:
        students = []
        if not os.path.exists(self.data_dir):
            return students

        for filename in os.listdir(self.data_dir):
            name_lower = filename.lower()
            if name_lower in self.IGNORED_FILES:
                continue
            if not filename.endswith('.json'):
                continue

            student_id = filename[:-5]
            try:
                student = self.load(student_id)
                if student:
                    students.append(student)
            except Exception:
                continue

        students.sort(key=lambda s: (s.class_name, s.name))
        return students

    def search(self, query: str) -> List[Student]:
        query = query.lower()
        return [s for s in self.get_all() if query in s.name.lower() or query in s.class_name.lower()]
