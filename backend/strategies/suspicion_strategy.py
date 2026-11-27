from interfaces.strategies import ISuspicionStrategy
from models.domain import SuspicionLevel, SuspicionReport

SMALL_GAP = 2            # פער קטן מזה נחשב רעש סביר
CLASS_LOW_RATIO = 0.15   # עד 15% חריגה בכיתה
CLASS_MEDIUM_RATIO = 0.35
STUDENT_MEDIUM_RATIO = 0.20  # מעל 20% פער בכיתה, סטודנט לא פעיל מקבל HIGH


class SmartRatioSuspicionStrategy(ISuspicionStrategy):
    """
    חישוב דרגות חשד:
    1. calculate: דרגת חשד לכיתה כולה, לפי הפער בין נרשמים לספירת ראשים מהתמונה.
    2. classify_student: דרגת חשד לסטודנט בודד, לפי פעילות (סקרים/שאלות) והפער הכיתתי.
    """

    def calculate(
        self,
        registered_count: int,
        ai_headcount: int,
        verified_active_count: int = 0,
    ) -> SuspicionReport:
        delta = registered_count - ai_headcount

        if delta <= 0:
            return SuspicionReport(
                ai_headcount=ai_headcount,
                registered_count=registered_count,
                verified_active_count=verified_active_count,
                delta=delta,
                excess_ratio=0.0,
                level=SuspicionLevel.NONE,
                explanation="תקין: מספר הנרשמים אינו עולה על מספר הראשים שנספרו בתמונה.",
            )

        baseline = max(ai_headcount, 1)
        excess_ratio = round(delta / baseline, 2)
        pct = int(excess_ratio * 100)

        if verified_active_count >= registered_count and excess_ratio <= CLASS_LOW_RATIO:
            level = SuspicionLevel.LOW
            explanation = (
                f"חשד נמוך: נרשמו {delta} יותר מהראשים בתמונה, אך כל הנרשמים פעילים "
                "(ייתכן שחלק מהסטודנטים יושבים מחוץ לטווח המצלמה)."
            )
        elif excess_ratio <= CLASS_LOW_RATIO or delta <= SMALL_GAP:
            level = SuspicionLevel.LOW
            explanation = f"חשד נמוך: פער קטן של {delta} סטודנטים ({pct}%)."
        elif excess_ratio <= CLASS_MEDIUM_RATIO:
            level = SuspicionLevel.MEDIUM
            explanation = (
                f"חשד בינוני: נרשמו {delta} סטודנטים יותר מהראשים שנספרו ({pct}% חריגה). "
                "מומלץ לבדוק את הסטודנטים הלא פעילים ברשימה."
            )
        else:
            level = SuspicionLevel.HIGH
            explanation = (
                f"חשד גבוה: נרשמו {registered_count} לעומת {ai_headcount} ראשים בתמונה "
                f"(חריגה של {delta} סטודנטים, {pct}%). ייתכן שהקוד הכיתתי הופץ מחוץ לכיתה."
            )

        return SuspicionReport(
            ai_headcount=ai_headcount,
            registered_count=registered_count,
            verified_active_count=verified_active_count,
            delta=delta,
            excess_ratio=excess_ratio,
            level=level,
            explanation=explanation,
        )

    def classify_student(self, is_active: bool, delta: int, ai_headcount: int) -> tuple[SuspicionLevel, str]:
        """
        דרגת חשד לסטודנט בודד.
        is_active: האם ענה על סקר או שלח שאלה במהלך השיעור.
        delta: הפער הכיתתי (נרשמים פחות ראשים בתמונה).
        """
        if is_active:
            return SuspicionLevel.NONE, "פעיל במהלך השיעור (ענה על סקר או שלח שאלה)."

        if delta <= SMALL_GAP:
            return (
                SuspicionLevel.LOW,
                "לא פעיל במהלך השיעור, אך אין פער משמעותי בין הנרשמים לנצפים.",
            )

        ratio = delta / max(ai_headcount, 1)
        pct = int(ratio * 100)

        if ratio <= STUDENT_MEDIUM_RATIO:
            return (
                SuspicionLevel.MEDIUM,
                f"לא פעיל במהלך השיעור, והכיתה כולה עם פער של {pct}% בין נרשמים לנצפים. מומלץ לבדוק.",
            )

        return (
            SuspicionLevel.HIGH,
            f"לא פעיל במהלך השיעור, והכיתה עם פער גדול של {pct}% בין נרשמים לנצפים. מומלץ לבדוק.",
        )