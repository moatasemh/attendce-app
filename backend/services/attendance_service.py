import csv
import os
import random
from models.domain import ClassSession, Student, AttendanceRecord
from models.exceptions import (
    InvalidCredentialsError,
    ResourceNotFoundError,
    SessionClosedError,
)

LEVEL_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}


class AuditResult:
    """תוצאת בקרת הנוכחות: דוח כיתתי + רשימת דרגות חשד לכל סטודנט. נשאר תואם ל-facade (to_dict)."""

    def __init__(self, report, students: list[dict]):
        self.report = report
        self.students = students

    def to_dict(self) -> dict:
        data = self.report.to_dict()
        data["students"] = self.students
        return data


class AttendanceService:
    def __init__(self, repo, headcount_strategy, suspicion_strategy, export_strategy):
        self.repo = repo
        self.headcount_strategy = headcount_strategy
        self.suspicion_strategy = suspicion_strategy
        self.export_strategy = export_strategy

    def _parse_session(self, record: dict) -> ClassSession:
        """מחלץ רק את השדות המוכרים כדי למנוע קריסה מ-collectionId"""
        return ClassSession(
            id=record.get("id", ""),
            title=record.get("title", ""),
            class_code=record.get("class_code", ""),
            status=record.get("status", "OPEN"),
            ai_headcount=record.get("ai_headcount", 0),
            final_headcount=record.get("final_headcount", 0),
            created=record.get("created", "")
        )

    def _parse_attendance(self, record: dict) -> AttendanceRecord:
        """מחלץ רק את השדות המוכרים"""
        return AttendanceRecord(
            id=record.get("id", ""),
            session_id=record.get("session_id", ""),
            student_id=record.get("student_id", ""),
            student_name=record.get("student_name", ""),
            status=record.get("status", "PRESENT"),
            verification_level=record.get("verification_level", "REGISTERED"),
            created=record.get("created", "")
        )

    def import_students_from_csv(self, csv_path: str) -> dict:
        if not os.path.exists(csv_path):
            raise ResourceNotFoundError(
                f"קובץ הסטודנטים לא נמצא בנתיב: {csv_path}. אנא וודא שהוא נמצא בתיקיית demo_assets.")

        added = 0
        existing = self.repo.get_records("students")
        existing_emails = {r.get("email", "") for r in existing}

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                first_name = row.get("שם פרטי", "").strip()
                last_name = row.get("שם משפחה", "").strip()
                email = row.get("דוא\"ל", "").strip()
                group = row.get("קבוצות", "").strip()

                full_name = f"{first_name} {last_name}".strip()

                if not full_name or email in existing_emails:
                    continue

                data = {"name": full_name, "email": email, "group": group}
                self.repo.create_record("students", data)
                added += 1

        return {"added": added, "total": len(existing) + added}

    def list_students(self) -> list[Student]:
        records = self.repo.get_records("students")
        return [Student(
            id=r.get("id", ""),
            name=r.get("name", "Unknown"),
            pin="",
            email=r.get("email", ""),
            group=r.get("group", "")
        ) for r in records]

    def open_session(self, title: str) -> ClassSession:
        class_code = str(random.randint(10, 99))
        data = {
            "title": title,
            "class_code": class_code,
            "status": "OPEN",
            "ai_headcount": 0,
            "final_headcount": 0,
        }
        record = self.repo.create_record("sessions", data)
        return self._parse_session(record)

    def get_active_or_latest_session(self) -> ClassSession | None:
        records = self.repo.get_records("sessions")
        if not records:
            return None
        records.sort(key=lambda x: x.get("created", ""), reverse=True)
        return self._parse_session(records[0])

    def check_in_student(self, student_name: str, class_code: str):
        session = self.get_active_or_latest_session()
        if not session or session.status != "OPEN":
            raise SessionClosedError("רישום הנוכחות סגור כעת.")

        if str(session.class_code) != str(class_code):
            raise InvalidCredentialsError("הקוד הכיתתי שגוי.")

        students = self.list_students()
        student = next((s for s in students if s.name == student_name), None)
        if not student:
            raise ResourceNotFoundError(f"הסטודנט {student_name} לא נמצא ברשימה.")

        existing = self.repo.get_records("attendance", f'session_id="{session.id}" && student_id="{student.id}"')
        if existing:
            return "הנוכחות שלך כבר נרשמה בשיעור זה.", self._parse_attendance(existing[0])

        data = {
            "session_id": session.id,
            "student_id": student.id,
            "student_name": student.name,
            "status": "PRESENT",
            "verification_level": "REGISTERED",
        }
        created = self.repo.create_record("attendance", data)
        return "הנוכחות נרשמה בהצלחה!", self._parse_attendance(created)

    # ==========================================
    # בקרת נוכחות: ספירת ראשים מתמונה + דרגות חשד
    # ==========================================
    def _collect_activity(self, session_id: str) -> dict[str, dict]:
        """
        פעילות לכל סטודנט בשיעור: כמות סקרים שענה עליהם וכמות שאלות ששלח.
        נספרים כל הסקרים והשאלות של השיעור.
        """
        activity: dict[str, dict] = {}

        def bucket(student_id: str) -> dict:
            return activity.setdefault(student_id, {"polls": 0, "questions": 0})

        messages = self.repo.get_records("messages", f'session_id="{session_id}"')
        for m in messages:
            sid = m.get("student_id")
            if sid:
                bucket(sid)["questions"] += 1

        polls = self.repo.get_records("polls", f'session_id="{session_id}"')
        poll_ids = [p["id"] for p in polls if p.get("id")]
        if poll_ids:
            poll_filter = " || ".join(f'poll_id="{pid}"' for pid in poll_ids)
            votes = self.repo.get_records("poll_votes", poll_filter)
            for v in votes:
                sid = v.get("student_id")
                if sid:
                    bucket(sid)["polls"] += 1

        return activity

    def audit_headcount(self, session_id: str, image_bytes: bytes, mime_type: str) -> AuditResult:
        ai_count = self.headcount_strategy.count_heads(image_bytes, mime_type)

        attendance = self.repo.get_records("attendance", f'session_id="{session_id}"')
        activity = self._collect_activity(session_id)
        active_ids = set(activity.keys())

        registered_count = len(attendance)
        verified_count = sum(1 for r in attendance if r.get("student_id") in active_ids)

        report = self.suspicion_strategy.calculate(registered_count, ai_count, verified_count)
        self.repo.update_record("sessions", session_id, {"ai_headcount": ai_count})

        students: list[dict] = []
        for r in attendance:
            sid = r.get("student_id", "")
            act = activity.get(sid, {"polls": 0, "questions": 0})
            is_active = (act["polls"] + act["questions"]) > 0

            if r.get("verification_level") == "MANUAL_OVERRIDE":
                level, explanation = "NONE", "סומן ידנית על ידי המרצה."
            else:
                level_enum, explanation = self.suspicion_strategy.classify_student(
                    is_active, report.delta, ai_count
                )
                level = level_enum.value

            students.append({
                "student_id": sid,
                "student_name": r.get("student_name", ""),
                "polls_answered": act["polls"],
                "questions_sent": act["questions"],
                "is_active": is_active,
                "level": level,
                "explanation": explanation,
            })

        students.sort(key=lambda s: (LEVEL_ORDER.get(s["level"], 9), s["student_name"]))
        return AuditResult(report, students)

    def manual_override(self, session_id: str, student_id: str) -> AttendanceRecord:
        existing = self.repo.get_records("attendance", f'session_id="{session_id}" && student_id="{student_id}"')
        if existing:
            return self._parse_attendance(existing[0])

        students = self.list_students()
        student = next((s for s in students if s.id == student_id), None)

        data = {
            "session_id": session_id,
            "student_id": student_id,
            "student_name": student.name if student else "Unknown",
            "status": "PRESENT",
            "verification_level": "MANUAL_OVERRIDE",
        }
        created = self.repo.create_record("attendance", data)
        return self._parse_attendance(created)

    def close_session(self, session_id: str, final_headcount: int) -> ClassSession:
        updated = self.repo.update_record("sessions", session_id, {
            "status": "CLOSED",
            "final_headcount": final_headcount,
        })
        return self._parse_session(updated)

    def export_attendance(self, session_id: str) -> tuple[bytes, str, str]:
        students = self.list_students()
        records_raw = self.repo.get_records("attendance", f'session_id="{session_id}"')
        records = [self._parse_attendance(r) for r in records_raw]

        content = self.export_strategy.export(students, records, session_id=session_id)

        # שליפת שם השיעור
        session_record = self.repo.get_records("sessions", f'id="{session_id}"')
        title = session_record[0].get("title", "שיעור") if session_record else "שיעור"

        # ניקוי תווים לא חוקיים משם הקובץ
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()

        filename = f"נוכחות_{safe_title}.{self.export_strategy.file_extension}"
        return content, self.export_strategy.media_type, filename
    # ==========================================
    # פיצ'ר 2: הודעות ותגובות
    # ==========================================
    def send_message(self, session_id: str, student_id: str, student_name: str, text: str):
        msg_data = {
            "session_id": session_id,
            "student_id": student_id,
            "student_name": student_name,
            "text": text,
            "status": "pending"
        }
        self.repo.create_record("messages", msg_data)
        self._upgrade_verification(session_id, student_id)
        return {"status": "success", "message": "ההודעה נשלחה"}

    def _upgrade_verification(self, session_id: str, student_id: str):
        records = self.repo.get_records("attendance", f'session_id="{session_id}" && student_id="{student_id}"')
        if records:
            record = records[0]
            if record.get("verification_level") not in ("VERIFIED_ACTIVE", "MANUAL_OVERRIDE"):
                self.repo.update_record("attendance", record["id"], {"verification_level": "VERIFIED_ACTIVE"})

    # ==========================================
    # פיצ'ר 3: סקרים
    # ==========================================
    def create_poll(self, session_id: str, question: str, options: list[str]):
        active_polls = self.repo.get_records("polls", f'session_id="{session_id}" && status="active"')
        for p in active_polls:
            self.repo.update_record("polls", p["id"], {"status": "closed"})

        data = {
            "session_id": session_id,
            "question": question,
            "options": options,
            "status": "active"
        }
        return self.repo.create_record("polls", data)

    def get_active_poll(self, session_id: str):
        records = self.repo.get_records("polls", f'session_id="{session_id}" && status="active"')
        if not records:
            return None
        records.sort(key=lambda x: x.get("created", ""), reverse=True)
        return records[0]

    def submit_poll_vote(self, poll_id: str, student_id: str, session_id: str, answer: str, student_name: str):
        existing = self.repo.get_records("poll_votes", f'poll_id="{poll_id}" && student_id="{student_id}"')
        if existing:
            return {"status": "error", "message": "כבר הצבעת בסקר זה"}

        self.repo.create_record("poll_votes", {
            "poll_id": poll_id,
            "student_id": student_id,
            "student_name": student_name,
            "answer": answer
        })

        self._upgrade_verification(session_id, student_id)
        return {"status": "success", "message": "הצבעתך נקלטה"}

    def get_poll_results(self, poll_id: str) -> list[dict]:
        return self.repo.get_records("poll_votes", f'poll_id="{poll_id}"')