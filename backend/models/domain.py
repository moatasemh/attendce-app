from dataclasses import asdict, dataclass
from enum import Enum


class SuspicionLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class Student:
    id: str
    name: str
    pin: str
    email: str = ""
    group: str = ""


@dataclass
class ClassSession:
    id: str
    title: str
    class_code: str
    status: str
    ai_headcount: int = 0
    final_headcount: int = 0
    created: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AttendanceRecord:
    id: str
    session_id: str
    student_id: str
    student_name: str
    status: str
    verification_level: str
    created: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SuspicionReport:
    ai_headcount: int
    registered_count: int
    verified_active_count: int
    delta: int
    excess_ratio: float
    level: SuspicionLevel
    explanation: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["level"] = self.level.value
        return data