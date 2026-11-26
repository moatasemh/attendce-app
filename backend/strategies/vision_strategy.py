import re
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from interfaces.strategies import IHeadcountStrategy
from models.exceptions import ExternalServiceError

RETRYABLE_CODES = {429, 503}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [2, 5]  # המתנה לפני הניסיון השני והשלישי


class GeminiVisionStrategy(IHeadcountStrategy):
    """ספירת נוכחים מתמונת כיתה באמצעות מודל Gemini Vision."""

    def __init__(self, api_key: str | None, model_name: str = "gemini-3.8-flash"):
        self.model_name = model_name
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=60_000),  # מילישניות (60 שניות לקריאה)
        ) if api_key else None
    def _generate_with_retry(self, contents):
        last_exc = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                )
            except genai_errors.APIError as exc:
                last_exc = exc
                code = getattr(exc, "code", None)
                print(f"⚠️ Gemini {model} ניסיון {attempt + 1}/{self.max_attempts} נכשל: {code}")
                # שגיאה שאינה זמנית (למשל 404 על שם מודל) לא תיפתר עם ניסיון חוזר
                if code not in RETRYABLE_CODES or attempt == MAX_ATTEMPTS - 1:
                    break
                time.sleep(BACKOFF_SECONDS[attempt])
            except Exception as exc:
                last_exc = exc
                break
        raise ExternalServiceError(f"שגיאה בקריאה ל-Gemini Vision: {last_exc}") from last_exc

    def count_heads(self, image_bytes: bytes, mime_type: str) -> int:
        if not self.client:
            raise ExternalServiceError("מפתח GEMINI_API_KEY לא הוגדר בקובץ .env בשרת.")

        prompt = (
            "Count the exact number of people/students visible in this classroom photo. "
            "Reply with ONLY a single integer number and nothing else."
        )
        response = self._generate_with_retry([
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ])

        match = re.search(r"\d+", response.text or "")
        if not match:
            raise ExternalServiceError(f"פלט לא צפוי מ-Gemini Vision: {response.text}")
        return int(match.group(0))


class MockHeadcountStrategy(IHeadcountStrategy):
    """אסטרטגיית דמה לבדיקות יחידה (Unit Tests) ללא תלות ברשת."""

    def __init__(self, fixed_count: int = 15):
        self.fixed_count = fixed_count

    def count_heads(self, image_bytes: bytes, mime_type: str) -> int:
        return self.fixed_count