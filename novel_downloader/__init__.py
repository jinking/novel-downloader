"""
Novel Downloader V2.1 Package
"""
from novel_downloader.orchestrator import NovelDownloaderOrchestrator
from novel_downloader.models import DownloadStatus, DownloadReport

__version__ = "2.1.0"
__all__ = ["NovelDownloaderOrchestrator", "DownloadStatus", "DownloadReport"]
