import csv
import io
import os
from concurrent.futures import ThreadPoolExecutor
from models.exceptions import DomainError, ResourceNotFoundError
from services.github_client import GitHubClient

MAX_WORKERS = 8


class RepoComparisonService:
    COLLECTION = "repos"

    def __init__(self, repo, github_client: GitHubClient, similarity_strategy):
        self.repo = repo
        self.github = github_client
        self.similarity = similarity_strategy
        self.threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))
        self._fingerprint_cache: dict[str, set[int]] = {}

    # ---------- ייבוא CSV של המרצה ----------
    def import_repos_csv(self, csv_text: str) -> dict:
        reader = csv.DictReader(io.StringIO(csv_text))
        headers = reader.fieldnames or []

        url_col = next((h for h in headers if "github" in h.lower()), None)
        if not url_col:
            raise ResourceNotFoundError("לא נמצאה עמודת קישור GitHub בקובץ ה-CSV.")

        name_col = (
            next((h for h in headers if h.strip() in ("Name", "שם", "שם מלא", "Full name")), None)
            or next((h for h in headers if any(k in h.lower() for k in ("name", "שם"))), None)
            or next((h for h in headers if "email" in h.lower() or "דוא" in h), None)
        )

        existing = {r.get("repo_url"): r for r in self.repo.get_records(self.COLLECTION)}
        added = updated = skipped = 0

        for row in reader:
            url = (row.get(url_col) or "").strip()
            if not url:
                skipped += 1
                continue
            data = {
                "student_name": (row.get(name_col) or "").strip() if name_col else "",
                "repo_url": url,
            }
            if url in existing:
                self.repo.update_record(self.COLLECTION, existing[url]["id"], data)
                updated += 1
            else:
                self.repo.create_record(self.COLLECTION, data)
                added += 1

        self._fingerprint_cache.clear()
        return {"added": added, "updated": updated, "skipped": skipped}

    # ---------- עזרים ----------
    def count(self) -> int:
        return len(self.repo.get_records(self.COLLECTION))

    @staticmethod
    def _key(url: str) -> tuple:
        parsed = GitHubClient.parse_repo_url(url)
        return (parsed[0].lower(), parsed[1].lower()) if parsed else (url.strip().lower(),)

    def _fingerprint(self, url: str) -> set[int]:
        if url not in self._fingerprint_cache:
            sources = self.github.fetch_code(url)
            if not sources:
                raise ResourceNotFoundError(f"לא נמצאו קבצי קוד במאגר: {url}")
            self._fingerprint_cache[url] = self.similarity.fingerprint(sources)
        return self._fingerprint_cache[url]

    # ---------- ציון אחד: המטלה מול כל המאגר ----------
    def compare(self, my_repo_url: str) -> dict:
        if self.count() == 0:
            raise ResourceNotFoundError("המאגר ריק. המרצה צריך להעלות קובץ קישורים קודם.")

        my_fp = self._fingerprint(my_repo_url)  # שגיאה במטלה עצמה מוחזרת למשתמש
        my_key = self._key(my_repo_url)

        others = [
            r["repo_url"] for r in self.repo.get_records(self.COLLECTION)
            if r.get("repo_url") and self._key(r["repo_url"]) != my_key
        ]

        def safe_fingerprint(url: str):
            try:
                return self._fingerprint(url)
            except Exception:
                return None

        # הורדה וניתוח של כל המטלות במקביל
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            fingerprints = list(pool.map(safe_fingerprint, others))

        scores = [self.similarity.score(my_fp, fp) for fp in fingerprints if fp]
        best = max(scores) if scores else 0.0

        return {
            "similarity": round(best * 100, 1),
            "flagged": best >= self.threshold,
            "threshold": round(self.threshold * 100),
            "compared_count": len(scores),
            "failed_count": len(others) - len(scores),
        }

    # ---------- גרסה לסטודנט: אותו ציון, בלי פרטים נוספים ----------
    def compare_for_student(self, my_repo_url: str) -> dict:
        full = self.compare(my_repo_url)
        return {
            "similarity": full["similarity"],
            "flagged": full["flagged"],
            "threshold": full["threshold"],
            "compared_count": full["compared_count"],
        }