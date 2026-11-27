import random
import time
from concurrent.futures import ThreadPoolExecutor
import requests

BASE_URL = "http://localhost:8080"

SAMPLE_QUESTIONS = [
    "אפשר לחזור שוב על ההבדל בין ירושה להרכבה?",
    "האם התרגיל הבא יכלול גם בדיקות יחידה (Unit Tests)?",
    "לא הבנתי למה השתמשנו כאן ב-Interface ולא ב-Abstract Class.",
    "אפשר לראות דוגמה נוספת ל-Strategy Pattern?",
    "מתי מועד ההגשה של מטלה 2?",
    "האם הקוד מהשיעור יעלה למודל בסוף ההרצאה?",
    "איך מטפלים בחריגות (Exceptions) בשכבת ה-Service?",
    "אפשר להגדיל קצת את הפונט ב-IDE?",
]


def main():
  print("🚀 מתחיל בדיקת עומס לפיצ'ר 2 — מדמה 50 סטודנטים שולחים שאלות...")

  # 1. שליפת הסשן הפעיל
  try:
    res = requests.get(f"{BASE_URL}/api/sessions/active", timeout=10)
    session_data = res.json().get("session")
    if not session_data or session_data.get("status") != "OPEN":
      print("❌ שגיאה: אין סשן פתוח. פתח רישום נוכחות בדשבורד המרצה קודם.")
      return
    session_id = session_data["id"]
    print(f"✅ נמצא סשן פעיל (ID: {session_id})")
  except Exception as e:
    print(f"❌ שגיאה בשליפת סשן: {e}")
    return

  # 2. שליפת רשימת הסטודנטים (נדרש student_id + student_name)
  try:
    res = requests.get(f"{BASE_URL}/api/students/names", timeout=10)
    students = res.json()
    print(f"✅ נטענו {len(students)} סטודנטים מהמערכת.")
  except Exception as e:
    print(f"❌ שגיאה בשליפת סטודנטים: {e}")
    return

  if not students:
    print("❌ רשימת הסטודנטים ריקה.")
    return

  students_to_send = students[:50]

  def send_question(idx_student):
    idx, student = idx_student
    payload = {
        "session_id": session_id,
        "student_id": student["id"],
        "student_name": student["name"],
        "text": f"{random.choice(SAMPLE_QUESTIONS)} (#{idx + 1})",
    }
    try:
      res = requests.post(f"{BASE_URL}/api/messages", data=payload, timeout=15)
      if res.status_code == 200:
        return True
      print(f"⚠️ נכשל בשליחה עבור {student['name']}: {res.text}")
      return False
    except Exception as e:
      print(f"⚠️ שגיאת רשת עבור {student['name']}: {e}")
      return False

  print(f"🔥 שולח {len(students_to_send)} שאלות במקביל (בו-זמנית)...")
  start_time = time.time()

  with ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(send_question, enumerate(students_to_send)))

  elapsed = time.time() - start_time
  success_count = sum(results)

  print(
      f"\n✅ הושלם! {success_count} מתוך {len(students_to_send)} שאלות נשלחו"
      " בהצלחה."
  )
  print(f"⏱️ זמן כולל לספיגת העומס: {elapsed:.2f} שניות")
  print("👉 בדוק בדשבורד המרצה:")
  print("   1. ה-Console השחור התמלא ב-50 שאלות וגלל אוטומטית למטה.")
  print(
      "   2. רמת האימות של הסטודנטים בטבלה שודרגה אוטומטית ל-VERIFIED_ACTIVE."
  )


if __name__ == "__main__":
  main()