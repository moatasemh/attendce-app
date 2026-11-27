import os
from dotenv import load_dotenv
from facade import SmartClassFacade
from repositories.pocketbase_repo import PocketBaseRepository
from services.attendance_service import AttendanceService
from strategies.export_strategy import ExcelExportStrategy
from strategies.suspicion_strategy import SmartRatioSuspicionStrategy
from strategies.vision_strategy import GeminiVisionStrategy, MockHeadcountStrategy
from services.github_client import GitHubClient
from services.repo_comparison_service import RepoComparisonService
from strategies.similarity_strategy import TokenShingleSimilarity


class SystemFactory:
    """מחלקת הרכבת התלויות (Composition Root) — מחברת את האסטרטגיות וה-Repository ל-Facade."""

    @staticmethod
    def bootstrap() -> SmartClassFacade:
        load_dotenv()

        repo = PocketBaseRepository(
            base_url=os.getenv("POCKETBASE_URL", "http://pocketbase:8090"),
            admin_email=os.getenv("PB_ADMIN_EMAIL", "admin@example.com"),
            admin_password=os.getenv("PB_ADMIN_PASSWORD", "1234567890"),
        )

        use_mock = os.getenv("USE_MOCK_AI", "false").lower() == "true"
        headcount_strategy = (
            MockHeadcountStrategy(fixed_count=20)
            if use_mock
            else GeminiVisionStrategy(api_key=os.getenv("GEMINI_API_KEY"))
        )

        suspicion_strategy = SmartRatioSuspicionStrategy()
        export_strategy =  export_strategy = ExcelExportStrategy()

        attendance_service = AttendanceService(
            repo=repo,
            headcount_strategy=headcount_strategy,
            suspicion_strategy=suspicion_strategy,
            export_strategy=export_strategy,
        )

        comparison_service = RepoComparisonService(
            repo=repo,
            github_client=GitHubClient(),
            similarity_strategy=TokenShingleSimilarity(k=6),
        )

        return SmartClassFacade.configure(
            attendance_service=attendance_service,
            comparison_service=comparison_service,
        )