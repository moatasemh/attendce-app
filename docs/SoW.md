# Statement of Work (SoW) — Smart Classroom Web-Based Teaching Tool

**Project Name:** Smart Classroom — End-to-End Web-Based Teaching Tool  
**Course:** Introduction to Software Engineering (OOP / OOD) — Ex2  
**Institution:** Ariel University  
**Prepared For:** Course Lecturer & Teaching Staff (Stakeholders)  
**Version:** 1.0  

---

## 1. Purpose & Executive Summary

This Statement of Work (SoW) defines the scope, deliverables, milestones, constraints, and acceptance criteria for the **Smart Classroom** system. The objective of the project is to design and implement a **KISS (Keep It Simple, Stupid)**, mobile-first, LLM-ready web application that streamlines live classroom management without requiring student installations, institutional SSO logins, or complex external LMS integrations.

The system bridges real-time classroom engagement (QR-based attendance, live student Q&A, and instant polls) with AI-assisted lecturer tools (automated classroom photo headcounting, suspicion auditing, lecture recording summarization, and GitHub homework similarity analysis).

---

## 2. Scope of Work (In-Scope)

### 2.1 Software Engineering & Design Deliverables
The engineering team will produce and maintain the following technical artifacts in the project's GitHub repository:
1. **Repository & Project Overview (`README.md`):** Problem definition, scope, architecture overview, setup instructions, and final conclusions.
2. **Technical Tools Report (`docs/Tools_Report.md`):** Evaluation of candidate technologies backed by real-life empirical benchmarks and load testing.
3. **Statement of Work (`docs/SoW.md`):** Formal definition of scope, exclusions, schedule, and acceptance criteria (this document).
4. **Software Requirements Specification (`docs/SRS.md`):** Detailed functional and non-functional requirements.
5. **Use Cases & Client Stories (`docs/Use_Cases.md`):** End-to-end user flows for lecturers and students.
6. **Software Components Definition (`docs/Components.md`):** Modular breakdown of backend, frontend, database, and infrastructure layers.
7. **Low-Level UML Diagrams (`docs/Diagrams.md`):** Detailed Class Diagrams and Sequence Diagrams illustrating OOP patterns and runtime interactions.
8. **Testing Strategy & Automated Suite (`docs/Testing_Strategy.md` & `tests/`):** Class-mapped testing plan and executable `pytest` unit/integration tests.

### 2.2 Web Application Functional Deliverables
1. **Hybrid Attendance & Suspicion Auditing (Primary Module):**
   * Dynamic QR code generation on the lecturer projector view pointing to a public mobile web URL.
   * Zero-friction student check-in using name selection and a 2-digit session code.
   * Automated classroom headcount from uploaded photographs via multimodal AI Vision (`GeminiVisionStrategy`).
   * Suspicion level calculation (`NONE`, `LOW`, `MEDIUM`, `HIGH`) at both class and individual student levels based on headcount delta and live participation (`SmartRatioSuspicionStrategy`).
   * Real-time attendance dashboard with manual override and one-click Excel spreadsheet export (`ExcelExportStrategy`).
2. **Real-Time Student Q&A & Suggestions:**
   * Live submission of questions/comments from student smartphones to the lecturer's console, automatically upgrading the student's verification status to `VERIFIED_ACTIVE`.
3. **On-the-Spot KISS Polls:**
   * Instant creation of multiple-choice polls by the lecturer with live mobile voting and real-time result aggregation.
4. **AI Lecture Summarizer:**
   * Asynchronous background summarization of recorded class videos (`.mp4`) or transcripts (`.txt`) into downloadable Markdown notes (`AIService`).
5. **GitHub Repository Similarity Comparison:**
   * Pairwise structural $k$-shingle code comparison across student GitHub repositories (`RepoComparisonService`, `GitHubClient`, `TokenShingleSimilarity`).

### 2.3 Deployment & Demonstration Deliverables
* Containerized multi-service deployment (`docker-compose.yml`) runnable via a single command (`docker compose up -d`).
* Live 5-minute in-class demonstration showing concurrent student check-in, live Q&A, polling, AI vision headcount, and repository comparison.

---

## 3. Out-of-Scope (Exclusions)

In strict alignment with the assignment guidelines, the following items are explicitly excluded from this project:
* **Institutional Integrations:** No integration with Moodle, Zoom APIs, or Ariel University's personal portal (*מידע אישי*).
* **Native Mobile Applications:** No native iOS (`.ipa`) or Android (`.apk`) app store builds; student access is delivered purely via a responsive mobile web interface.
* **Biometric / Facial Recognition:** Classroom photo analysis performs anonymous headcounting only; it does not identify individual student faces.
* **Production Cloud Hosting & Billing:** The system runs locally on the lecturer's machine via Docker and exposes public student access dynamically via an ephemeral HTTPS tunnel.

---

## 4. Work Breakdown & Project Milestones

| Phase | Milestone | Key Activities & Outputs | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Problem Definition & Tooling Validation** | Initialize GitHub repository, evaluate stack options, and benchmark PocketBase, FastAPI, Gemini 3.5, Caddy, and Tunneling in real-life tests. | Completed |
| **Phase 2** | **Requirements & System Architecture** | Author `SoW.md`, `SRS.md`, `Use_Cases.md`, `Components.md`, and UML `Diagrams.md` applying SOLID principles and OOP patterns (`SmartClassFacade`, `SystemFactory`, Strategy, Repository). | Completed |
| **Phase 3** | **Core System Implementation** | Compose containerized backend (`FastAPI`), realtime DB (`PocketBase`), reverse proxy (`Caddy`), public tunnel, and KISS frontend (`lecturer.html`, `index.html`). | Completed |
| **Phase 4** | **Testing, Load Simulation & Optimization** | Execute 50-student concurrent load tests, implement background job queuing (`job_store.py`), and write class-level `pytest` unit/integration tests. | Completed |
| **Phase 5** | **Live Classroom Demo & Final Delivery** | Conduct live 5-minute class demo, finalize results/conclusions in `README.md`, and submit repository link. | Completed |

---

## 5. Assumptions, Dependencies & Constraints

* **Network Connectivity:** The lecturer's laptop has active internet access during the demo to establish the outbound HTTPS tunnel (`cloudflared` or `localhost.run`) so students can connect via cellular data (4G/5G), bypassing university Wi-Fi client isolation.
* **External API Credentials:** Valid `GEMINI_API_KEY` and `GITHUB_TOKEN` environment variables are configured in `.env` prior to runtime.
* **KISS Usability Constraint:** Any student with a standard smartphone browser must be able to scan the QR code and mark attendance within 15 seconds without typing a password or creating an account.

---

## 6. Acceptance Criteria (Definition of Done)

The project will be considered complete and ready for grading when all of the following conditions are met:
1. **Repository Completeness:** All 12 items listed in the assignment To-Do list are present, well-structured, and documented in the GitHub repository.
2. **End-to-End Functionality:** All 5 core features execute reliably without unhandled server errors (`500`) or UI freezes.
3. **Concurrency & Latency:** The system absorbs 50 simultaneous student requests in under 3 seconds without SQLite locking errors, and AI Vision/Summary jobs return results asynchronously within ~1–4 seconds.
4. **Automated Test Verification:** All unit and integration tests in `tests/` pass (`pytest -v`) and cover the core domain, service, facade, and strategy classes.
5. **Live Demo Execution:** Successful live demonstration in class verifying real-time interaction between student smartphones and the lecturer dashboard.