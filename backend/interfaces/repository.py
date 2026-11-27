from abc import ABC, abstractmethod


class IDataRepository(ABC):
    """חוזה מופשט לגישה למסד נתונים (מאפשר החלפה ל-InMemory בבדיקות)."""

    @abstractmethod
    def get_records(self, collection: str, filter_str: str = "", sort_str: str = "") -> list[dict]:
        pass

    @abstractmethod
    def create_record(self, collection: str, data: dict) -> dict:
        pass

    @abstractmethod
    def update_record(self, collection: str, record_id: str, data: dict) -> dict:
        pass