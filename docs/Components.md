# Software Components Definition — Smart Classroom

**Project Name:** Smart Classroom — Web-Based Teaching Tool  
**Course:** Introduction to Software Engineering (OOP / OOD) — Ex2  
**Institution:** Ariel University  
**Document Purpose:** Deliverable #7 — Architectural decomposition and class-level component specification (aligned 1:1 with `backend/` and serving as the baseline for UML Diagrams in #8 and Class-Mapped Testing Strategy in #9).

---

## 1. Architectural Overview

**Smart Classroom** is organized into four decoupled layers orchestrated via Docker Compose:
1. **Infrastructure & Edge Layer:** Reverse proxy (`Caddy`), embedded database & realtime broker (`PocketBase`), and public HTTPS ingress (`Cloudflare Tunnel`).
2. **Presentation Layer (`frontend/`):** Zero-build, mobile-first HTML/JS views (`login.html`, `lecturer.html`, `index.html`).
3. **API & Orchestration Layer (`backend/`):** FastAPI REST endpoints (`main.py`), unified entry facade (`SmartClassFacade`), and dependency-injection factory (`SystemFactory`).
4. **Domain, Service, Strategy & Persistence Layer (`backend/*`):** Modular OOP packages implementing **SOLID** principles and **Facade, Factory, Strategy, and Repository** design patterns.

---

## 2. Infrastructure & Frontend Components

### 2.1 Infrastructure Microservices (`docker-compose.yml`, `Caddyfile`)
| Component | Container / File | Responsibilities |
| :--- | :--- | :--- |
| **Reverse Proxy** | `Caddy` (`class_proxy`) | Listens on port `8080`; routes `/api/*` to FastAPI (`backend:8000`), `/pb/*` to PocketBase (`pocketbase:8090`), and `/` to static HTML files, eliminating CORS issues. |
| **Database & Realtime Engine** | `PocketBase` (`class_pocketbase`) | Embedded SQLite database backed by Docker volume `pb_data`; provides REST CRUD APIs, superuser authentication, and Server-Sent Events (SSE) WebSocket streams. |
| **Public HTTPS Tunnel** | `Cloudflare Tunnel` (`class_tunnel`) | Runs `cloudflared` over `--protocol http2` to expose `http://proxy:80` on a public `*.trycloudflare.com` HTTPS endpoint for cellular 4G/5G student access. |

### 2.2 Frontend Presentation Components (`frontend/`)
| Component | Route | Responsibilities |
| :--- | :--- | :--- |
| **Lecturer Login View** | `/` (`login.html`) | Authenticates lecturer credentials against PocketBase and stores the auth token in `localStorage`. |
| **Lecturer Dashboard** | `/lecturer` (`lecturer.html`) | Real-time classroom control center: opens/closes sessions, projects dynamic QR codes with auto-polling, triggers async AI Vision headcount audits, displays live student Q&A console, manages KISS polls, downloads AI lecture summaries, exports spreadsheets, and runs GitHub similarity comparisons. |
| **Student Mobile App** | `/student` (`index.html`) | KISS smartphone interface requiring zero installation: allows 15-second attendance check-in, live question submission, and single-tap poll voting. |

---

## 3. Backend Core & OOP Components (`backend/`)

### 3.1 API & Orchestration Layer
* **`FastAPI Application` (`backend/main.py`)**
  * **Pattern Role:** HTTP Controller / Presentation Adapter.
  * **Responsibilities:** Exposes all REST endpoints (`/api/sessions/*`, `/api/attendance/*`, `/api/messages`, `/api/polls/*`, `/api/summarize`, `/api/review-homework`, `/api/repos/*`, `/api/jobs/{job_id}`, `/api/public-url`, `/api/students/*`), serves frontend HTML files, and executes startup schema auto-migration (`bootstrap_database()`).
* **`SmartClassFacade` (`backend/facade.py`)**
  * **Pattern Role:** **Facade Pattern** (Structural).
  * **Responsibilities:** Exposes a single unified API to `main.py`, decoupling HTTP handlers from internal service orchestration, repositories, and tunnel log parsing.
  * **Key Methods:** `configure()`, `get_public_tunnel_url()`, `import_course_students()`, `get_student_directory()`, `start_attendance_session()`, `get_current_session()`, `register_student_attendance()`, `run_attendance_audit()`, `override_student_attendance()`, `finalize_attendance_session()`, `generate_attendance_report()`, `send_student_message()`, `create_poll()`, `get_active_poll()`, `vote_in_poll()`, `get_poll_results()`, `import_repos_csv()`, `compare_my_repo()`, `repos_status()`, `compare_for_student()`.
* **`SystemFactory` (`backend/factory.py`)**
  * **Pattern Role:** **Factory Pattern** (Creational).
  * **Responsibilities:** Centralizes object creation and dependency wiring via `SystemFactory.bootstrap()`, instantiating `PocketBaseRepository`, concrete strategies (`GeminiVisionStrategy`, `SmartRatioSuspicionStrategy`, `ExcelExportStrategy`, `TokenShingleSimilarity`), `GitHubClient`, domain services (`AttendanceService`, `RepoComparisonService`), and returning a configured `SmartClassFacade`.

---

### 3.2 Domain Models & Exceptions (`backend/models/`)
* **`Domain Models` (`backend/models/domain.py`)**
  * **`SuspicionLevel(str, Enum)`:** Enumeration defining risk tiers (`NONE`, `LOW`, `MEDIUM`, `HIGH`).
  * **`Student`:** Represents a course student (`id`, `name`, `pin`, `email`, `group`).
  * **`ClassSession`:** Represents a lecture session (`id`, `title`, `class_code`, `status`, `final_headcount`, `to_dict()`).
  * **`AttendanceRecord`:** Represents a student's attendance entry (`id`, `session_id`, `student_id`, `student_name`, `status`, `verification_level`, `created`, `to_dict()`).
  * **`SuspicionReport`:** Encapsulates class-wide suspicion evaluation metrics (`registered_count`, `ai_headcount`, `delta`, `level`, `explanation`, `to_dict()`).
* **`Exception Hierarchy` (`backend/models/exceptions.py`)**
  * **`DomainError(Exception)`:** Base domain exception class.
  * **`SessionClosedError(DomainError)`:** Raised when an operation targets a closed or nonexistent session.
  * **`InvalidCredentialsError(DomainError)`:** Raised when a student enters an invalid 2-digit `class_code` or unrecognized credentials.
  * **`ResourceNotFoundError(DomainError)`:** Raised when a requested student, session, or poll does not exist.
  * **`ExternalServiceError(DomainError)`:** Raised when external APIs (PocketBase, Gemini, GitHub) fail or exceed rate limits.

---

### 3.3 Abstract Interfaces (`backend/interfaces/` & `backend/strategies/`)
* **`IDataRepository(ABC)` (`backend/interfaces/repository.py`)**
  * **Responsibilities:** Abstract persistence contract (`get_records`, `create_record`, `update_record`) isolating services from database implementation details.
* **`IHeadcountStrategy(ABC)` (`backend/interfaces/strategies.py`)**
  * **Responsibilities:** Contract `count_heads(image_bytes: bytes, mime_type: str) -> int` for classroom headcount estimation.
* **`ISuspicionStrategy(ABC)` (`backend/interfaces/strategies.py`)**
  * **Responsibilities:** Contract `calculate(...) -> SuspicionReport` and `classify_student(...)` for two-tier suspicion evaluation.
* **`IExportStrategy(ABC)` (`backend/interfaces/strategies.py`)**
  * **Responsibilities:** Contract `media_type()`, `file_extension()`, and `export(students, records, session_id) -> bytes` for attendance report generation.
* **`ISimilarityStrategy(ABC)` (`backend/strategies/similarity_strategy.py`)**
  * **Responsibilities:** Contract `fingerprint(sources: dict[str, str]) -> set[int]` and `score(a: set[int], b: set[int]) -> float` for code similarity comparison.

---

### 3.4 Persistence Layer (`backend/repositories/`)
* **`PocketBaseRepository(IDataRepository)` (`backend/repositories/pocketbase_repo.py`)**
  * **Pattern Role:** **Repository Pattern**.
  * **Responsibilities:** Implements `IDataRepository` over PocketBase's REST API, managing superuser authentication (`_authenticate`), authorization headers (`_headers`), and automatic retry on transient failures (`_request_with_retry`).

---

### 3.5 Business Logic & Integration Services (`backend/services/`)
* **`AuditResult` (`backend/services/attendance_service.py`)**
  * **Responsibilities:** Data transfer wrapper combining the class-level `SuspicionReport` with per-student suspicion breakdowns (`to_dict()`).
* **`AttendanceService` (`backend/services/attendance_service.py`)**
  * **Responsibilities:** Core classroom domain service managing student roster seeding (`import_students_from_csv`), session lifecycle (`open_session`, `close_session`, `get_active_or_latest_session`), idempotent student check-in (`check_in_student`), manual overrides (`manual_override`), live Q&A (`send_message`), KISS polls (`create_poll`, `get_active_poll`, `submit_poll_vote`, `get_poll_results`), automatic verification upgrades (`_upgrade_verification`), and hybrid vision auditing (`audit_headcount`) via injected `IHeadcountStrategy`, `ISuspicionStrategy`, and `IExportStrategy`.
* **`AIService` (`backend/services/ai_service.py`)**
  * **Responsibilities:** Encapsulates Google Gemini API calls (`_generate_with_retry`) with audio extraction (`extract_audio`) to generate Markdown lecture summaries (`summarize_content`) and automated homework reviews (`review_homework`).
* **`RepoComparisonService` (`backend/services/repo_comparison_service.py`)**
  * **Responsibilities:** Imports student GitHub URLs from CSV (`import_repos_csv`), computes and caches structural fingerprints (`_fingerprint`), and evaluates target submissions against the corpus (`compare`, `compare_for_student`).
* **`GitHubClient` (`backend/services/github_client.py`)**
  * **Responsibilities:** Parses GitHub URLs (`parse_repo_url`) and retrieves repository file trees and source files (`fetch_code`) using `GITHUB_TOKEN` authentication when configured.
* **`job_store` (`backend/services/job_store.py`)**
  * **Responsibilities:** Thread-safe background worker module (`submit`, `get`, `_run`, `_cleanup`) executing long-running AI Vision, video summarization, and repository comparison tasks asynchronously without blocking HTTP endpoints.

---

### 3.6 Concrete Strategy Implementations (`backend/strategies/`)
* **`GeminiVisionStrategy(IHeadcountStrategy)` (`backend/strategies/vision_strategy.py`)**
  * **Responsibilities:** Preprocesses images (`prepare_image`) and queries Gemini multimodal Vision (`_generate_with_retry`) to count visible students in classroom photos.
* **`MockHeadcountStrategy(IHeadcountStrategy)` (`backend/strategies/vision_strategy.py`)**
  * **Responsibilities:** Deterministic test/fallback strategy returning a configurable `fixed_count` without external API calls.
* **`SmartRatioSuspicionStrategy(ISuspicionStrategy)` (`backend/strategies/suspicion_strategy.py`)**
  * **Responsibilities:** Computes class-level suspicion (`calculate`) from the ratio/delta between registered check-ins, active participants, and AI headcount, and classifies each student (`classify_student`) into a `SuspicionLevel` with a Hebrew explanation.
* **`ExcelExportStrategy(IExportStrategy)` (`backend/strategies/export_strategy.py`)**
  * **Responsibilities:** Exports attendance rosters, statuses, and verification levels into an `.xlsx` Excel spreadsheet (`export`).
* **`TokenShingleSimilarity(ISimilarityStrategy)` (`backend/strategies/similarity_strategy.py`)**
  * **Responsibilities:** Normalizes source code tokens (`_normalize`), generates $k$-shingle hash sets (`fingerprint`, default `k=6`), and computes Jaccard/overlap similarity percentages (`score`).