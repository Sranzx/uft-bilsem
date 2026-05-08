import io
import csv
from datetime import datetime, timedelta
from typing import List, Optional
from core.models import Student, Homework, Project, Exam


class CSVExporter:
    @staticmethod
    def student_to_csv(student: Student) -> str:
        lines = []

        lines.append("=== ÖĞRENCİ BİLGİLERİ ===")
        lines.append(f"Ad Soyad,{student.name}")
        lines.append(f"Sınıf,{student.class_name}")
        lines.append(f"Kayıt Tarihi,{student.enrollment_date}")
        lines.append(f"Son Güncelleme,{student.last_updated}")
        lines.append("")

        lines.append("=== DERS NOTLARI ===")
        lines.append("Ders,Not,Tarih")
        for g in student.grades:
            lines.append(f"{g.subject},{g.score},{g.date}")
        lines.append("")

        lines.append("=== ÖDEVLER ===")
        lines.append("Başlık,Ders,Açıklama,Veriliş,Teslim,Durum,Not,Maks Not,Geri Bildirim")
        for h in student.homeworks:
            lines.append(f'"{h.title}","{h.subject}","{h.description[:100]}","{h.assigned_date}","{h.due_date}","{h.status}",{h.grade or ""},{h.max_grade},"{h.feedback[:100]}"')
        lines.append("")

        lines.append("=== PROJELER ===")
        lines.append("Başlık,Ders,Açıklama,Başlangıç,Teslim,Durum,Not,Maks Not,Geri Bildirim")
        for p in student.projects:
            lines.append(f'"{p.title}","{p.subject}","{p.description[:100]}","{p.start_date}","{p.due_date}","{p.status}",{p.grade or ""},{p.max_grade},"{p.feedback[:100]}"')
        lines.append("")

        lines.append("=== SINAVLAR ===")
        lines.append("Ad,Ders,Tür,Tarih,Not,Maks Not,Yüzde,Notlar")
        for e in student.exams:
            pct = (e.score / e.max_score * 100) if e.max_score else 0
            lines.append(f'"{e.title}","{e.subject}","{e.exam_type}","{e.date}",{e.score},{e.max_score},{pct:.1f}%,"{e.notes[:100]}"')
        lines.append("")

        lines.append("=== DAVRANIŞ NOTLARI ===")
        for b in student.behavior_notes:
            lines.append(f"- {b}")

        lines.append("")
        lines.append("=== GÖZLEM ===")
        lines.append(student.observation)

        return "\n".join(lines)

    @staticmethod
    def all_students_csv(students: List[Student]) -> str:
        lines = []
        lines.append("Ad,Sınıf,Ders Sayısı,Ortalama,Ödev Sayısı,Bekleyen Ödev,Notlanan Ödev,Proje,Sınav,Kayıt Tarihi")

        for s in students:
            avg = sum(g.score for g in s.grades) / len(s.grades) if s.grades else 0
            pending = sum(1 for h in s.homeworks if h.status in ("pending", "late"))
            graded = sum(1 for h in s.homeworks if h.status == "graded")
            lines.append(
                f'"{s.name}","{s.class_name}",{len(s.grades)},{avg:.1f},'
                f'{len(s.homeworks)},{pending},{graded},{len(s.projects)},{len(s.exams)},{s.enrollment_date}'
            )

        return "\n".join(lines)

    @staticmethod
    def homework_overview_csv(students: List[Student]) -> str:
        lines = []
        lines.append("Öğrenci,Sınıf,Ödev Başlık,Ders,Teslim Tarihi,Durum,Not,Maks Not,Gün Kaldı")

        for s in students:
            for h in s.homeworks:
                days_left = ""
                if h.due_date:
                    try:
                        due = datetime.strptime(h.due_date, "%Y-%m-%d")
                        diff = (due - datetime.now()).days
                        days_left = str(diff)
                    except Exception:
                        days_left = ""
                pct = ""
                if h.grade is not None:
                    pct = f"{(h.grade/h.max_grade*100):.0f}%" if h.max_grade else ""
                lines.append(
                    f'"{s.name}","{s.class_name}","{h.title}","{h.subject}","{h.due_date}",'
                    f'"{h.status}",{h.grade or ""},{h.max_grade},"{days_left}"'
                )

        return "\n".join(lines)


class PDFExporter:
    @staticmethod
    def student_to_pdf(student: Student) -> bytes:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib import colors
        except ImportError:
            return CSVExporter.student_to_csv(student).encode("utf-8")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=16, textColor=colors.HexColor('#4facfe'), spaceAfter=6)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#4facfe'), spaceBefore=12, spaceAfter=4)
        normal = styles['Normal']

        story.append(Paragraph(f"Öğrenci Raporu: {student.name}", title_style))
        story.append(Paragraph(f"Sınıf: {student.class_name} | Kayıt: {student.enrollment_date}", normal))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#4facfe')))
        story.append(Spacer(1, 0.3*cm))

        if student.grades:
            story.append(Paragraph("Ders Notları", h2_style))
            rows = [["Ders", "Not", "Tarih"]]
            for g in student.grades:
                rows.append([g.subject, f"{g.score:.0f}", g.date])
            t = Table(rows, colWidths=[7*cm, 3*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4facfe')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

        if student.homeworks:
            story.append(Paragraph("Ödevler", h2_style))
            rows = [["Başlık", "Ders", "Teslim", "Durum", "Not"]]
            for h in student.homeworks:
                rows.append([h.title[:30], h.subject, h.due_date or "-", h.status, f"{h.grade:.0f}" if h.grade is not None else "-"])
            t = Table(rows, colWidths=[5*cm, 3.5*cm, 3*cm, 3*cm, 2*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4facfe')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

        if student.exams:
            story.append(Paragraph("Sınavlar", h2_style))
            rows = [["Ad", "Ders", "Tür", "Tarih", "Not", "%"]]
            for e in student.exams:
                pct = (e.score / e.max_score * 100) if e.max_score else 0
                rows.append([e.title[:25], e.subject, e.exam_type, e.date, f"{e.score:.0f}/{e.max_score:.0f}", f"{pct:.0f}%"])
            t = Table(rows, colWidths=[5*cm, 3.5*cm, 2.5*cm, 3*cm, 3*cm, 2*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#51cf66')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (4, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(t)

        if student.observation:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph("Gözlem", h2_style))
            story.append(Paragraph(student.observation.replace('\n', '<br/>'), normal))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()


def get_homework_alerts(students: List[Student]):
    today = datetime.now().date()
    alerts = []

    for s in students:
        for hw in s.homeworks:
            if hw.status in ("pending", "submitted"):
                if not hw.due_date:
                    continue
                try:
                    due = datetime.strptime(hw.due_date, "%Y-%m-%d").date()
                    days_left = (due - today).days

                    if days_left < 0:
                        urgency = "OVERDUE"
                    elif days_left == 0:
                        urgency = "TODAY"
                    elif days_left <= 2:
                        urgency = "SOON"
                    elif days_left <= 5:
                        urgency = "UPCOMING"
                    else:
                        urgency = "OK"

                    if urgency in ("OVERDUE", "TODAY", "SOON"):
                        alerts.append({
                            "student": s,
                            "homework": hw,
                            "days_left": days_left,
                            "urgency": urgency
                        })
                except Exception:
                    continue

    alerts.sort(key=lambda a: (a["days_left"], a["student"].name))
    return alerts