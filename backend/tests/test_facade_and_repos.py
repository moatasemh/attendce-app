import pytest
import io
import os
from unittest.mock import MagicMock, mock_open, patch
from services.repo_comparison_service import RepoComparisonService
from services.github_client import GitHubClient
from strategies.similarity_strategy import TokenShingleSimilarity
from strategies.export_strategy import ExcelExportStrategy
from facade import SmartClassFacade
from models.domain import Student, AttendanceRecord


def test_excel_export_strategy():
    strategy = ExcelExportStrategy()
    # שימוש באובייקטים אמיתיים במקום MagicMock
    students = [Student(id="1", name="Test", pin="", email="test@test.com", group="A")]
    records = [AttendanceRecord(id="r1", session_id="s1", student_id="1", student_name="Test", status="PRESENT",
                                verification_level="REGISTERED", created="2026")]

    output = strategy.export(students, records)

    assert isinstance(output, bytes)
    assert len(output) > 0
    assert output.startswith(b'PK')  # ZIP signature


# תוקן: patch ל-requests.get ולא ל-Session.get
@patch('services.github_client.requests.get')
def test_github_client_parse_and_fetch(mock_get):
    client = GitHubClient(token="fake_token")
    assert client.parse_repo_url("https://github.com/user/repo") == ("user", "repo")

    # Mock tree response
    mock_tree_response = MagicMock()
    mock_tree_response.status_code = 200
    mock_tree_response.json.return_value = {"tree": [{"path": "main.py", "type": "blob", "size": 100}]}

    # Mock file content response
    mock_file_response = MagicMock()
    mock_file_response.status_code = 200
    mock_file_response.text = "print('hello')"

    # מגדירים את הסדר של התגובות
    mock_get.side_effect = [mock_tree_response, mock_file_response]

    sources = client.fetch_code("https://github.com/user/repo")
    assert "main.py" in sources
    assert sources["main.py"] == "print('hello')"


def test_repo_comparison_service(mock_repo):
    github_client = MagicMock()
    github_client.fetch_code.return_value = {"main.py": "def foo(): pass"}
    similarity = TokenShingleSimilarity()

    service = RepoComparisonService(mock_repo, github_client, similarity)

    csv_text = "Email Address,Link to your Ex1 repository (@ Github)\ntest@test.com,https://github.com/user/repo"
    res = service.import_repos_csv(csv_text)
    assert res["added"] == 1

    mock_repo.get_records.return_value = [{"repo_url": "https://github.com/other/repo"}]
    service._fingerprint_cache = {
        "https://github.com/other/repo": similarity.fingerprint({"main.py": "def bar(): pass"})}

    result = service.compare("https://github.com/user/repo")
    assert "similarity" in result
    assert result["compared_count"] == 1


def test_facade_tunnel_url(tmp_path):
    log_file = tmp_path / "tunnel.log"
    log_file.write_text(
        'Info: Requesting new quick Tunnel...\nYour quick Tunnel has been created! Visit it at https://test-tunnel.trycloudflare.com\n')

    att_service = MagicMock()
    facade = SmartClassFacade(attendance_service=att_service)

    with patch('facade.os.path.exists', return_value=True), \
            patch('facade.open', mock_open(read_data=log_file.read_text())):
        url = facade.get_public_tunnel_url()
        assert url == "https://test-tunnel.trycloudflare.com"