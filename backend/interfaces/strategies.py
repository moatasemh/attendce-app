from abc import ABC, abstractmethod
from models.domain import AttendanceRecord, Student, SuspicionReport

class IHeadcountStrategy(ABC):
    @abstractmethod
    def count_heads(self, image_bytes: bytes, mime_type: str) -> int:
        pass

class ISuspicionStrategy(ABC):
    @abstractmethod
    def calculate(self, registered_count: int, ai_headcount: int, verified_active_count: int = 0) -> SuspicionReport:
        pass
    @abstractmethod
    def classify_student(self, is_active: bool, delta: int, ai_headcount: int):
        pass

class IExportStrategy(ABC):
    @property
    @abstractmethod
    def media_type(self) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass

    @abstractmethod
    def export(self, students: list[Student], records: list[AttendanceRecord], session_id: str = None) -> bytes:
        pass