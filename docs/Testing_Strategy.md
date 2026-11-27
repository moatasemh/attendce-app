# Testing Strategy — Smart Classroom

**Project Name:** Smart Classroom — Web-Based Teaching Tool  
**Course:** Introduction to Software Engineering (OOP / OOD) — Ex2  
**Institution:** Ariel University  
**Document Purpose:** Deliverable #9 — Define the testing strategy, explicitly addressing all core classes defined in `Components.md`.

---

## 1. Testing Approach & Layers

The Smart Classroom testing strategy is organized into three distinct layers:

1. **Unit Tests (Class-Level):** Validate isolated algorithmic logic and OOP Strategy implementations without external dependencies.
2. **Service Tests (Mocked Integration):** Validate business logic and session lifecycle within `AttendanceService` using mocked repository interfaces (`MagicMock`).
3. **Load & System Tests (End-to-End):** Validate the full FastAPI + PocketBase stack under concurrent load conditions (50 simulated students).

---

## 2. Class-Level Testing Matrix

The following table maps all **18 core system classes and interfaces** to their respective test cases:

| Class Under Test | Test Objective | Test Type | Expected Result |
| :--- | :--- | :--- | :--- |
| **`SmartRatioSuspicionStrategy`** | Verify class-level and per-student suspicion calculations based on headcount deltas and activity levels. | Unit | Correct `SuspicionLevel` enum (`NONE`, `LOW`, `MEDIUM`, `HIGH`). |
| **`TokenShingleSimilarity`** | Verify structural code fingerprinting normalizes tokens and computes Jaccard similarity scores. | Unit | Identical code yields 1.0; different code yields < 0.5. |
| **`ExcelExportStrategy`** | Verify spreadsheet generation includes correct headers and handles data conversion. | Unit | Returns `bytes` representing a valid `.xlsx` file (starts with `PK`). |
| **`GeminiVisionStrategy`** | Verify `count_heads` parsing logic and fallback behavior on API failure. | Unit (Mocked API) | Extracts integer from string; raises `ExternalServiceError` on failure. |
| **`MockHeadcountStrategy`** | Verify it returns the configured fixed count. | Unit | Returns `fixed_count`. |
| **`GitHubClient`** | Verify URL parsing regex and repository tree fetching (mocked). | Unit (Mocked HTTP) | Correctly parses `owner/repo`; returns `dict` of file contents. |
| **`AttendanceService`** | Verify `check_in_student` handles valid sessions, invalid codes, closed sessions, unknown students, and duplicates. | Service (Mocked) | `InvalidCredentialsError`, `SessionClosedError`, `ResourceNotFoundError` raised correctly; no duplicate writes. |
| **`AttendanceService`** | Verify `audit_headcount` combines headcount, activity, and suspicion strategies. | Service (Mocked) | Returns `AuditResult` with calculated `SuspicionReport` and per-student list. |
| **`AttendanceService`** | Verify `send_message` and `submit_poll_vote` trigger `_upgrade_verification`. | Service (Mocked) | `verification_level` updated to `VERIFIED_ACTIVE`. |
| **`AttendanceService`** | Verify `create_poll` closes previously active polls. | Service (Mocked) | Previous poll status updated to `closed`. |
| **`RepoComparisonService`** | Verify CSV ingestion and pairwise comparison logic. | Service (Mocked) | Correct `added` counts; correct similarity score and threshold flagging. |
| **`SmartClassFacade`** | Verify tunnel URL extraction from log file. | Unit (File Mock) | Extracts latest URL from `tunnel.log`. |
| **`SystemFactory`** | Verify object graph instantiation (Dependency Injection). | Unit | Returns a fully configured `SmartClassFacade` instance. |
| **`PocketBaseRepository`** | Verify HTTP request retry logic and authentication flow. | Unit (Mocked HTTP) | Handles `401` by re-authenticating and retrying. |
| **`AIService`** | Verify audio extraction and Gemini API call mocking. | Unit (Mocked API) | Returns Markdown summary string. |
| **`AuditResult`** | Verify `to_dict()` serializes report and students correctly. | Unit | Returns a combined dictionary. |
| **`Domain Models`** | Verify dataclass initialization and `to_dict()` methods. | Unit | Correct dictionary representation. |
| **`Exception Hierarchy`** | Verify custom exceptions raise properly and are caught by API handlers. | Unit | Correct inheritance and message propagation. |

---

## 3. Automated Test Suite

The automated suite uses `pytest` and `pytest-mock`. It is organized into three files:
*   **`tests/conftest.py`:** Configures mocked dependencies and sample domain entities.
*   **`tests/test_services.py`:** Tests `AttendanceService` (check-in, closed sessions, invalid students, polls, messages, vision audit).
*   **`tests/test_facade_and_repos.py`:** Tests `RepoComparisonService`, `GitHubClient`, `ExcelExportStrategy`, and `SmartClassFacade`.

### How to Run the Tests
```bash
docker exec -it class_python_backend pytest /app/tests -v