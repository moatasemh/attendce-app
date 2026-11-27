# Software Requirements Specification (SRS) — Smart Classroom

**Project Name:** Smart Classroom — Web-Based Teaching Tool  
**Course:** Introduction to Software Engineering (OOP / OOD) — Ex2  
**Institution:** Ariel University  
**Version:** 1.0  

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) defines the complete functional, non-functional, interface, and data requirements for the **Smart Classroom** system. It serves as the authoritative technical baseline for system architecture, implementation, and verification testing.

### 1.2 Scope
**Smart Classroom** is a lightweight, LLM-ready web application designed to facilitate real-time interaction during university lectures. It enables frictionless mobile attendance check-in, AI-powered classroom photo auditing, live student Q&A, instant comprehension polls, automated lecture summarization, and GitHub homework similarity detection—without requiring student app installations or external LMS integrations.

### 1.3 Definitions, Acronyms, and Abbreviations
* **KISS:** Keep It Simple, Stupid — design principle prioritizing minimal friction and rapid usability.
* **LLM:** Large Language Model (Google Gemini `gemini-3.5-flash-lite` / `gemini-3.5-flash`).
* **REST API:** Representational State Transfer Application Programming Interface.
* **WebSocket (Realtime):** Full-duplex communication channel used by PocketBase to push live database updates to the lecturer UI.
* **Audit / Suspicion Level:** Automated risk classification (`NONE`, `LOW`, `MEDIUM`, `HIGH`) comparing digital check-ins against physical headcount and live student participation.

### 1.4 References
* `README.md` — Project Overview, Architecture & Setup Guide
* `docs/Tools_Report.md` — Technical Tools Evaluation & Empirical Benchmarks
* `docs/SoW.md` — Statement of Work

---

## 2. Overall Description

### 2.1 Product Perspective
Smart Classroom operates as a containerized microservices stack orchestrated via Docker Compose:
* **Reverse Proxy (`Caddy`):** Exposes a single unified HTTP entry point (`port 8080`), routing traffic between static frontend pages, FastAPI REST endpoints (`/api/*`), and PocketBase (`/pb/*`).
* **Backend Service (`FastAPI`):** Implements domain logic, SOLID/OOP design patterns (`SmartClassFacade`, `SystemFactory`, Strategy & Repository patterns), background AI job execution (`job_store`), and database auto-migration.
* **Database & Realtime Engine (`PocketBase`):** Embedded SQLite database running on an internal Docker volume with built-in authentication and real-time event streaming.
* **Public Ingress (`Cloudflare Tunnel`):** Dynamically exposes the local proxy over HTTPS (`trycloudflare.com`) so students can connect via cellular networks (4G/5G).

### 2.2 User Classes and Characteristics
1. **Lecturer (Authenticated Admin/Instructor):**
   * Logs into the web dashboard (`/lecturer`) from a classroom laptop connected to a projector.
   * Opens/closes attendance sessions, projects the dynamic QR code, triggers AI photo audits, moderates live student questions, launches instant polls, generates lecture summaries, and runs GitHub repository similarity comparisons.
2. **Student (Unauthenticated Mobile Web User):**
   * Scans the projected QR code using any standard smartphone browser (`/student`).
   * Requires zero installation, zero password setup, and minimal typing (selects name from roster and enters a 2-digit session code).

### 2.3 Operating Environment
* **Server Host:** Docker Engine / Docker Desktop (Linux containers) with outbound internet access for Gemini API, GitHub API, and HTTPS tunneling.
* **Lecturer Client:** Desktop browser (Chrome, Edge, Firefox, Safari) at minimum 1280×720 resolution.
* **Student Client:** Mobile browser (iOS Safari, Android Chrome) over cellular data (4G/5G) or campus Wi-Fi.

### 2.4 Design and Implementation Constraints
* **No Institutional Integration:** Must operate independently of Moodle, Zoom, and university SSO (*מידע אישי*).
* **Non-Blocking AI Operations:** Long-running multimodal AI tasks (image headcount, `.mp4` video summarization, repository comparison) must not block synchronous HTTP worker threads.
* **Anonymous Photo Processing:** Classroom photographs must be processed strictly for aggregate headcount estimation without biometric facial identification.

---

## 3. System Features & Functional Requirements

### 3.1 Feature 1: Session Management & Authentication
* **FR-1.1:** The system shall authenticate lecturers via PocketBase admin credentials before granting access to `/lecturer`.
* **FR-1.2:** The system shall automatically initialize required database collections (`sessions`, `students`, `attendance`, `messages`, `polls`, `poll_votes`, `repositories`) and seed the initial student roster (`demo_assets/students.csv`) if empty.
* **FR-1.3:** The lecturer shall be able to open a new lecture session (`POST /api/sessions/open`) with a custom title, generating a unique 2-digit numeric `class_code` and setting session status to `OPEN`.
* **FR-1.4:** The lecturer dashboard shall automatically discover the active public tunnel URL (`GET /api/public-url`) and render a live QR code pointing to `<PUBLIC_URL>/student`.
* **FR-1.5:** The lecturer shall be able to close an active session (`POST /api/sessions/{session_id}/close`), recording the final confirmed headcount and setting status to `CLOSED`.

### 3.2 Feature 2: Hybrid Attendance & Suspicion Auditing (Primary Feature)
* **FR-2.1:** A student shall be able to mark attendance (`POST /api/attendance/checkin`) by selecting their name and submitting the active 2-digit `class_code`.
* **FR-2.2:** The system shall reject check-in attempts with an invalid `class_code` (`InvalidCredentialsError`), an unrecognized student name (`ResourceNotFoundError`), or when no `OPEN` session exists (`SessionClosedError`), returning an explicit HTTP error (`400`/`404`).
* **FR-2.3:** Duplicate check-ins by the same student within the same session shall be handled idempotently without creating duplicate attendance records.
* **FR-2.4:** Upon valid check-in, the student's initial verification level shall be recorded as `REGISTERED`, and the lecturer's attendance counter and table shall update in real time via WebSocket.
* **FR-2.5:** The lecturer shall be able to manually toggle/override any student's attendance status (`POST /api/sessions/{session_id}/override/{student_id}`).
* **FR-2.6:** The lecturer shall be able to upload a classroom photograph (`POST /api/sessions/{session_id}/audit`) to trigger an asynchronous AI Vision headcount (`IHeadcountStrategy` / `GeminiVisionStrategy`).
* **FR-2.7:** Upon headcount completion, `ISuspicionStrategy` (`SmartRatioSuspicionStrategy`) shall compute:
  * **Class-level suspicion (`SuspicionLevel`: `NONE`, `LOW`, `MEDIUM`, `HIGH`)** and explanation based on the delta between `registered_count` and `ai_headcount`.
  * **Per-student suspicion level** factoring in verification level (`VERIFIED_ACTIVE` vs. `REGISTERED`), polls answered, and questions submitted.
* **FR-2.8:** The lecturer shall be able to export the session's attendance roster, status, and verification levels as a downloadable Excel spreadsheet (`GET /api/sessions/{session_id}/export` via `IExportStrategy` / `ExcelExportStrategy`).

### 3.3 Feature 3: Real-Time Student Q&A & Suggestions
* **FR-3.1:** Checked-in students shall be able to submit text questions or feedback (`POST /api/messages`) during an `OPEN` session.
* **FR-3.2:** Submitted messages shall appear immediately in the lecturer's live console via PocketBase Realtime subscription, auto-scrolling to the latest entry.
* **FR-3.3:** Submitting a valid message shall automatically upgrade the student's attendance `verification_level` from `REGISTERED` to `VERIFIED_ACTIVE`.

### 3.4 Feature 4: On-the-Spot KISS Polls
* **FR-4.1:** The lecturer shall be able to create a live multiple-choice poll (`POST /api/polls`) by specifying a question and comma-separated answer options, automatically closing any previously active poll (`status="closed"`).
* **FR-4.2:** Active polls (`GET /api/polls/active`) shall automatically appear on connected student mobile interfaces.
* **FR-4.3:** Students shall be able to submit one vote per active poll (`POST /api/polls/{poll_id}/vote`), upgrading their verification level to `VERIFIED_ACTIVE`.
* **FR-4.4:** The lecturer dashboard shall display live individual and aggregated poll responses (`GET /api/polls/{poll_id}/results`).

### 3.5 Feature 5: AI Class Video & Transcript Summarizer
* **FR-5.1:** The lecturer shall be able to upload a recorded lecture video (`.mp4`) or text transcript (`.txt`) (`POST /api/summarize`) to generate a structured lecture summary.
* **FR-5.2:** Summarization shall execute asynchronously via `job_store` (`GET /api/jobs/{job_id}`) using `AIService` and Google Gemini (`gemini-3.5-flash-lite` with fallback to `gemini-3.5-flash`).
* **FR-5.3:** Upon completion, the lecturer UI shall automatically trigger a downloadable Markdown summary file (`summary_<session_id>.md`).

### 3.6 Feature 6: GitHub Repository Similarity Comparison
* **FR-6.1:** The lecturer (and students via the comparison endpoint) shall be able to compare a target GitHub repository URL (`GET /api/repos/compare`) against the stored student repository corpus to detect code similarity.
* **FR-6.2:** The lecturer shall be able to import a CSV list of student GitHub repository URLs (`POST /api/repos/import`) into the active comparison corpus via `RepoComparisonService`.
* **FR-6.3:** Given a target GitHub repository URL, `RepoComparisonService` shall fetch source files via `GitHubClient`, extract structural $k$-shingle code fingerprints (`ISimilarityStrategy` / `TokenShingleSimilarity`), compare against all stored repositories, and return the maximum similarity percentage, count of compared repositories, and a plagiarism flag (`flagged: true` if above threshold).

---

## 4. External Interface Requirements

### 4.1 User Interfaces
* **Login Screen (`/` — `login.html`):** Minimalist authentication form storing the PocketBase auth token in `localStorage`.
* **Lecturer Dashboard (`/lecturer` — `lecturer.html`):** RTL Hebrew interface built with Pico.css containing five modular cards: Session & QR Projector, Hybrid Vision Audit, Live Q&A / Polls / AI Summary, Real-Time Attendance Table, and GitHub Assignment Comparison.
* **Student Mobile View (`/student` — `index.html`):** Single-column mobile-first RTL interface displaying session check-in, active poll voting card, and live question submission box.

### 4.2 Software & External API Interfaces
* **PocketBase REST & Realtime API (`/pb/api/*`):** Internal HTTP JSON API and Server-Sent Events (SSE) WebSocket stream managed by `PocketBaseRepository`.
* **Google Gemini API (`google-genai` SDK):** Multimodal `generate_content` calls over HTTPS authenticated via `GEMINI_API_KEY` (`GeminiVisionStrategy` and `AIService`).
* **GitHub REST API (`api.github.com`):** Repository tree and blob retrieval over HTTPS authenticated via `GITHUB_TOKEN` (`GitHubClient`).

---

## 5. Non-Functional Requirements

### 5.1 Performance & Latency
* **NFR-1.1:** Standard REST operations (check-in, poll vote, message submission) shall respond in **< 300 ms** under normal load.
* **NFR-1.2:** AI Vision headcount audits shall complete within **1–4 seconds**; lecture video summaries shall complete within **3–15 seconds** depending on file size.
* **NFR-1.3:** Student mobile page initial payload shall remain under **100 KB** (excluding CDN CSS/JS) for rapid loading over cellular networks.

### 5.2 Concurrency & Scalability
* **NFR-2.1:** The system shall support at least **50 concurrent students** performing simultaneous check-ins, poll votes, and Q&A submissions within a 5-second burst window with **0% failed requests** and zero SQLite locking errors.

### 5.3 Reliability & Fault Tolerance
* **NFR-3.1:** All AI calls in `GeminiVisionStrategy` and `AIService` shall implement automatic retry logic and model fallback (`gemini-3.5-flash-lite` → `gemini-3.5-flash`) with strict request timeouts.
* **NFR-3.2:** `RepoComparisonService` and `GitHubClient` shall cache repository fingerprints in memory and handle HTTP `403`/`429` rate-limit responses gracefully with descriptive Hebrew error messages (`ExternalServiceError`).
* **NFR-3.3:** Containers shall be configured with `restart: unless-stopped` and persistent Docker volumes (`pb_data`) to preserve session data across service restarts.

### 5.4 Security & Privacy
* **NFR-4.1:** Sensitive credentials (`GEMINI_API_KEY`, `GITHUB_TOKEN`, `PB_ADMIN_PASSWORD`) shall be injected strictly via environment variables (`.env`) and excluded from version control (`.gitignore`).
* **NFR-4.2:** All dynamic user inputs rendered in the lecturer and student DOM (student names, live questions, poll options, suspicion explanations) shall be HTML-escaped to prevent Cross-Site Scripting (XSS).

### 5.5 Usability
* **NFR-5.1:** A first-time student shall be able to scan the QR code and complete attendance registration in **under 15 seconds** without verbal instructions.

---

## 6. Data Model & Persistence Schema

PocketBase maintains the following relational collections inside `pb_data`:

| Collection | Key Fields | Description |
| :--- | :--- | :--- |
| `sessions` | `id`, `title`, `class_code`, `status` (`OPEN`/`CLOSED`), `final_headcount`, `created` | Represents a single lecture instance. |
| `students` | `id`, `name`, `pin`, `email`, `group` | Class roster seeded from `demo_assets/students.csv`. |
| `attendance` | `id`, `session_id`, `student_id`, `student_name`, `status` (`PRESENT`/`ABSENT`), `verification_level` (`REGISTERED`/`VERIFIED_ACTIVE`), `created` | Links students to sessions and tracks active participation. |
| `messages` | `id`, `session_id`, `student_id`, `student_name`, `text`, `created` | Live questions and comments submitted during class. |
| `polls` | `id`, `session_id`, `question`, `options` (JSON), `status` (`active`/`closed`) | Quick multiple-choice polls launched by the lecturer. |
| `poll_votes` | `id`, `poll_id`, `student_id`, `student_name`, `answer` | Individual student responses to active polls. |
| `repositories` | `id`, `repo_url`, `student_name`, `fingerprint` | Stored GitHub assignment links for similarity comparison. |