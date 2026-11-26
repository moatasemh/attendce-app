import threading
from services.attendance_service import AttendanceService
import os
import re


class SmartClassFacade:
    _instance: "SmartClassFacade | None" = None
    _lock = threading.Lock()

    def __init__(self, attendance_service: AttendanceService, comparison_service=None):
        self._attendance = attendance_service
        self._comparison = comparison_service

    def get_public_tunnel_url(self) -> str | None:
        log_path = "/shared/tunnel.log"
        if not os.path.exists(log_path): return None
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
        return matches[-1] if matches else None

    @classmethod
    def configure(cls, attendance_service: AttendanceService, comparison_service=None) -> "SmartClassFacade":
        with cls._lock:
            cls._instance = cls(attendance_service=attendance_service, comparison_service=comparison_service)
            return cls._instance

    def import_course_students(self, csv_path: str = "/app/demo_assets/students.csv") -> dict:
        return self._attendance.import_students_from_csv(csv_path)

    def get_student_directory(self) -> list[dict]:
        return [{"id": s.id, "name": s.name, "group": s.group} for s in self._attendance.list_students()]

    def start_attendance_session(self, title: str) -> dict:
        return self._attendance.open_session(title).to_dict()

    def get_current_session(self) -> dict | None:
        session = self._attendance.get_active_or_latest_session()
        return session.to_dict() if session else None

    def register_student_attendance(self, student_name: str, class_code: str) -> dict:
        msg, record = self._attendance.check_in_student(student_name, class_code)
        return {"message": msg, "record": record.to_dict()}

    def run_attendance_audit(self, session_id: str, image_bytes: bytes, mime_type: str) -> dict:
        report = self._attendance.audit_headcount(session_id, image_bytes, mime_type)
        return report.to_dict()

    def override_student_attendance(self, session_id: str, student_id: str) -> dict:
        return self._attendance.manual_override(session_id, student_id).to_dict()

    def finalize_attendance_session(self, session_id: str, final_headcount: int) -> dict:
        return self._attendance.close_session(session_id, final_headcount).to_dict()

    def generate_attendance_report(self, session_id: str) -> tuple[str, str, str]:
        return self._attendance.export_attendance(session_id)

    def send_student_message(self, session_id: str, student_id: str, student_name: str, text: str) -> dict:
        return self._attendance.send_message(session_id, student_id, student_name, text)

    def create_poll(self, session_id: str, question: str, options: list[str]) -> dict:
        return self._attendance.create_poll(session_id, question, options)

    def get_active_poll(self, session_id: str) -> dict | None:
        return self._attendance.get_active_poll(session_id)

    def vote_in_poll(self, poll_id: str, student_id: str, session_id: str, answer: str, student_name: str) -> dict:
        return self._attendance.submit_poll_vote(poll_id, student_id, session_id, answer, student_name)

    def get_poll_results(self, poll_id: str) -> list:
        return self._attendance.get_poll_results(poll_id)

    def import_repos_csv(self, csv_text: str) -> dict:
        return self._comparison.import_repos_csv(csv_text)

    def compare_my_repo(self, my_repo_url: str) -> dict:
        return self._comparison.compare(my_repo_url)

    def repos_status(self) -> dict:
        return {"count": self._comparison.count()}

    def compare_for_student(self, my_repo_url: str) -> dict:
        return self._comparison.compare_for_student(my_repo_url)