# Low-Level Class & Sequence Diagrams — Smart Classroom

**Project Name:** Smart Classroom — Web-Based Teaching Tool  
**Course:** Introduction to Software Engineering (OOP / OOD) — Ex2  
**Institution:** Ariel University  
**Document Purpose:** Deliverable #8 — Low-level UML Class Diagrams and Runtime Sequence Diagrams aligned 1:1 with `backend/` classes.

---

## 1. Low-Level Class Diagrams

### 1.1 Backend Architecture, Design Patterns & Services
This diagram illustrates the exact classes, interfaces, attributes, methods, and design patterns implemented in `backend/`: **Facade** (`SmartClassFacade`), **Factory** (`SystemFactory`), **Repository** (`IDataRepository` / `PocketBaseRepository`), and **Strategy** (`IHeadcountStrategy`, `ISuspicionStrategy`, `IExportStrategy`, `ISimilarityStrategy`).

```mermaid
classDiagram
    direction TB

    class SystemFactory {
        +bootstrap() SmartClassFacade
    }

    class SmartClassFacade {
        -attendance_service: AttendanceService
        -comparison_service: RepoComparisonService
        +configure(attendance_service, comparison_service) SmartClassFacade
        +get_public_tunnel_url() str
        +import_course_students(csv_path: str) dict
        +get_student_directory() list
        +start_attendance_session(title: str) dict
        +get_current_session() dict
        +register_student_attendance(student_name: str, class_code: str) dict
        +run_attendance_audit(session_id: str, image_bytes: bytes, mime_type: str) dict
        +override_student_attendance(session_id: str, student_id: str) dict
        +finalize_attendance_session(session_id: str, final_headcount: int) dict
        +generate_attendance_report(session_id: str) tuple
        +send_student_message(session_id: str, student_id: str, student_name: str, text: str) dict
        +create_poll(session_id: str, question: str, options: list) dict
        +get_active_poll(session_id: str) dict
        +vote_in_poll(poll_id: str, student_id: str, session_id: str, answer: str, student_name: str) dict
        +get_poll_results(poll_id: str) list
        +import_repos_csv(csv_text: str) dict
        +compare_my_repo(my_repo_url: str) dict
        +repos_status() dict
        +compare_for_student(my_repo_url: str) dict
    }

    class IDataRepository {
        <<interface>>
        +get_records(collection: str, filter_str: str, sort_str: str) list
        +create_record(collection: str, data: dict) dict
        +update_record(collection: str, record_id: str, data: dict) dict
    }

    class PocketBaseRepository {
        -base_url: str
        -admin_email: str
        -admin_password: str
        -_authenticate() str
        -_headers() dict
        -_request_with_retry(method: str, url: str) dict
        +get_records(collection: str, filter_str: str, sort_str: str) list
        +create_record(collection: str, data: dict) dict
        +update_record(collection: str, record_id: str, data: dict) dict
    }

    class AttendanceService {
        -repo: IDataRepository
        -headcount_strategy: IHeadcountStrategy
        -suspicion_strategy: ISuspicionStrategy
        -export_strategy: IExportStrategy
        +import_students_from_csv(csv_path: str) dict
        +list_students() list
        +open_session(title: str) ClassSession
        +get_active_or_latest_session() ClassSession
        +check_in_student(student_name: str, class_code: str) dict
        +audit_headcount(session_id: str, image_bytes: bytes, mime_type: str) AuditResult
        +manual_override(session_id: str, student_id: str) AttendanceRecord
        +close_session(session_id: str, final_headcount: int) ClassSession
        +export_attendance(session_id: str) tuple
        +send_message(session_id: str, student_id: str, student_name: str, text: str) dict
        +create_poll(session_id: str, question: str, options: list) dict
        +get_active_poll(session_id: str) dict
        +submit_poll_vote(poll_id: str, student_id: str, session_id: str, answer: str, student_name: str) dict
        +get_poll_results(poll_id: str) list
        -_collect_activity(session_id: str) dict
        -_upgrade_verification(session_id: str, student_id: str) None
    }

    class AuditResult {
        +report: SuspicionReport
        +students: list
        +to_dict() dict
    }

    class AIService {
        +summarize_content(file_bytes: bytes, mime_type: str) str
        +review_homework(repo_url: str) str
        -_generate_with_retry(contents: list) str
    }

    class RepoComparisonService {
        -repo: IDataRepository
        -github_client: GitHubClient
        -similarity_strategy: ISimilarityStrategy
        +import_repos_csv(csv_text: str) dict
        +count() int
        +compare(my_repo_url: str) dict
        +compare_for_student(my_repo_url: str) dict
        -_fingerprint(url: str) set
    }

    class GitHubClient {
        -token: str
        +parse_repo_url(url: str) tuple
        +fetch_code(url: str) dict
        -_headers() dict
        -_get(url: str) dict
    }

    class IHeadcountStrategy {
        <<interface>>
        +count_heads(image_bytes: bytes, mime_type: str) int
    }

    class GeminiVisionStrategy {
        -api_key: str
        -model_name: str
        +count_heads(image_bytes: bytes, mime_type: str) int
        -_generate_with_retry(contents: list) str
    }

    class MockHeadcountStrategy {
        -fixed_count: int
        +count_heads(image_bytes: bytes, mime_type: str) int
    }

    class ISuspicionStrategy {
        <<interface>>
        +calculate(registered_count: int, ai_headcount: int, verified_active_count: int) SuspicionReport
        +classify_student(is_active: bool, delta: int, ai_headcount: int) tuple
    }

    class SmartRatioSuspicionStrategy {
        +calculate(registered_count: int, ai_headcount: int, verified_active_count: int) SuspicionReport
        +classify_student(is_active: bool, delta: int, ai_headcount: int) tuple
    }

    class IExportStrategy {
        <<interface>>
        +media_type() str
        +file_extension() str
        +export(students: list, records: list, session_id: str) bytes
    }

    class ExcelExportStrategy {
        +media_type() str
        +file_extension() str
        +export(students: list, records: list, session_id: str) bytes
    }

    class ISimilarityStrategy {
        <<interface>>
        +fingerprint(sources: dict) set
        +score(a: set, b: set) float
    }

    class TokenShingleSimilarity {
        -k: int
        +fingerprint(sources: dict) set
        +score(a: set, b: set) float
        -_normalize(code: str) list
    }

    SystemFactory ..> SmartClassFacade : bootstraps
    SystemFactory ..> PocketBaseRepository : creates
    SystemFactory ..> AttendanceService : creates
    SystemFactory ..> RepoComparisonService : creates

    SmartClassFacade --> AttendanceService : delegates
    SmartClassFacade --> RepoComparisonService : delegates

    IDataRepository <|.. PocketBaseRepository : implements
    IHeadcountStrategy <|.. GeminiVisionStrategy : implements
    IHeadcountStrategy <|.. MockHeadcountStrategy : implements
    ISuspicionStrategy <|.. SmartRatioSuspicionStrategy : implements
    IExportStrategy <|.. ExcelExportStrategy : implements
    ISimilarityStrategy <|.. TokenShingleSimilarity : implements

    AttendanceService --> IDataRepository : persists via
    AttendanceService --> IHeadcountStrategy : uses
    AttendanceService --> ISuspicionStrategy : uses
    AttendanceService --> IExportStrategy : uses
    AttendanceService ..> AuditResult : returns

    RepoComparisonService --> IDataRepository : persists via
    RepoComparisonService --> GitHubClient : fetches code via
    RepoComparisonService --> ISimilarityStrategy : scores via
```

---

### 1.2 Domain Models & Custom Exception Hierarchy (`backend/models/`)
This diagram details the domain entities (`domain.py`) and custom domain exception hierarchy (`exceptions.py`).

```mermaid
classDiagram
    direction LR

    class SuspicionLevel {
        <<enumeration>>
        NONE
        LOW
        MEDIUM
        HIGH
    }

    class Student {
        +id: str
        +name: str
        +pin: str
        +email: str
        +group: str
    }

    class ClassSession {
        +id: str
        +title: str
        +class_code: str
        +status: str
        +final_headcount: int
        +to_dict() dict
    }

    class AttendanceRecord {
        +id: str
        +session_id: str
        +student_id: str
        +student_name: str
        +status: str
        +verification_level: str
        +created: str
        +to_dict() dict
    }

    class SuspicionReport {
        +registered_count: int
        +ai_headcount: int
        +delta: int
        +level: SuspicionLevel
        +explanation: str
        +to_dict() dict
    }

    ClassSession "1" --> "*" AttendanceRecord : tracks
    Student "1" --> "*" AttendanceRecord : checks in
    SuspicionReport --> SuspicionLevel : uses

    class DomainError {
        <<Exception>>
    }

    class SessionClosedError
    class InvalidCredentialsError
    class ResourceNotFoundError
    class ExternalServiceError

    DomainError <|-- SessionClosedError
    DomainError <|-- InvalidCredentialsError
    DomainError <|-- ResourceNotFoundError
    DomainError <|-- ExternalServiceError
```

---

## 2. Low-Level Sequence Diagrams

### 2.1 Session Opening, QR Sync & Real-Time Student Check-In (UC-01 & UC-02)

```mermaid
sequenceDiagram
    actor Lecturer
    participant LecUI as lecturer.html
    participant API as FastAPI (main.py)
    participant Facade as SmartClassFacade
    participant AttSvc as AttendanceService
    participant PB as PocketBaseRepository
    actor Student
    participant StuUI as index.html (/student)

    Lecturer->>LecUI: Click "פתח רישום נוכחות"
    LecUI->>API: POST /api/sessions/open (title)
    API->>Facade: start_attendance_session(title)
    Facade->>AttSvc: open_session(title)
    AttSvc->>PB: create_record("sessions", status="OPEN", class_code)
    PB-->>AttSvc: session record
    AttSvc-->>API: ClassSession.to_dict()
    API-->>LecUI: 200 OK (session)

    loop Poll until tunnel ready (qrPollTimer)
        LecUI->>API: GET /api/public-url
        API->>Facade: get_public_tunnel_url()
        Facade-->>API: "https://<id>.trycloudflare.com"
        API-->>LecUI: {url}
    end
    LecUI->>LecUI: Render QRCode("<url>/student") & subscribe WebSocket

    Student->>StuUI: Scan QR code & open /student
    StuUI->>API: GET /api/students/names
    API->>Facade: get_student_directory()
    Facade-->>StuUI: Student roster list
    Student->>StuUI: Select name, enter 2-digit code, tap "אשר נוכחות"
    StuUI->>API: POST /api/attendance/checkin (student_name, class_code)
    API->>Facade: register_student_attendance(student_name, class_code)
    Facade->>AttSvc: check_in_student(student_name, class_code)
    AttSvc->>PB: Validate OPEN session & create/update attendance (REGISTERED)
    PB-->>LecUI: WebSocket realtime event (attendance)
    LecUI->>LecUI: Increment live counter & refresh table
    AttSvc-->>StuUI: 200 OK (Check-in confirmed)
```

---

### 2.2 Asynchronous AI Vision Headcount & Suspicion Auditing (UC-03)

```mermaid
sequenceDiagram
    actor Lecturer
    participant LecUI as lecturer.html
    participant API as FastAPI (main.py)
    participant Jobs as job_store
    participant Facade as SmartClassFacade
    participant AttSvc as AttendanceService
    participant Vision as GeminiVisionStrategy
    participant Susp as SmartRatioSuspicionStrategy
    participant PB as PocketBaseRepository

    Lecturer->>LecUI: Upload classroom photo & click "ספור ראשים"
    LecUI->>API: POST /api/sessions/{id}/audit (multipart photo)
    API->>Jobs: submit(facade.run_attendance_audit, session_id, image_bytes, mime_type)
    Jobs-->>API: job_id
    API-->>LecUI: 200 OK {job_id}

    par Background Worker Thread
        Jobs->>Facade: run_attendance_audit(session_id, image_bytes, mime_type)
        Facade->>AttSvc: audit_headcount(session_id, image_bytes, mime_type)
        AttSvc->>Vision: count_heads(image_bytes, mime_type)
        Vision-->>AttSvc: ai_headcount
        AttSvc->>PB: get_records("attendance", "poll_votes", "messages")
        PB-->>AttSvc: session records & activity
        AttSvc->>Susp: calculate(registered_count, ai_headcount, verified_active_count)
        Susp-->>AttSvc: SuspicionReport
        loop For each registered student
            AttSvc->>Susp: classify_student(is_active, delta, ai_headcount)
            Susp-->>AttSvc: (SuspicionLevel, explanation)
        end
        AttSvc-->>Jobs: AuditResult.to_dict() (status="done")
    and Frontend Job Polling
        loop Every 700ms until status == "done"
            LecUI->>API: GET /api/jobs/{job_id}
            API->>Jobs: get(job_id)
            Jobs-->>LecUI: {status, result}
        end
    end

    LecUI->>LecUI: Render suspicion badge, headcount & per-student table
```

---

### 2.3 Live Student Q&A & Verification Upgrade (UC-05)

```mermaid
sequenceDiagram
    actor Student
    participant StuUI as index.html (/student)
    participant API as FastAPI (main.py)
    participant Facade as SmartClassFacade
    participant AttSvc as AttendanceService
    participant PB as PocketBaseRepository
    participant LecUI as lecturer.html

    Student->>StuUI: Type question & tap "שלח שאלה"
    StuUI->>API: POST /api/messages (session_id, student_id, student_name, text)
    API->>Facade: send_student_message(session_id, student_id, student_name, text)
    Facade->>AttSvc: send_message(...)
    AttSvc->>PB: create_record("messages", ...)
    AttSvc->>AttSvc: _upgrade_verification(session_id, student_id)
    AttSvc->>PB: update_record("attendance", verification_level="VERIFIED_ACTIVE")
    PB-->>LecUI: WebSocket realtime event (messages & attendance)
    LecUI->>LecUI: Append message to console & update verification badge
    AttSvc-->>StuUI: 200 OK
```

---

### 2.4 GitHub Repository Similarity Comparison (UC-08)

```mermaid
sequenceDiagram
    actor Lecturer
    participant LecUI as lecturer.html
    participant API as FastAPI (main.py)
    participant Facade as SmartClassFacade
    participant RepoSvc as RepoComparisonService
    participant GH as GitHubClient
    participant Sim as TokenShingleSimilarity
    participant PB as PocketBaseRepository

    Lecturer->>LecUI: Enter GitHub URL & click "השווה למטלות אחרות"
    LecUI->>API: GET /api/repos/compare?my_repo_url=<url>
    API->>Facade: compare_my_repo(my_repo_url)
    Facade->>RepoSvc: compare(my_repo_url)
    RepoSvc->>GH: fetch_code(my_repo_url)
    GH-->>RepoSvc: sources dict
    RepoSvc->>Sim: fingerprint(sources)
    Sim-->>RepoSvc: target_shingles (set)

    RepoSvc->>PB: get_records("repositories")
    PB-->>RepoSvc: Stored repository URLs

    loop For each stored repository
        RepoSvc->>RepoSvc: _fingerprint(repo_url)
        RepoSvc->>Sim: score(target_shingles, candidate_shingles)
        Sim-->>RepoSvc: similarity_score
    end

    RepoSvc-->>API: {similarity, compared_count, flagged}
    API-->>LecUI: 200 OK JSON
    LecUI->>LecUI: Render similarity percentage & status badge
```