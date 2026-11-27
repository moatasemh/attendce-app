# Smart Classroom — Web-Based Teaching Tool

**Course:** Introduction to Software Engineering (OOP / OOD) — Ariel University  
**Assignment:** Ex2 — Vibe Coding & Deep Designing: Web-Based Teaching Tool  

---

## 1. Problem Statement & Motivation

Existing digital classroom tools (video conferencing platforms, static LMS portals, and manual roll-call sheets) fail to support real-time, low-friction classroom interaction. Taking attendance wastes valuable lecture time, passive students rarely ask questions aloud, and lecturers lack immediate, LLM-ready tools to verify physical attendance, run instant comprehension checks, summarize recorded lectures, or detect similarity across code submissions.

**Smart Classroom** solves this by providing a **KISS (Keep It Simple, Stupid)**, mobile-first web application that requires zero student installation or registration, paired with an AI-augmented lecturer dashboard.

---

## 2. Project Scope & Core Features

### Implemented Features
1. **Hybrid Smart Attendance & Suspicion Auditing (Primary Feature):**
   * **Zero-Friction Student Check-In:** Students scan a dynamic QR code displayed on the projector, select their name, and enter a 2-digit session code (`POST /api/attendance/checkin`).
   * **AI Vision Headcount:** The lecturer uploads a classroom photo; Gemini Vision counts visible students automatically.
   * **Automated Suspicion Scoring:** Compares registered check-ins against the AI headcount and individual student engagement (polls answered, questions asked) to assign suspicion levels (`NONE`, `LOW`, `MEDIUM`, `HIGH`) both class-wide and per student.
   * **Live Dashboard & Spreadsheet Export:** Real-time attendance table powered by WebSockets with manual override and one-click CSV/Excel export.
2. **Real-Time Student Q&A & Suggestions:**
   * Students submit live questions or feedback from their phones, appearing immediately in the lecturer's live console and automatically upgrading their verification status to `VERIFIED_ACTIVE`.
3. **On-the-Spot KISS Polls:**
   * Lecturers create quick multiple-choice polls during class; students vote on their phones and results stream live to the lecturer's screen.
4. **AI Class Video & Transcript Summarizer:**
   * Asynchronous background processing of class recordings (`.mp4`) or transcripts (`.txt`) using Google Gemini (`gemini-3.5-flash-lite`) to generate structured Markdown lecture summaries.
5. **LLM Homework Review & GitHub Repository Comparison:**
   * Batch homework review from CSV submissions and automated pairwise code similarity analysis against a repository dataset via the GitHub API.

### Out of Scope (Per Assignment Guidelines)
* Direct integration with external institutional systems (Moodle, Zoom, or מידע אישי).
* Native iOS/Android mobile app stores (delivered purely as a responsive mobile web app).

---

## 3. System Architecture & Design Patterns

The system runs as a containerized microservices stack orchestrated with **Docker Compose**:

* **Reverse Proxy (`Caddy`):** Single entry point on port `8080`, routing `/api/*` to FastAPI, `/pb/*` to PocketBase, and `/` to static frontend assets.
* **Backend (`FastAPI` — Python 3.12):** Asynchronous REST API, background job execution (`job_store`), and automatic database schema migration on startup.
* **Database & Realtime Engine (`PocketBase`):** Embedded SQLite database with built-in authentication and real-time WebSocket subscriptions for live UI updates.
* **Public Connectivity (`Cloudflare Tunnel`):** Exposes the local server over HTTPS (`trycloudflare.com`) so students can connect immediately over cellular data (4G/5G) without university Wi-Fi isolation issues.

### Applied OOP & SOLID Design Patterns
* **Facade Pattern (`backend/facade.py`):** `SmartClassFacade` exposes a clean, unified interface to the HTTP layer, hiding the complexity of repositories, AI services, and strategy orchestration.
* **Factory Pattern (`backend/factory.py`):** `SystemFactory` centralizes object creation and dependency wiring across the application via `bootstrap()`.
* **Strategy Pattern (`backend/strategies/` & `backend/interfaces/strategies.py`):** Encapsulates interchangeable algorithms behind abstract interfaces (`IHeadcountStrategy`, `ISuspicionStrategy`, `IExportStrategy`, `ISimilarityStrategy`).
* **Repository Pattern (`backend/repositories/`):** Decouples business logic from PocketBase persistence details via `IDataRepository` (`backend/interfaces/repository.py`).

---

## 4. Project Structure & Backend Python Modules

```text
oop2/
├── backend/
│   ├── interfaces/                 # Abstract base classes & contracts (SOLID DIP)
│   │   ├── repository.py           # IDataRepository persistence interface
│   │   └── strategies.py           # IHeadcountStrategy, ISuspicionStrategy, IExportStrategy
│   ├── models/                     # Core domain entities & custom exceptions
│   │   ├── domain.py               # SuspicionLevel, Student, ClassSession, AttendanceRecord, SuspicionReport
│   │   └── exceptions.py           # DomainError hierarchy
│   ├── repositories/               # Data access implementations
│   │   └── pocketbase_repo.py      # PocketBaseRepository REST API persistence
│   ├── services/                   # Core business logic & external integrations
│   │   ├── attendance_service.py   # AttendanceService & AuditResult
│   │   ├── ai_service.py           # AIService (Gemini video summary & homework review)
│   │   ├── repo_comparison_service.py # RepoComparisonService (CSV ingestion & similarity)
│   │   ├── github_client.py        # GitHubClient (authenticated GitHub API wrapper)
│   │   └── job_store.py            # Non-blocking background worker queue
│   ├── strategies/                 # Concrete Strategy Pattern implementations
│   │   ├── vision_strategy.py      # GeminiVisionStrategy & MockHeadcountStrategy
│   │   ├── suspicion_strategy.py   # SmartRatioSuspicionStrategy
│   │   ├── export_strategy.py      # ExcelExportStrategy
│   │   └── similarity_strategy.py  # ISimilarityStrategy & TokenShingleSimilarity
│   ├── facade.py                   # SmartClassFacade (unified backend entry point)
│   ├── factory.py                  # SystemFactory (dependency injection & bootstrap)
│   ├── main.py                     # FastAPI routes, startup auto-migration & static serving
│   ├── Dockerfile                  # Backend container image definition
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── login.html                  # Lecturer authentication page
│   ├── lecturer.html               # Lecturer live control dashboard & projector QR view
│   └── index.html                  # Student KISS mobile web interface (/student)
├── demo_assets/
│   └── students.csv                # Class roster seeded automatically into PocketBase
├── docs/                           # Software engineering deliverables (To-Do items 3–9)
│   ├── Tools_Report.md             # Technical tools evaluation & real-life benchmarks
│   ├── SoW.md                      # Statement of Work
│   ├── SRS.md                      # Software Requirements Specification
│   ├── Use_Cases.md                # Client stories & main use cases
│   ├── Components.md               # Software component definitions
│   ├── Diagrams.md                 # Low-level UML Class & Sequence diagrams
│   └── Testing_Strategy.md         # Testing strategy mapped to system classes
├── tests/                          # Automated unit & integration test suite (pytest)
├── Caddyfile                       # Reverse proxy routing rules
├── docker-compose.yml              # Multi-container orchestration
└── README.md                       # Project overview, setup & conclusions
```

### `backend/requirements.txt`
```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
google-genai==2.9.0
requests==2.32.3
python-dotenv==1.0.1
python-multipart==0.0.20
Pillow==10.4.0
imageio-ffmpeg==0.5.1
openpyxl==3.1.2
pytest==8.0.0
pytest-mock==3.12.0
httpx>=0.28.1
```

---

## 5. Engineering Documentation (`docs/`)

All required software engineering artifacts are maintained under the `docs/` directory:

1. **Technical Tools Report:** `docs/Tools_Report.md`
2. **Statement of Work (SoW):** `docs/SoW.md`
3. **Software Requirements Specification (SRS):** `docs/SRS.md`
4. **Main Use Cases (Client Stories):** `docs/Use_Cases.md`
5. **Software Components:** `docs/Components.md`
6. **Low-Level Class & Sequence Diagrams:** `docs/Diagrams.md`
7. **Testing Strategy:** `docs/Testing_Strategy.md`

---

## 6. Setup & Running the Application

### Prerequisites
* **Docker Desktop** (with Docker Compose v2)
* **Google Gemini API Key** (for Vision headcount, lecture summary, and homework review)
* **GitHub Personal Access Token** (optional, increases GitHub API limit from 60 to 5,000 req/hr)

### 1. Environment Configuration
Create a `.env` file in the root directory (`oop2/.env`):
```env
PB_ADMIN_EMAIL=admin@smartclass.local
PB_ADMIN_PASSWORD=ChangeMe123!
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_VISION_MODEL=gemini-3.5-flash-lite
GEMINI_SUMMARY_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-3.5-flash
GITHUB_TOKEN=your_github_token_here
```

### 2. Start the System
```bash
docker compose up -d
```

### 3. Access Endpoints
* **Lecturer Login:** `http://localhost:8080/`
* **Lecturer Dashboard:** `http://localhost:8080/lecturer`
* **Student Mobile View (Local):** `http://localhost:8080/student` (or scan the live QR code displayed on the lecturer dashboard for public mobile access)

### 4. Running Automated Tests
```bash
docker exec -it class_python_backend pytest /app/tests -v
```

---

## 7. Results & Conclusions

* **Concurrency & Live Demo Readiness:** Load testing with 50 concurrent simulated students (`ThreadPoolExecutor`) confirmed that simultaneous check-ins (`POST /api/attendance/checkin`) and live question submissions (`POST /api/messages`) complete within ~1–2 seconds without SQLite locking errors, updating the lecturer dashboard in real time via WebSockets.
* **AI Performance & Latency:** Offloading Gemini Vision headcounts and video summarization to an asynchronous background job store (`job_store.py`) eliminated HTTP timeouts and delivered headcount audits in ~1–3 seconds.
* **Architecture Takeaway:** Combining a strict OOP backend (`SmartClassFacade`, `SystemFactory`, Strategy & Repository patterns) with lightweight KISS frontend templates enabled rapid iteration ("vibe coding" + structured engineering) while keeping every core component isolated and unit-testable.