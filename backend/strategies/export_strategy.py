import io
import os
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill
from interfaces.strategies import IExportStrategy
from models.domain import AttendanceRecord, Student


class ExcelExportStrategy(IExportStrategy):
    """ייצוא דוח נוכחות לקובץ Excel (XLSX) כולל תמונת הכיתה."""

    @property
    def media_type(self) -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @property
    def file_extension(self) -> str:
        return "xlsx"

    def export(self, students: list[Student], records: list[AttendanceRecord], session_id: str = None) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"

        # עיצוב כותרות
        headers = ["Student_Name", "Email", "Group", "Status", "Verification_Level", "Timestamp"]
        ws.append(headers)

        header_fill = PatternFill(start_color="0172AD", end_color="0172AD", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # הוספת נתונים
        records_by_student = {r.student_id: r for r in records}
        for st in students:
            rec = records_by_student.get(st.id)
            if rec:
                ws.append([st.name, st.email, st.group, rec.status, rec.verification_level, rec.created])
            else:
                ws.append([st.name, st.email, st.group, "ABSENT", "NONE", "-"])

        # התאמת רוחב עמודות
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 4

        # הוספת התמונה אם קיימת
        if session_id:
            img_path = f"/app/uploads/{session_id}.jpg"
            if os.path.exists(img_path):
                img = XLImage(img_path)
                # הקטנת התמונה כדי שתיכנס יפה לאקסל
                img.width = 600
                img.height = 400
                # הצבת התמונה מתחת לטבלה (2 שורות מתחת לסטודנט האחרון)
                ws.add_image(img, f"A{len(students) + 3}")

        # שמירה לזיכרון והחזרת הבייטים
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()