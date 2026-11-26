from abc import ABC, abstractmethod
from models.domain import AttendanceRecord, Student, SuspicionReport


class IHeadcountStrategy(ABC):
    """חוזה לאלגוריתם ספירת נוכחים מתמונת כיתה (Strategy Pattern)."""

    @abstractmethod
    def count_heads(self, image_bytes: bytes, mime_type: str) -> int:
        pass


class ISuspicionStrategy(ABC):
    """חוזה לאלגוריתם חישוב דרגת חשד להונאת נוכחות (Strategy Pattern)."""

    @abstractmethod
    def calculate(
        self,
        registered_count: int,
        ai_headcount: int,
        verified_active_count: int = 0,
    ) -> SuspicionReport:
        pass


class IExportStrategy(ABC):
    """חוזה לאלגוריתם ייצוא דוחות נוכחות (Strategy Pattern)."""

    @property
    @abstractmethod
    def media_type(self) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass

    @abstractmethod
    def export(self, students: list[Student], records: list[AttendanceRecord]) -> str:
        pass