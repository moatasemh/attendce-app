import os
import traceback
import time
import requests
import csv
import io
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from factory import SystemFactory
from services.ai_service import AIService
from models.exceptions import (
    DomainError, ExternalServiceError, InvalidCredentialsError, ResourceNotFoundError, SessionClosedError,
)

print("==================================================")
print("🚀 !!! NEW MAIN.PY IS RUNNING !!! 🚀")
print("==================================================")

def bootstrap_database():
    pb_url = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
    email = os.getenv("PB_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("PB_ADMIN_PASSWORD", "1234567890")

    print("⏳ ממתין ל-PocketBase...")
    for _ in range(10):
        try:
            requests.get(f"{pb_url}/api/health", timeout=2)
            break
        except requests.exceptions.RequestException:
            time.sleep(2)

    print("🔐 מנסה להתחבר כמנהל...")
    auth_res = requests.post(f"{pb_url}/api/collections/_superusers/auth-with-password", json={"identity": email, "password": password})
    if auth_res.status_code != 200:
        print("⚠️ לא ניתן להתחבר לאדמין. ממשיך בכל זאת...")
        return

    token = auth_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    collections = {
        "students": [
            {"name": "name", "type": "text", "required": True},
            {"name": "email", "type": "text", "required": False},
            {"name": "group", "type": "text", "required": False}
        ],
        "sessions": [
            {"name": "title", "type": "text", "required": True},
            {"name": "class_code", "type": "text", "required": True},
            {"name": "status", "type": "text", "required": True},
            {"name": "ai_headcount", "type": "number", "required": False},
            {"name": "final_headcount", "type": "number", "required": False}
        ],
        "attendance": [
            {"name": "session_id", "type": "text", "required": True},
            {"name": "student_id", "type": "text", "required": True},
            {"name": "student_name", "type": "text", "required": True},
            {"name": "status", "type": "text", "required": True},
            {"name": "verification_level", "type": "text", "required": True}
        ],
        "messages": [
            {"name": "session_id", "type": "text", "required": True},
            {"name": "student_id", "type": "text", "required": True},
            {"name": "student_name", "type": "text", "required": True},
            {"name": "text", "type": "text", "required": True},
            {"name": "status", "type": "text", "required": False}
        ],
        "polls": [
            {"name": "session_id", "type": "text", "required": True},
            {"name": "question", "type": "text", "required": True},
            {"name": "options", "type": "json", "required": True},
            {"name": "status", "type": "text", "required": True}
        ],
        "poll_votes": [
            {"name": "poll_id", "type": "text", "required": True},
            {"name": "student_id", "type": "text", "required": True},
            {"name": "student_name", "type": "text", "required": False}, # הוספנו שם סטודנט
            {"name": "answer", "type": "text", "required": True}
        ],
        "summaries": [
            {"name": "session_id", "type": "text", "required": True},
            {"name": "content", "type": "text", "required": True}
        ],
        "homework_reviews": [
            {"name": "student_name", "type": "text", "required": True},
            {"name": "repo_url", "type": "text", "required": True},
            {"name": "feedback", "type": "text", "required": True}
        ],
        "repos": [
            {"name": "student_name", "type": "text", "required": False},
            {"name": "repo_url", "type": "text", "required": True}
        ],
    }

    for col_name, schema in collections.items():
        res = requests.get(f"{pb_url}/api/collections/{col_name}", headers=headers)
        if res.status_code == 404:
            print(f"🔨 יוצר טבלה חדשה: {col_name}...")
            payload = {
                "name": col_name,
                "type": "base",
                "fields": schema,
                "listRule": "", "viewRule": "", "createRule": "", "updateRule": "", "deleteRule": ""
            }
            create_res = requests.post(f"{pb_url}/api/collections", headers=headers, json=payload)
            if create_res.status_code == 200:
                print(f"✅ טבלה {col_name} נוצרה.")
            else:
                print(f"❌ שגיאה ביצירת {col_name}: {create_res.text}")
        else:
            print(f"✅ טבלה {col_name} כבר קיימת.")

bootstrap_database()

app = FastAPI(title="Smart Class Teaching Tool API")
facade = SystemFactory.bootstrap()
ai_service = AIService()

@app.post("/api/auth/login")
def lecturer_login(email: str = Form(...), password: str = Form(...)):
    pb_url = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
    auth_res = requests.post(f"{pb_url}/api/collections/_superusers/auth-with-password", json={"identity": email, "password": password})
    if auth_res.status_code == 200:
        return {"token": auth_res.json()["token"]}
    raise InvalidCredentialsError("פרטי התחברות שגויים.")

@app.post("/api/auth/signup")
def lecturer_signup(email: str = Form(...), password: str = Form(...), old_password: str = Form("")):
    pb_url = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
    auth_res = requests.post(f"{pb_url}/api/collections/_superusers/auth-with-password", json={"identity": email, "password": password})
    if auth_res.status_code == 200:
        return {"token": auth_res.json()["token"], "status": "logged_in"}
    create_res = requests.post(f"{pb_url}/api/collections/_superusers/records", json={"email": email, "password": password, "passwordConfirm": password})
    if create_res.status_code == 200:
        auth_res = requests.post(f"{pb_url}/api/collections/_superusers/auth-with-password", json={"identity": email, "password": password})
        return {"token": auth_res.json()["token"], "status": "created"}
    raise InvalidCredentialsError("המשתמש קיים. יש להזין סיסמה ישנה.") # פישוט

@app.get("/")
def serve_login_page(): return FileResponse("/app/frontend/login.html")

@app.get("/student")
def serve_student_portal(): return FileResponse("/app/frontend/index.html")

@app.get("/lecturer")
def serve_lecturer_dashboard(): return FileResponse("/app/frontend/lecturer.html")

@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    traceback.print_exc()
    status_code = 400
    if isinstance(exc, InvalidCredentialsError): status_code = 401
    elif isinstance(exc, ResourceNotFoundError): status_code = 404
    elif isinstance(exc, ExternalServiceError): status_code = 502
    elif isinstance(exc, SessionClosedError): status_code = 400
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})

@app.get("/api/health")
def health_check(): return {"status": "ok"}

@app.post("/api/students/seed")
def import_students(): return facade.import_course_students()

@app.get("/api/students/names")
def list_students(): return facade.get_student_directory()

@app.get("/api/sessions/active")
def get_active_session(): return {"session": facade.get_current_session()}

@app.post("/api/sessions/open")
def open_session(title: str = Form("שיעור OOP")): return facade.start_attendance_session(title)

@app.post("/api/attendance/checkin")
def check_in(student_name: str = Form(...), class_code: str = Form(...)): return facade.register_student_attendance(student_name, class_code)

@app.post("/api/sessions/{session_id}/audit")
async def headcount_audit(session_id: str, photo: UploadFile = File(...)):
    image_bytes = await photo.read()
    return facade.run_attendance_audit(session_id, image_bytes, photo.content_type or "image/jpeg")

@app.post("/api/sessions/{session_id}/override/{student_id}")
def override_student(session_id: str, student_id: str): return facade.override_student_attendance(session_id, student_id)

@app.post("/api/sessions/{session_id}/close")
def close_session(session_id: str, final_headcount: int = Form(...)): return facade.finalize_attendance_session(session_id, final_headcount)

@app.get("/api/sessions/{session_id}/export")
def export_attendance(session_id: str):
    content, media_type, filename = facade.generate_attendance_report(session_id)
    return StreamingResponse(iter([content]), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/api/public-url")
def get_public_url(): return {"url": facade.get_public_tunnel_url()}

@app.post("/api/messages")
def post_message(session_id: str = Form(...), student_id: str = Form(...), student_name: str = Form(...), text: str = Form(...)):
    return facade.send_student_message(session_id, student_id, student_name, text)

@app.post("/api/polls")
def create_poll(session_id: str = Form(...), question: str = Form(...), options: str = Form(...)):
    opts = [o.strip() for o in options.split(",")]
    return facade.create_poll(session_id, question, opts)

@app.get("/api/polls/active")
def get_poll(session_id: str): return {"poll": facade.get_active_poll(session_id)}

@app.post("/api/polls/vote")
def vote(poll_id: str = Form(...), student_id: str = Form(...), session_id: str = Form(...), answer: str = Form(...), student_name: str = Form(...)):
    return facade.vote_in_poll(poll_id, student_id, session_id, answer, student_name)

# נתיב חדש לתוצאות סקר
@app.get("/api/polls/{poll_id}/results")
def get_poll_results(poll_id: str): return {"results": facade.get_poll_results(poll_id)}

@app.post("/api/summarize")
async def summarize_lecture(session_id: str = Form(...), text: str = Form(""), file: UploadFile = File(None)):
    if file:
        content = await file.read()
        summary = ai_service.summarize_content("", is_file=True, file_bytes=content, mime_type=file.content_type)
    else:
        summary = ai_service.summarize_content(text)
    facade._attendance.repo.create_record("summaries", {"session_id": session_id, "content": summary})
    return {"summary": summary}

@app.post("/api/review-homework")
async def review_homework(file: UploadFile = File(...)):
    content = await file.read()
    csv_text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(csv_text))
    results = []
    for row in reader:
        name = row.get("Email Address", "Unknown")
        repo = row.get("Link to your Ex1 repository (@ Github)", "")
        feedback = ai_service.review_homework(repo)
        results.append({"name": name, "repo": repo, "feedback": feedback})
    return {"reviews": results}

# ===== פיצ'ר 5: השוואת מטלות =====
@app.post("/api/repos/import")
async def import_repos(file: UploadFile = File(...)):
    content = await file.read()
    return facade.import_repos_csv(content.decode("utf-8-sig"))

@app.get("/api/repos/compare")
def compare_repos(my_repo_url: str):
    return facade.compare_my_repo(my_repo_url)

@app.get("/api/repos/status")
def repos_status():
    return facade.repos_status()

@app.get("/api/student/repos/compare")
def student_compare_repo(my_repo_url: str):
    return facade.compare_for_student(my_repo_url)