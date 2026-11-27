import os
import re
import requests
from models.exceptions import ExternalServiceError, ResourceNotFoundError

CODE_EXTENSIONS = (".py", ".java", ".js", ".ts", ".cpp", ".c", ".h", ".cs", ".go", ".rb", ".kt", ".php")
EXCLUDED_DIRS = {"node_modules", "vendor", "venv", ".venv", "dist", "build", "__pycache__"}
MAX_FILE_BYTES = 200_000
MAX_FILES = 150
TIMEOUT = 15


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = (token or os.getenv("GITHUB_TOKEN") or "").strip() or None

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def _get(self, url: str):
        res = requests.get(url, headers=self._headers(), timeout=TIMEOUT)

        # טוקן שגוי או פג תוקף: ממשיכים בלי אימות (עובד למאגרים ציבוריים)
        if res.status_code == 401 and self.token:
            print("⚠️ GITHUB_TOKEN לא תקין. ממשיך ללא אימות. בדוק את קובץ .env")
            self.token = None
            res = requests.get(url, headers=self._headers(), timeout=TIMEOUT)

        return res

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str] | None:
        m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url or "")
        if not m:
            return None
        owner, repo = m.group(1), m.group(2)
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo

    def fetch_code(self, url: str) -> dict[str, str]:
        parsed = self.parse_repo_url(url)
        if not parsed:
            raise ResourceNotFoundError(f"קישור GitHub לא תקין: {url}")
        owner, repo = parsed

        tree_res = self._get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1")

        if tree_res.status_code == 404:
            raise ResourceNotFoundError(f"המאגר לא נמצא או פרטי: {url}")
        if tree_res.status_code in (403, 429):
            raise ExternalServiceError("GitHub הגביל את מספר הבקשות. נסה שוב מאוחר יותר או הגדר GITHUB_TOKEN תקין.")
        if tree_res.status_code != 200:
            raise ExternalServiceError(f"שגיאת GitHub ({tree_res.status_code}) עבור {url}")

        tree = tree_res.json().get("tree", [])
        paths = [
            e["path"] for e in tree
            if e.get("type") == "blob"
            and e["path"].endswith(CODE_EXTENSIONS)
            and e.get("size", 0) <= MAX_FILE_BYTES
            and not EXCLUDED_DIRS.intersection(e["path"].split("/"))
        ][:MAX_FILES]

        sources: dict[str, str] = {}
        for path in paths:
            r = self._get(f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}")
            if r.status_code == 200:
                sources[path] = r.text
        return sources