import pytest
from models.exceptions import InvalidCredentialsError, SessionClosedError, ResourceNotFoundError


def test_check_in_success(attendance_service, mock_repo):
    mock_repo.get_records.side_effect = [
        [{"id": "sess1", "title": "הרצאה 1", "class_code": "99", "status": "OPEN", "created": "2026-01-01"}],
        [{"id": "123", "name": "גיא אביב", "email": "guy@gmail.com", "group": "3"}],
        []
    ]
    mock_repo.create_record.return_value = {
        "id": "rec1", "session_id": "sess1", "student_id": "123",
        "student_name": "גיא אביב", "status": "PRESENT",
        "verification_level": "REGISTERED", "created": "2026-01-01"
    }

    msg, record = attendance_service.check_in_student("גיא אביב", "99")

    assert "בהצלחה" in msg
    assert record.student_id == "123"
    mock_repo.create_record.assert_called_once()


def test_check_in_wrong_class_code(attendance_service, mock_repo):
    mock_repo.get_records.return_value = [
        {"id": "sess1", "title": "הרצאה 1", "class_code": "99", "status": "OPEN", "created": "2026-01-01"}
    ]
    with pytest.raises(InvalidCredentialsError):
        attendance_service.check_in_student("גיא אביב", "11")


def test_check_in_closed_session(attendance_service, mock_repo):
    mock_repo.get_records.return_value = [
        {"id": "sess1", "title": "הרצאה 1", "class_code": "99", "status": "CLOSED", "created": "2026-01-01"}
    ]
    with pytest.raises(SessionClosedError):
        attendance_service.check_in_student("גיא אביב", "99")


def test_check_in_unknown_student(attendance_service, mock_repo):
    mock_repo.get_records.side_effect = [
        [{"id": "sess1", "title": "הרצאה 1", "class_code": "99", "status": "OPEN", "created": "2026-01-01"}],
        []  # רשימת סטודנטים ריקה
    ]
    with pytest.raises(ResourceNotFoundError):
        attendance_service.check_in_student("לא קיים", "99")


def test_check_in_duplicate(attendance_service, mock_repo):
    mock_repo.get_records.side_effect = [
        [{"id": "sess1", "title": "הרצאה 1", "class_code": "99", "status": "OPEN", "created": "2026-01-01"}],
        [{"id": "123", "name": "גיא אביב", "email": "guy@gmail.com", "group": "3"}],
        [{"id": "rec1", "student_id": "123", "student_name": "גיא אביב", "status": "PRESENT",
          "verification_level": "REGISTERED", "created": "2026-01-01"}]
    ]

    msg, record = attendance_service.check_in_student("גיא אביב", "99")
    assert "כבר נרשמה" in msg
    mock_repo.create_record.assert_not_called()


def test_create_poll_closes_previous(attendance_service, mock_repo):
    mock_repo.get_records.return_value = [{"id": "poll1", "status": "active"}]
    attendance_service.create_poll("sess1", "שאלה חדשה", ["כן", "לא"])
    mock_repo.update_record.assert_called_once_with("polls", "poll1", {"status": "closed"})
    mock_repo.create_record.assert_called_once()


def test_send_message_upgrades_verification(attendance_service, mock_repo):
    mock_repo.get_records.return_value = [{"id": "rec1", "student_id": "123", "verification_level": "REGISTERED"}]

    attendance_service.send_message("sess1", "123", "גיא אביב", "שאלה?")

    mock_repo.create_record.assert_called_once()
    mock_repo.update_record.assert_called_once_with("attendance", "rec1", {"verification_level": "VERIFIED_ACTIVE"})


def test_submit_poll_vote_upgrades_verification(attendance_service, mock_repo):
    mock_repo.get_records.side_effect = [
        [],  # אין הצבעה קיימת
        [{"id": "rec1", "student_id": "123", "verification_level": "REGISTERED"}]  # רשומת נוכחות
    ]

    attendance_service.submit_poll_vote("poll1", "123", "sess1", "כן", "גיא אביב")

    mock_repo.create_record.assert_called_once()
    mock_repo.update_record.assert_called_once_with("attendance", "rec1", {"verification_level": "VERIFIED_ACTIVE"})


def test_audit_headcount(attendance_service, mock_repo):
    # מדמה 2 נרשמים, אחד מהם פעיל
    mock_repo.get_records.side_effect = [
        [{"id": "rec1", "student_id": "1", "student_name": "סטודנט 1", "verification_level": "VERIFIED_ACTIVE"},
         {"id": "rec2", "student_id": "2", "student_name": "סטודנט 2", "verification_level": "REGISTERED"}],
        # attendance
        [{"student_id": "1"}],  # messages (סטודנט 1 פעיל)
        []  # polls
    ]

    result = attendance_service.audit_headcount("sess1", b"image_bytes", "image/jpeg")

    assert result.report.registered_count == 2
    assert result.report.ai_headcount == 20  # MockHeadcountStrategy מחזיר 20
    assert len(result.students) == 2

    # הסטודנט הלא פעיל מקבל דרגת חשד גבוהה יותר ולכן מופיע ראשון ברשימה הממוינת
    assert result.students[0]["student_id"] == "2"
    assert result.students[1]["student_id"] == "1"