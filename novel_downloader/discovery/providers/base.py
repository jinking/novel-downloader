from abc import ABC, abstractmethod
from typing import List
from novel_downloader.models import SearchResult

class SearchProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        pass
