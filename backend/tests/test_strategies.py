from strategies.suspicion_strategy import SmartRatioSuspicionStrategy
from strategies.similarity_strategy import TokenShingleSimilarity
from models.domain import SuspicionLevel


def test_suspicion_none_when_no_delta():
    strategy = SmartRatioSuspicionStrategy()
    report = strategy.calculate(registered_count=20, ai_headcount=20)
    assert report.level == SuspicionLevel.NONE
    assert report.delta == 0


def test_suspicion_high_on_large_delta():
    strategy = SmartRatioSuspicionStrategy()
    # נרשמו 40, אבל יש רק 20 ראשים בתמונה -> חשד גבוה
    report = strategy.calculate(registered_count=40, ai_headcount=20)
    assert report.level == SuspicionLevel.HIGH
    assert report.delta == 20


def test_classify_student_active():
    strategy = SmartRatioSuspicionStrategy()
    level, explanation = strategy.classify_student(is_active=True, delta=10, ai_headcount=20)
    assert level == SuspicionLevel.NONE
    assert "פעיל" in explanation


def test_classify_student_inactive_high_risk():
    strategy = SmartRatioSuspicionStrategy()
    level, explanation = strategy.classify_student(is_active=False, delta=15, ai_headcount=20)
    assert level == SuspicionLevel.HIGH


def test_similarity_strategy_identical_code():
    strategy = TokenShingleSimilarity(k=3)
    code1 = {"file.py": "def foo(): return 1"}
    code2 = {"file.py": "def foo(): return 1"}

    fp1 = strategy.fingerprint(code1)
    fp2 = strategy.fingerprint(code2)

    score = strategy.score(fp1, fp2)
    assert score == 1.0  # 100% דמיון


def test_similarity_strategy_different_code():
    strategy = TokenShingleSimilarity(k=3)
    code1 = {"file.py": "def foo(): return 1"}
    code2 = {"file.py": "class Bar: pass"}

    fp1 = strategy.fingerprint(code1)
    fp2 = strategy.fingerprint(code2)

    score = strategy.score(fp1, fp2)
    assert score < 0.5  # דמיון נמוך