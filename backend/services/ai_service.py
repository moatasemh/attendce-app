import os
import requests
from google import genai
from google.genai import types
from models.exceptions import ExternalServiceError


class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # עדכון שם המודל ל-gemini-3.8-flash
        self.model_name = "gemini-3.8-flash"

    def summarize_content(self, content: str, is_file: bool = False, file_bytes: bytes = None,
                          mime_type: str = None) -> str:
        if not self.client:
            raise ExternalServiceError("מפתח GEMINI_API_KEY לא מוגדר.")

        prompt = (
            "You are an expert teaching assistant. Summarize the following lecture content into a well-structured Markdown format. "
            "Structure the summary exactly like this:\n"
            "1. **Quick Recap**: A brief executive summary of the main topics discussed.\n"
            "2. **Key Concepts & Definitions**: Important technical terms or ideas introduced in the lecture.\n"
            "3. **Student Difficulties / Q&A**: Any areas of confusion, questions raised, or common pitfalls.\n"
            "4. **Next Steps / Assignments**: Any homework, tasks, or next actions mentioned in the lecture."
        )

        try:
            if is_file and file_bytes:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[types.Part.from_bytes(data=file_bytes, mime_type=mime_type), prompt]
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, content]
                )
            return response.text
        except Exception as e:
            raise ExternalServiceError(f"שגיאה בסיכום AI: {e}")

    def review_homework(self, repo_url: str) -> str:
        if "github.com" not in repo_url:
            return "Invalid GitHub URL."

        parts = repo_url.rstrip("/").replace(".git", "").split("/")
        owner, repo = parts[-2], parts[-1]

        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"

        res = requests.get(api_url, headers=headers)
        if res.status_code != 200:
            return f"Could not fetch repo: {res.text}"

        files = res.json()
        code_content = ""
        for f in files:
            if f["name"].endswith((".py", ".java", ".js", ".cpp", ".c", ".md")):
                file_res = requests.get(f["download_url"])
                code_content += f"\n--- {f['name']} ---\n{file_res.text}\n"

        if not code_content:
            return "No code files found in the root of the repo."

        prompt = (
            f"Review the following student code from the repository {repo_url}. "
            "Provide constructive feedback on structure, bugs, and code quality. "
            "Keep it brief and encouraging."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, code_content]
            )
            return response.text
        except Exception as e:
            return f"AI review failed: {e}"