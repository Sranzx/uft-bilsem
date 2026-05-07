from typing import Optional
import PyPDF2
from docx import Document


class FileHandler:
    @staticmethod
    def extract_text(uploaded_file) -> str:
        text = ""
        try:
            ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ""

            if ext == 'pdf':
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            elif ext in ('docx', 'doc'):
                doc = Document(uploaded_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif ext == 'txt':
                text = uploaded_file.getvalue().decode("utf-8")
            else:
                return "Desteklenmeyen dosya formatı"

            return text[:15000]
        except Exception as e:
            return f"Dosya okunamadı: {str(e)}"

    @staticmethod
    def get_file_extension(filename: str) -> str:
        return filename.split('.')[-1].lower() if '.' in filename else ""
