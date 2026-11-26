import requests
from interfaces.repository import IDataRepository
from models.exceptions import ExternalServiceError


class PocketBaseRepository(IDataRepository):
    """מימוש קונקרטי של IDataRepository מול PocketBase REST API."""

    def __init__(self, base_url: str, admin_email: str, admin_password: str):
        self.base_url = base_url.rstrip("/")
        self.admin_email = admin_email
        self.admin_password = admin_password
        self._token: str | None = None

    def _authenticate(self) -> str:
        try:
            res = requests.post(
                f"{self.base_url}/api/collections/_superusers/auth-with-password",
                json={"identity": self.admin_email, "password": self.admin_password},
                timeout=10,
            )
            res.raise_for_status()
            self._token = res.json()["token"]
            return self._token
        except requests.RequestException as exc:
            raise ExternalServiceError(f"כשל באימות מול PocketBase: {exc}") from exc

    def _headers(self) -> dict:
        if not self._token:
            self._authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    def _request_with_retry(self, method: str, url: str, **kwargs) -> dict:
        try:
            res = requests.request(method, url, headers=self._headers(), timeout=10, **kwargs)
            if res.status_code == 401:
                self._authenticate()
                res = requests.request(method, url, headers=self._headers(), timeout=10, **kwargs)
            try:
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # ידפיס את השגיאה האמיתית של PocketBase ללוגים
                print(f"❌ PocketBase Error: {res.status_code} - {res.text}")
                raise
            return res.json()
        except requests.RequestException as exc:
            raise ExternalServiceError(f"שגיאת תקשורת מול PocketBase: {exc}") from exc

    def get_records(self, collection: str, filter_str: str = "", sort_str: str = "") -> list[dict]:
        params: dict = {"perPage": 500}
        if filter_str:
            params["filter"] = filter_str
        if sort_str:
            params["sort"] = sort_str
        data = self._request_with_retry(
            "GET",
            f"{self.base_url}/api/collections/{collection}/records",
            params=params,
        )
        return data.get("items", [])

    def create_record(self, collection: str, data: dict) -> dict:
        return self._request_with_retry(
            "POST",
            f"{self.base_url}/api/collections/{collection}/records",
            json=data,
        )

    def update_record(self, collection: str, record_id: str, data: dict) -> dict:
        return self._request_with_retry(
            "PATCH",
            f"{self.base_url}/api/collections/{collection}/records/{record_id}",
            json=data,
        )