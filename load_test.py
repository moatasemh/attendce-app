import requests
import time
from concurrent.futures import ThreadPoolExecutor

# הכתובת של המערכת (אם אתה מריץ מתוך הקונטיינר, שנה ל- "http://proxy")
BASE_URL = "http://localhost:8080"


def main():
    print("🚀 מתחיל בדיקת עומס - מדמה 50 סטודנטים...")

    # 1. שליפת הסשן הפעיל
    try:
        res = requests.get(f"{BASE_URL}/api/sessions/active")
        session_data = res.json().get("session")
        if not session_data or session_data.get("status") != "OPEN":
            print("❌ שגיאה: אין סשן פתוח. נא לפתוח רישום נוכחות בדשבורד המרצה קודם.")
            return

        session_id = session_data["id"]
        class_code = session_data["class_code"]
        print(f"✅ נמצא סשן פעיל. קוד כיתתי: {class_code}, ID: {session_id}")

    except Exception as e:
        print(f"❌ שגיאה בשליפת סשן: {e}")
        return

    # 2. שליפת רשימת הסטודנטים
    try:
        res = requests.get(f"{BASE_URL}/api/students/names")
        students = res.json()
        print(f"✅ נטענו {len(students)} סטודנטים מהמערכת.")
    except Exception as e:
        print(f"❌ שגיאה בשליפת סטודנטים: {e}")
        return

    if not students:
        print("❌ רשימת הסטודנטים ריקה. נסה לרענן את דף המרצה כדי לטעון אותם.")
        return

    # 3. הכנת 50 בקשות רישום
    students_to_register = students[:50]

    def register_student(student):
        try:
            payload = {
                "student_name": student["name"],
                "class_code": class_code
            }
            # שליחת בקשת POST
            res = requests.post(f"{BASE_URL}/api/attendance/checkin", data=payload, timeout=15)
            if res.status_code == 200:
                return True
            else:
                print(f"⚠️ נכשל ברישום {student['name']}: {res.text}")
                return False
        except Exception as e:
            print(f"⚠️ שגיאת רשת ברישום {student['name']}: {e}")
            return False

    print(f"🔥 שולח {len(students_to_register)} בקשות רישום במקביל (בו-זמנית)...")

    start_time = time.time()

    # שימוש ב-ThreadPoolExecutor כדי לשלוח 50 בקשות בו זמנית
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(register_student, students_to_register))

    end_time = time.time()

    success_count = sum(results)
    print(f"\n✅ הושלם! {success_count} מתוך {len(students_to_register)} נרשמו בהצלחה.")
    print(f"⏱️ זמן כולל לספיגת העומס: {end_time - start_time:.2f} שניות")
    print("👉 עכשיו תסתכל על דשבורד המרצה - המונה אמור לזנק!")


if __name__ == "__main__":
    main()