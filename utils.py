from fpdf import FPDF


class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'OGRENCI GELISIM VE ANALIZ RAPORU', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')


def clean_text(text):
    """
    Türkçe karakterleri PDF uyumlu Latin-1 formatına çevirir.
    FPDF'in standart fontları Türkçe karakter desteklemediği için bu işlem gereklidir.
    """
    tr_map = {
        'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I',
        'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    # Eğer text None ise boş string yap
    if text is None:
        text = ""

    # Karakter değişimi
    for tr, en in tr_map.items():
        text = text.replace(tr, en)

    # Latin-1 encode işlemi (Hataları yoksaymak yerine 'replace' ile ? koyar)
    return text.encode('latin-1', 'replace').decode('latin-1')


def create_pdf_report(student, ai_analysis):
    pdf = PDFReport()
    pdf.add_page()
    # Otomatik sayfa sonu ayarı
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- BAŞLIK BİLGİLERİ ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, clean_text("Ogrenci Bilgileri"), 0, 1)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, clean_text(f"Ad Soyad: {student.name}"), 0, 1)
    pdf.cell(0, 7, clean_text(f"Numara (ID): {student.id}"), 0, 1)
    pdf.cell(0, 7, clean_text(f"Sinif: {student.class_name}"), 0, 1)
    pdf.cell(0, 7, clean_text(f"Rapor Tarihi: {student.last_updated}"), 0, 1)

    pdf.ln(5)

    # --- AKADEMİK DURUM ---
    if student.grades:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean_text("Akademik Ozet"), 0, 1)
        pdf.set_font("Arial", "", 11)

        subjects = {}
        for g in student.grades:
            subjects.setdefault(g.subject, []).append(g.score)

        for subj, scores in subjects.items():
            avg = sum(scores) / len(scores)
            pdf.cell(0, 7, clean_text(f"- {subj}: Ortalama {avg:.1f}"), 0, 1)

    pdf.ln(5)

    # --- YAPAY ZEKA ANALİZİ ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, clean_text("Yapay Zeka Degerlendirmesi"), 0, 1)

    pdf.set_font("Arial", "", 10)
    # Multi_cell uzun metinleri alt satıra kaydırır
    pdf.multi_cell(0, 6, clean_text(ai_analysis))

    # Streamlit için byte çıktısı döndür
    return pdf.output(dest='S').encode('latin-1')