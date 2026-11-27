import sys
import os

# הוספת תיקיית האב לנתיב החיפוש של פייתון
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock
from models.domain import Student, ClassSession
from services.attendance_service import AttendanceService
from strategies.suspicion_strategy import SmartRatioSuspicionStrategy
from strategies.export_strategy import ExcelExportStrategy
from strategies.vision_strategy import MockHeadcountStrategy

@pytest.fixture
def mock_repo():
    return MagicMock()

@pytest.fixture
def attendance_service(mock_repo):
    return AttendanceService(
        repo=mock_repo,
        headcount_strategy=MockHeadcountStrategy(fixed_count=20),
        suspicion_strategy=SmartRatioSuspicionStrategy(),
        export_strategy=ExcelExportStrategy()
    )

@pytest.fixture
def sample_student():
    # תוקן: הוספת pin ו-email כדי להתאים ל-SRS
    return Student(id="123", name="גיא אביב", pin="", email="guy@gmail.com", group="3")

@pytest.fixture
def sample_session():
    return ClassSession(id="sess1", title="הרצאה 1", class_code="99", status="OPEN")