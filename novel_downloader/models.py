"""
Data Contract & Models for Novel Downloader V2.1
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable, Any

class DownloadStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"
    UNREACHABLE = "unreachable"
    UNPARSABLE = "unparsable"
    LOW_QUALITY = "low_quality"
    DOWNLOAD_FAILED = "download_failed"

@dataclass
class SearchResult:
    provider: str
    query: str
    title: str
    url: str
    snippet: Optional[str] = None
    rank: int = 0

@dataclass
class Candidate:
    url: str
    domain: str
    discovered_by: List[str] = field(default_factory=list)
    matched_queries: List[str] = field(default_factory=list)
    search_titles: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)
    
    discovery_score: float = 0.0
    parse_score: float = 0.0
    quality_score: float = 0.0
    total_score: float = 0.0

@dataclass
class Chapter:
    title: str
    url: str
    index: int = 0

@dataclass
class ChapterContent:
    url: str
    title: str
    text: str
    length: int = 0
    is_valid: bool = True

@dataclass
class ValidationResult:
    identity_score: float = 0.0
    catalog_score: float = 0.0
    content_score: float = 0.0
    completeness_score: float = 0.0
    total_score: float = 0.0
    is_qualified: bool = False
    reasons: List[str] = field(default_factory=list)

@dataclass
class PostDownloadValidationResult:
    is_valid: bool = False
    total_chapters: int = 0
    success_chapters: int = 0
    failed_chapters: int = 0
    failed_ratio: float = 0.0
    reasons: List[str] = field(default_factory=list)

@dataclass
class ProbeResult:
    engine: str
    title: str
    chapters: List[Chapter]
    downloader_func: Callable[[Chapter], ChapterContent]
    author: Optional[str] = None
    is_book_page: bool = True
    probe_score: float = 0.0
    validation: Optional[ValidationResult] = None

@dataclass
class FailureRecord:
    stage: str
    target: str
    reason: str
    details: Optional[str] = None

@dataclass
class DownloadReport:
    status: DownloadStatus
    novel_name: str
    author: Optional[str] = None
    providers_used: List[str] = field(default_factory=list)
    candidates_found: int = 0
    candidates_parsed: int = 0
    candidates_qualified: int = 0
    selected_source: Optional[str] = None
    selected_source_score: float = 0.0
    selected_source_qualified: bool = False
    quality_reasons: List[str] = field(default_factory=list)
    chapter_count: int = 0
    failed_chapters: int = 0
    output_file: Optional[str] = None
    post_validation: Optional[PostDownloadValidationResult] = None
    failures: List[FailureRecord] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"=== Novel Downloader V2.1 任务报告 ===",
            f"书名: 《{self.novel_name}》" + (f" (作者: {self.author})" if self.author else ""),
            f"最终状态: {self.status.value.upper()}",
            f"调用发现引擎: {', '.join(self.providers_used) if self.providers_used else '无'}",
            f"候选源统计: 发现 {self.candidates_found} 个 -> 解析 {self.candidates_parsed} 个 -> 达标 {self.candidates_qualified} 个",
        ]
        if self.selected_source:
            lines.append(f"中标源站: {self.selected_source}")
            lines.append(f"质量评分: {self.selected_source_score:.1f}")
            lines.append(f"质量验收: {'PASS' if self.selected_source_qualified else 'FAIL'}")
            lines.append(f"章节总数: {self.chapter_count} (失败/丢失: {self.failed_chapters})")
            if self.output_file:
                lines.append(f"导出文件: {self.output_file}")

        if not self.selected_source_qualified and self.quality_reasons:
            lines.append(f"\n[质量不达标原因]")
            for r in self.quality_reasons:
                lines.append(f"  - {r}")
        
        if self.status != DownloadStatus.SUCCESS and self.failures:
            lines.append(f"\n[失败与异常追溯]")
            for f in self.failures[:6]:
                lines.append(f"  - [{f.stage}] {f.target}: {f.reason}")
        return "\n".join(lines)
