"""
Base Novel Parser Interface
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from novel_downloader.models import Candidate, ProbeResult, Chapter, ChapterContent

class NovelParser(ABC):
    @abstractmethod
    def probe(self, candidate: Candidate, keyword: str) -> Optional[ProbeResult]:
        """探测并返回目录章节与下载函数"""
        pass
