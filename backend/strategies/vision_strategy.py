import hashlib
import io
import os
import re
import time
from PIL import Image
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from interfaces.strategies import IHeadcountStrategy
from models.exceptions import ExternalServiceError

RETRYABLE_CODES = {429, 503, 504}
MAX_SIDE = 1024
JPEG_QUALITY = 75
CALL_TIMEOUT_MS = 60_000


def prepare_image(image_bytes: bytes) -> tuple[bytes, str]:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        print(f"🖼️ התמונה הוקטנה ל: {len(out.getvalue()) / 1024:.1f} KB")
        return out.getvalue(), "image/jpeg"
    except Exception as exc:
        print(f"⚠️ הקטנת התמונה נכשלה, שולח מקור: {exc}")
        return image_bytes, "image/jpeg"


class GeminiVisionStrategy(IHeadcountStrategy):
    def __init__(self, api_key: str | None, model_name: str | None = None):
        # מודלים עדכניים וזמינים למפתחות חדשים (2026)
        primary = model_name or os.getenv("GEMINI_VISION_MODEL", "gemini-3.8-flash")
        fallback_1 = os.getenv("GEMINI_FALLBACK_MODEL_1", "gemini-2.5-flash")
        fallback_2 = os.getenv("GEMINI_FALLBACK_MODEL_2", "gemini-3.1-flash")

        self.models = [primary, fallback_1, fallback_2]
        self.models = list(dict.fromkeys(filter(None, self.models)))

        self.max_attempts = 3
        self._cache: dict[str, int] = {}
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=CALL_TIMEOUT_MS),
        ) if api_key else None

    def _generate_with_retry(self, contents) -> str:
        # הסרנו את thinking_config כדי למנוע 400 INVALID_ARGUMENT
        config = types.GenerateContentConfig(temperature=0.0)
        last_exc = None

        for model in self.models:
            for attempt in range(self.max_attempts):
                try:
                    print(f"🔄 מנסה מודל: {model} (ניסיון {attempt + 1}/{self.max_attempts})")
                    res = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    )
                    if res.text:
                        print(f"✅ הצלחה עם מודל: {model}")
                        return res.text
                except genai_errors.APIError as exc:
                    last_exc = exc
                    code = getattr(exc, "code", None)
                    print(f"⚠️ Vision {model} ניסיון {attempt + 1} נכשל ({code}): {exc}")
                    if code not in RETRYABLE_CODES:
                        break
                    wait_time = 2 ** attempt
                    print(f"⏳ ממתין {wait_time} שניות לפני ניסיון חוזר...")
                    time.sleep(wait_time)
                except Exception as exc:
                    last_exc = exc
                    print(f"⚠️ Vision {model} שגיאה לא צפויה: {exc}")
                    break
            print(f"🔁 המודל {model} נכשל לחלוטין, עובר למודל הבא...")

        raise ExternalServiceError(
            f"כל מודלי ה-Vision נכשלו. השגיאה האחרונה: {last_exc}"
        )

    def count_heads(self, image_bytes: bytes, mime_type: str) -> int:
        if not self.client:
            raise ExternalServiceError("מפתח GEMINI_API_KEY לא הוגדר בשרת.")

        img_hash = hashlib.sha256(image_bytes).hexdigest()
        if img_hash in self._cache:
            return self._cache[img_hash]

        small_bytes, small_mime = prepare_image(image_bytes)
        prompt = (
            "Count the exact number of real students/people sitting in this classroom photo. "
            "Do not count people on projector screens or posters. "
            "Reply with ONLY a single integer number."
        )
        text = self._generate_with_retry([
            types.Part.from_bytes(data=small_bytes, mime_type=small_mime),
            prompt,
        ])

        match = re.search(r"\d+", text)
        if not match:
            raise ExternalServiceError(f"פלט לא צפוי מ-Gemini Vision: {text}")

        count = int(match.group(0))
        self._cache[img_hash] = count
        return count


class MockHeadcountStrategy(IHeadcountStrategy):
    def __init__(self, fixed_count: int = 15):
        self.fixed_count = fixed_count

    def count_heads(self, image_bytes: bytes, mime_type: str) -> int:
        return self.fixed_count