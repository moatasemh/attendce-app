class DomainError(Exception):
    """שגיאת בסיס בשכבת הלוגיקה העסקית (ללא תלות ב-HTTP)."""


class SessionClosedError(DomainError):
    """נזרקת כאשר אין סשן נוכחות פתוח לרישום."""


class InvalidCredentialsError(DomainError):
    """נזרקת כאשר קוד כיתתי, שם סטודנט או PIN שגויים."""


class ResourceNotFoundError(DomainError):
    """נזרקת כאשר ישות מבוקשת (סטודנט, סשן או קובץ) לא נמצאה."""


class ExternalServiceError(DomainError):
    """נזרקת בעת כשל בתקשורת מול שירות חיצוני (Gemini / PocketBase)."""