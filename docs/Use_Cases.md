# Use Cases & Client Stories — Smart Classroom

**Project Name:** Smart Classroom — Web-Based Teaching Tool  
**Course:** Introduction to Software Engineering (OOP / OOD) — Ex2  
**Institution:** Ariel University  
**Document Purpose:** Deliverable #6 — Client stories and detailed end-to-end use case specifications.

---

## 1. System Actors

| Actor | Type | Description |
| :--- | :--- | :--- |
| **Lecturer** | Primary Human Actor | Authenticated instructor operating `/lecturer` from a classroom laptop connected to a projector. |
| **Student** | Primary Human Actor | Unauthenticated student accessing `/student` from a smartphone browser via QR code. |
| **Google Gemini API** | Secondary System Actor | External multimodal LLM service performing classroom headcounts (`GeminiVisionStrategy`) and lecture summarization (`AIService`). |
| **GitHub REST API** | Secondary System Actor | External code hosting API queried by `GitHubClient` to fetch repository trees and source code for similarity comparison. |

---

## 2. Client Stories (Agile User Stories)

### Lecturer Stories
* **US-L1 (Session & QR Setup):** *As a lecturer, I want to open a class session with one click and project a live QR code with a 2-digit code, so that students can join immediately without installing an app or logging in.*
* **US-L2 (AI Attendance Audit):** *As a lecturer, I want to snap and upload a photo of the classroom to automatically count heads and flag discrepancies against digital check-ins, so that I can verify physical attendance in seconds without manual roll call.*
* **US-L3 (Attendance Export):** *As a lecturer, I want to manually override individual attendance statuses when needed and export the final sheet to Excel, so that I have a reliable record for course administration.*
* **US-L4 (Live Student Q&A):** *As a lecturer, I want to see student questions stream into a live console during my lecture, so that shy or back-row students can ask questions without interrupting the flow.*
* **US-L5 (On-the-Spot KISS Polls):** *As a lecturer, I want to launch a quick multiple-choice poll mid-lecture and watch answers update in real time, so that I can immediately gauge whether the class understood a concept.*
* **US-L6 (AI Lecture Summary):** *As a lecturer, I want to upload a recorded lecture video or transcript and receive a structured Markdown summary, so that I can share clean study notes with the class.*
* **US-L7 (GitHub Repository Similarity Comparison):** *As a lecturer, I want to enter a target GitHub repository URL and compare it against the class repository corpus, so that I can automatically detect structural code similarity and potential plagiarism.*

### Student Stories
* **US-S1 (Zero-Friction Check-In):** *As a student, I want to scan the projected QR code on my phone, pick my name, and enter a 2-digit number, so that my attendance is marked in under 15 seconds.*
* **US-S2 (Real-Time Question Submission):** *As a student, I want to send questions or suggestions from my phone during class, so that the lecturer sees my question immediately and knows I am actively participating.*
* **US-S3 (Instant Poll Voting):** *As a student, I want active class polls to pop up automatically on my phone so I can vote with a single tap.*

---

## 3. Detailed Use Case Specifications

### UC-01: Open Lecture Session & Project Dynamic QR Code
* **Primary Actor:** Lecturer
* **Preconditions:** Lecturer is logged in (`localStorage.pb_auth` valid) and viewing `/lecturer`.
* **Main Flow:**
  1. Lecturer enters a session title (e.g., `"הרצאה 1 - תכנות מונחה עצמים"`) and clicks **"פתח רישום נוכחות"**.
  2. Frontend sends `POST /api/sessions/open` with the session title.
  3. `SmartClassFacade` delegates to `AttendanceService`, which seeds the student roster (`demo_assets/students.csv`) if empty, generates a random 2-digit `class_code`, creates an `OPEN` `ClassSession` record in PocketBase, and returns the session object.
  4. Frontend queries `GET /api/public-url` (`SmartClassFacade.get_public_tunnel_url()`) to retrieve the active HTTPS tunnel URL (`trycloudflare.com`).
  5. Lecturer dashboard displays the 2-digit code, renders the dynamic QR code pointing to `<PUBLIC_URL>/student`, and initializes live WebSocket subscriptions.
* **Alternative / Exception Flows:**
  * *AF-1 (Tunnel still initializing):* If `/api/public-url` initially returns `null`, `lecturer.html` polls every 1.5 seconds (`qrPollTimer`) and automatically renders the QR code as soon as the tunnel URL becomes available.
  * *EF-1 (Database error):* Server returns HTTP `500` with an error detail alert.
* **Postconditions:** An `OPEN` lecture session is active and ready to accept student check-ins.

---

### UC-02: Zero-Friction Mobile Attendance Check-In
* **Primary Actor:** Student
* **Preconditions:** An `OPEN` lecture session exists; student has scanned the projected QR code on a smartphone.
* **Main Flow:**
  1. Student opens `/student` (`index.html`), which fetches the student roster (`GET /api/students/names`).
  2. Student selects their name from the dropdown, types the 2-digit `class_code` shown on the projector, and taps **"אשר נוכחות"**.
  3. Frontend sends `POST /api/attendance/checkin` (`student_name`, `class_code`).
  4. `AttendanceService.check_in_student()` validates the `class_code` against the active `OPEN` session and creates an `AttendanceRecord` with `status="PRESENT"` and `verification_level="REGISTERED"`.
  5. PocketBase broadcasts the database change via WebSocket; the lecturer's live attendance counter and table update immediately.
* **Alternative / Exception Flows:**
  * *AF-1 (Duplicate check-in):* If the student submits check-in again in the same session, `AttendanceService` treats the operation idempotently without creating duplicate rows.
  * *EF-1 (Invalid class code, closed session, or unknown student):* Backend raises `InvalidCredentialsError`, `SessionClosedError`, or `ResourceNotFoundError` (`400`/`404`) and displays a clear Hebrew validation error on the student's phone.
* **Postconditions:** Student is registered as `PRESENT` and unlocked for live Q&A and poll participation.

---

### UC-03: Hybrid AI Vision Headcount & Suspicion Auditing
* **Primary Actor:** Lecturer | **Secondary Actor:** Google Gemini API
* **Preconditions:** An `OPEN` session has registered students; lecturer has captured or selected a classroom photograph.
* **Main Flow:**
  1. Lecturer selects an image file in `#class-photo` and clicks **"ספור ראשים וחשב דרגת חשד"**.
  2. Frontend sends `POST /api/sessions/{session_id}/audit` (`multipart/form-data`).
  3. Backend enqueues `SmartClassFacade.run_attendance_audit()` in `job_store` and immediately returns a `job_id`.
  4. Background worker invokes `GeminiVisionStrategy.count_heads()` (`gemini-3.5-flash-lite`) to count visible students in the photo, then passes `registered_count`, `ai_headcount`, and `verified_active_count` to `SmartRatioSuspicionStrategy`.
  5. Frontend polls `GET /api/jobs/{job_id}` until `status === "done"`, then displays the class-level `SuspicionReport` badge (`NONE`, `LOW`, `MEDIUM`, `HIGH`), headcount delta, and per-student suspicion breakdown table.
* **Alternative / Exception Flows:**
  * *EF-1 (Primary model timeout or unavailability):* `GeminiVisionStrategy` automatically retries and falls back to `gemini-3.5-flash`.
  * *EF-2 (API failure):* `ExternalServiceError` is caught by `job_store`, setting status to `"error"` with a descriptive alert.
* **Postconditions:** Suggested final headcount is pre-filled in `#final-headcount` for lecturer confirmation before closing the session.

---

### UC-04: Manual Attendance Override & Spreadsheet Export
* **Primary Actor:** Lecturer
* **Preconditions:** A session exists with a loaded student roster.
* **Main Flow:**
  1. Lecturer clicks **"סמן ידנית"** next to any student row in the live attendance table (`POST /api/sessions/{session_id}/override/{student_id}`).
  2. `AttendanceService.manual_override()` toggles the student's attendance status (`PRESENT` / `ABSENT`) and refreshes the table.
  3. When ready, lecturer clicks **"ייצוא גיליון Excel"** (`GET /api/sessions/{session_id}/export`).
  4. `AttendanceService.export_attendance()` delegates to `ExcelExportStrategy` to generate a formatted `.xlsx` workbook containing student names, groups, statuses, and verification levels, returning it as a file download.
* **Postconditions:** Lecturer obtains an offline `.xlsx` spreadsheet of the session's attendance record.

---

### UC-05: Real-Time Student Q&A & Verification Upgrade
* **Primary Actor:** Student | **Secondary Actor:** Lecturer
* **Preconditions:** Student is checked into an active `OPEN` session.
* **Main Flow:**
  1. Student types a question or comment in the mobile UI and taps **"שלח שאלה"**.
  2. Frontend sends `POST /api/messages` (`session_id`, `student_id`, `student_name`, `text`).
  3. `AttendanceService.send_message()` persists the message in PocketBase and calls `_upgrade_verification()` to automatically upgrade the student's attendance `verification_level` from `REGISTERED` to `VERIFIED_ACTIVE`.
  4. Lecturer's live console receives the message via PocketBase Realtime subscription, appends `[Student Name]: Question`, scrolls to the bottom, and updates the browser tab title to `"(!) שאלה חדשה"`.
* **Postconditions:** Question is logged and displayed to the lecturer; student's active presence is confirmed (`VERIFIED_ACTIVE`).

---

### UC-06: On-the-Spot KISS Poll Creation & Live Voting
* **Primary Actor:** Lecturer & Student
* **Preconditions:** An `OPEN` lecture session is active.
* **Main Flow:**
  1. Lecturer enters a question and comma-separated options (e.g., `"כן, לא, חלקית"`) and clicks **"צור סקר"** (`POST /api/polls`).
  2. `AttendanceService.create_poll()` closes any previously active poll (`status="closed"`) and creates a new poll with `status="active"`.
  3. Connected student mobile clients detect the new active poll (`GET /api/polls/active`) and render clickable option buttons.
  4. Student taps an option (`POST /api/polls/{poll_id}/vote`), recording their vote in `poll_votes` and upgrading their verification level to `VERIFIED_ACTIVE`.
  5. Lecturer dashboard polls `GET /api/polls/{poll_id}/results` and displays live student votes in `#poll-results-tbody`.
* **Alternative / Exception Flows:**
  * *AF-1 (Duplicate vote):* Backend prevents multiple votes from the same student on the same poll.
* **Postconditions:** Poll responses are recorded and displayed live to the lecturer.

---

### UC-07: Asynchronous AI Class Video & Transcript Summarizer
* **Primary Actor:** Lecturer | **Secondary Actor:** Google Gemini API
* **Preconditions:** An active session is open; lecturer has a class recording (`.mp4`) or transcript file (`.txt`).
* **Main Flow:**
  1. Lecturer selects the file in `#summary-file` and clicks **"צור סיכום"**.
  2. Frontend sends `POST /api/summarize`, receives a `job_id` from `job_store`, and displays an elapsed-seconds progress indicator.
  3. Background worker calls `AIService.summarize_content()` (extracting audio via `extract_audio()` for videos and querying `gemini-3.5-flash-lite`) to generate a structured Markdown summary.
  4. Once `pollJob` receives `status === "done"`, the browser automatically downloads `summary_<session_id>.md`.
* **Postconditions:** Lecturer receives a downloadable Markdown summary of the lecture.

---

### UC-08: GitHub Repository Similarity Comparison
* **Primary Actor:** Lecturer (and Student self-check) | **Secondary Actor:** GitHub REST API
* **Preconditions:** Student repository links have been imported into the `repositories` collection (`POST /api/repos/import`), and the lecturer has a target GitHub repository URL to evaluate.
* **Main Flow:**
  1. Lecturer enters a target GitHub repository URL (`https://github.com/user/repo`) into the comparison input field and clicks **"השווה למטלות אחרות"**.
  2. Frontend sends `GET /api/repos/compare?my_repo_url=<url>` (or `GET /api/student/compare-repo` for student self-check).
  3. `SmartClassFacade` delegates to `RepoComparisonService.compare()`, which uses `GitHubClient.fetch_code()` (authenticated via `GITHUB_TOKEN`) to retrieve the target repository's source files and computes a $k$-shingle fingerprint via `TokenShingleSimilarity.fingerprint()`.
  4. `RepoComparisonService` compares the target fingerprint against all stored repositories in `PocketBaseRepository` (using cached fingerprints when available) via `TokenShingleSimilarity.score()`.
  5. Frontend renders a summary table displaying maximum similarity percentage, number of compared repositories (`compared_count`), and a visual status badge (`⚠️ חשד לדמיון` or `✅ תקין`).
* **Alternative / Exception Flows:**
  * *EF-1 (Invalid GitHub URL):* `GitHubClient.parse_repo_url()` returns `None` and the backend returns a descriptive validation error.
  * *EF-2 (GitHub API Rate Limit):* If unauthenticated requests exceed 60/hr (`403`/`429`), `GitHubClient` raises `ExternalServiceError` advising configuration of `GITHUB_TOKEN`.
* **Postconditions:** Maximum similarity percentage, compared repository count, and plagiarism flag are displayed on the dashboard.