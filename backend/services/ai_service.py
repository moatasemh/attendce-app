import hashlib
import os
import subprocess
import tempfile
import time
import requests
import imageio_ffmpeg
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from models.exceptions import ExternalServiceError

RETRYABLE_CODES = {429, 503}
BACKOFF_SECONDS = [1, 2]
CALL_TIMEOUT_MS = 90_000
FFMPEG_TIMEOUT_S = 120
INLINE_AUDIO_LIMIT_BYTES = 18 * 1024 * 1024  # 18MB

SUMMARY_PROMPT = (
    "You are an expert teaching assistant. Summarize the following lecture content into a clear, concise Markdown document "
    "(in the same language as the lecture — Hebrew or English). Structure it strictly with these 4 headings:\n"
    "1. **Quick Recap**: Executive summary of the main topics discussed.\n"
    "2. **Key Concepts & Definitions**: Important technical terms or ideas introduced.\n"
    "3. **Student Difficulties / Q&A**: Questions raised, confusion points, or common pitfalls.\n"
    "4. **Next Steps / Assignments**: Homework, tasks, or action items mentioned."
)


def extract_audio(video_bytes: bytes) -> bytes | None:
    """ממיר וידאו לאודיו MP3 מונו דחוס (כ-900KB ל-5 דקות) תוך ~1.5 שניות."""
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "input.mp4")
            dst = os.path.join(tmp, "audio.mp3")
            with open(src, "wb") as f:
                f.write(video_bytes)
            subprocess.run(
                [
                    ffmpeg, "-y", "-loglevel", "error", "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000", "-b:a", "24k",
                    "-c:a", "libmp3lame", dst,
                ],
                check=True,
                capture_output=True,
                timeout=FFMPEG_TIMEOUT_S,
            )
            with open(dst, "rb") as f:
                return f.read()
    except Exception as exc:
        print(f"⚠️ המרה לאודיו נכשלה, ממשיך עם המקור: {exc}")
        return None


class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=CALL_TIMEOUT_MS),
        ) if api_key else None

        self.models = [os.getenv("GEMINI_SUMMARY_MODEL", "gemini-3.5-flash-lite")]
        fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash").strip()
        if fallback and fallback not in self.models:
            self.models.append(fallback)
        self.max_attempts = 2
        self._summary_cache: dict[str, str] = {}

    @staticmethod
    def _extract_text(response) -> str:
        if getattr(response, "text", None):
            return response.text.strip()
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    return part.text.strip()
        return ""

    def _generate_with_retry(self, contents) -> str:
        config = types.GenerateContentConfig(temperature=0.0)
        last_exc = None
        for model in self.models:
            for attempt in range(self.max_attempts):
                try:
                    res = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    )
                    text = self._extract_text(res)
                    if text:
                        return text
                    last_exc = RuntimeError(f"המודל {model} החזיר תשובה ריקה.")
                except genai_errors.APIError as exc:
                    last_exc = exc
                    code = getattr(exc, "code", None)
                    print(f"⚠️ Summary {model} ניסיון {attempt + 1} נכשל ({code}): {exc}")
                    if code not in RETRYABLE_CODES:
                        break
                    time.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
                except Exception as exc:
                    last_exc = exc
                    print(f"⚠️ Summary {model} שגיאה: {exc}")
                    break
        raise ExternalServiceError(f"שגיאה בסיכום AI: {last_exc}")

    def summarize_content(
        self,
        content: str,
        is_file: bool = False,
        file_bytes: bytes = None,
        mime_type: str = None,
    ) -> str:
        if not self.client:
            raise ExternalServiceError("מפתח GEMINI_API_KEY לא מוגדר בשרת.")

        if not (is_file and file_bytes):
            return self._generate_with_retry([SUMMARY_PROMPT, content])

        cache_key = hashlib.sha256(file_bytes).hexdigest()
        if cache_key in self._summary_cache:
            return self._summary_cache[cache_key]

        mime_type = mime_type or "application/octet-stream"

        if mime_type.startswith("text/"):
            text = file_bytes.decode("utf-8", errors="ignore")
            summary = self._generate_with_retry([SUMMARY_PROMPT, text])
            self._summary_cache[cache_key] = summary
            return summary

        if mime_type.startswith("video/"):
            audio = extract_audio(file_bytes)
            if audio:
                file_bytes, mime_type = audio, "audio/mp3"

        # שליחה ישירה בזיכרון (Inline) ללא המתנה ל-File API — חוסך 15-30 שניות
        if len(file_bytes) <= INLINE_AUDIO_LIMIT_BYTES:
            part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            summary = self._generate_with_retry([part, SUMMARY_PROMPT])
            self._summary_cache[cache_key] = summary
            return summary

        raise ExternalServiceError("קובץ האודיו גדול מדי לעיבוד מהיר (מעל 18MB).")

    def review_homework(self, repo_url: str) -> str:
        if "github.com" not in repo_url:
            return "Invalid GitHub URL."

        parts = repo_url.rstrip("/").replace(".git", "").split("/")
        owner, repo = parts[-2], parts[-1]

        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"

        res = requests.get(api_url, headers=headers, timeout=15)
        if res.status_code != 200:
            return f"Could not fetch repo: {res.text}"

        files = res.json()
        code_content = ""
        for f in files:
            if f["name"].endswith((".py", ".java", ".js", ".cpp", ".c", ".md")):
                file_res = requests.get(f["download_url"], timeout=15)
                code_content += f"\n--- {f['name']} ---\n{file_res.text}\n"

        if not code_content:
            return "No code files found in the root of the repo."

        prompt = (
            f"Review the following student code from the repository {repo_url}. "
            "Provide constructive feedback on structure, bugs, and code quality. "
            "Keep it brief and encouraging."
        )
        try:
            return self._generate_with_retry([prompt, code_content])
        except ExternalServiceError as e:
            return f"AI review failed: {e}"