import csv
import io
from interfaces.strategies import IExportStrategy
from models.domain import AttendanceRecord, Student


class CsvExportStrategy(IExportStrategy):
    """ייצוא דוח נוכחות לקובץ CSV עם קידוד UTF-8 BOM לתמיכה מלאה בעברית ב-Excel."""

    @property
    def media_type(self) -> str:
        return "text/csv"

    @property
    def file_extension(self) -> str:
        return "csv"

    def export(self, students: list[Student], records: list[AttendanceRecord]) -> str:
        records_by_student = {r.student_id: r for r in records}
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)
        writer.writerow(["Student_Name", "Email", "Group", "Status", "Verification_Level", "Timestamp"])

        for st in students:
            rec = records_by_student.get(st.id)
            if rec:
                writer.writerow([st.name, st.email, st.group, rec.status, rec.verification_level, rec.created])
            else:
                writer.writerow([st.name, st.email, st.group, "ABSENT", "NONE", "-"])

        return output.getvalue()