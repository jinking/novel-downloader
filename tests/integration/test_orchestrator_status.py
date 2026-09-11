import os
import shutil
from unittest.mock import patch, MagicMock
from novel_downloader.orchestrator import NovelDownloaderOrchestrator
from novel_downloader.models import (
    DownloadStatus, SearchResult, ProbeResult, ValidationResult, Chapter, ChapterContent
)

TEST_OUT_DIR = "./tests_downloads"

def setup_function():
    os.makedirs(TEST_OUT_DIR, exist_ok=True)

def teardown_function():
    if os.path.exists(TEST_OUT_DIR):
        shutil.rmtree(TEST_OUT_DIR)

def test_case_2_ddg_results_unusable_deep_discovery_continues():
    """Case 2: 某搜索引擎有结果但全部不可用，Deep Discovery 由 qualified source 驱动并继续"""
    orchestrator = NovelDownloaderOrchestrator(
        novel_name="测试书",
        output_dir=TEST_OUT_DIR
    )

    with patch("novel_downloader.orchestrator.DiscoveryEngine") as MockEngine, \
         patch("novel_downloader.orchestrator.ParserRouter.probe") as mock_probe, \
         patch("novel_downloader.orchestrator.SourceValidator.validate") as mock_validate, \
         patch("novel_downloader.orchestrator.ConcurrentDownloader.download_all") as mock_download:

        engine_inst = MockEngine.return_value
        engine_inst.get_failures.return_value = []

        # 阶段 1: 返回不可用链接
        mock_pool_1 = MagicMock()
        mock_cand_bad = MagicMock(url="https://bad.com", domain="bad.com", discovered_by=["duckduckgo"])
        mock_pool_1.count.return_value = 1
        mock_pool_1.rank_candidates.return_value = [mock_cand_bad]

        # 阶段 2: 深度搜索返回可用链接
        mock_pool_2 = MagicMock()
        mock_cand_good = MagicMock(url="https://good.com", domain="good.com", discovered_by=["google"])
        mock_pool_2.count.return_value = 2
        mock_pool_2.rank_candidates.return_value = [mock_cand_bad, mock_cand_good]

        engine_inst.discover_candidates.side_effect = [mock_pool_1, mock_pool_2]

        def fake_probe(url, name):
            if "bad.com" in url:
                return None  # 无法解析
            chaps = [Chapter(title=f"第{i}章", url=f"https://good.com/{i}", index=i) for i in range(50)]
            return ProbeResult(engine="universal", title="测试书", chapters=chaps, downloader_func=lambda c: None)
        mock_probe.side_effect = fake_probe

        def fake_validate(probe, name, author, candidate=None):
            return ValidationResult(total_score=85.0, is_qualified=True)
        mock_validate.side_effect = fake_validate

        # 模拟下载成功 (正常章节文本)
        ch_contents = [
            ChapterContent(url=f"https://good.com/{i}", title=f"第{i}章", text="天地不仁以万物为刍狗，神州浩土广瀚无边..." * 30, is_valid=True)
            for i in range(50)
        ]
        mock_download.return_value = (ch_contents, 0)

        report = orchestrator.run()

        # 验证：阶段 2 deep=True 必须被调用（不能因为阶段 1 有 URL 就退出）
        assert engine_inst.discover_candidates.call_count == 2
        assert report.status == DownloadStatus.SUCCESS
        assert report.selected_source == "https://good.com"

def test_case_4_all_sources_unqualified_default_stops_without_download():
    """Case 4 (默认模式): 所有来源未通过质量验收，直接返回 LOW_QUALITY，不进行正式下载"""
    orchestrator = NovelDownloaderOrchestrator(
        novel_name="测试书",
        output_dir=TEST_OUT_DIR,
        allow_low_quality=False
    )

    with patch("novel_downloader.orchestrator.DiscoveryEngine") as MockEngine, \
         patch("novel_downloader.orchestrator.ParserRouter.probe") as mock_probe, \
         patch("novel_downloader.orchestrator.SourceValidator.validate") as mock_validate, \
         patch("novel_downloader.orchestrator.ConcurrentDownloader.download_all") as mock_download:

        engine_inst = MockEngine.return_value
        engine_inst.get_failures.return_value = []
        mock_pool = MagicMock()
        mock_cand = MagicMock(url="https://fake.com/book", domain="fake.com", discovered_by=["ddg"])
        mock_pool.count.return_value = 1
        mock_pool.rank_candidates.return_value = [mock_cand]
        engine_inst.discover_candidates.return_value = mock_pool

        # 章节多 (100章)，但质量校验不达标
        chaps = [Chapter(title=f"第{i}章", url=f"https://fake.com/{i}", index=i) for i in range(100)]
        mock_probe.return_value = ProbeResult(engine="universal", title="假书", chapters=chaps, downloader_func=lambda c: None)
        mock_validate.return_value = ValidationResult(total_score=40.0, is_qualified=False, reasons=["正文全被截断"])

        report = orchestrator.run()

        # 期望：状态为 LOW_QUALITY，不能调用 Downloader，未达标源坚决不下载
        assert report.status == DownloadStatus.LOW_QUALITY
        assert report.selected_source_qualified is False
        assert mock_download.call_count == 0

def test_case_4_allow_low_quality_explicit_flag_still_not_success():
    """Case 4 (显式模式): --allow-low-quality 允许下载，但最终状态坚决不能是 SUCCESS"""
    orchestrator = NovelDownloaderOrchestrator(
        novel_name="测试书",
        output_dir=TEST_OUT_DIR,
        allow_low_quality=True
    )

    with patch("novel_downloader.orchestrator.DiscoveryEngine") as MockEngine, \
         patch("novel_downloader.orchestrator.ParserRouter.probe") as mock_probe, \
         patch("novel_downloader.orchestrator.SourceValidator.validate") as mock_validate, \
         patch("novel_downloader.orchestrator.ConcurrentDownloader.download_all") as mock_download:

        engine_inst = MockEngine.return_value
        engine_inst.get_failures.return_value = []
        mock_pool = MagicMock()
        mock_cand = MagicMock(url="https://fake.com/book", domain="fake.com", discovered_by=["ddg"])
        mock_pool.count.return_value = 1
        mock_pool.rank_candidates.return_value = [mock_cand]
        engine_inst.discover_candidates.return_value = mock_pool

        chaps = [Chapter(title=f"第{i}章", url=f"https://fake.com/{i}", index=i) for i in range(10)]
        mock_probe.return_value = ProbeResult(engine="universal", title="假书", chapters=chaps, downloader_func=lambda c: None)
        mock_validate.return_value = ValidationResult(total_score=45.0, is_qualified=False, reasons=["作者不匹配"])

        # 即使下载了 100% 章节
        ch_contents = [
            ChapterContent(url=f"https://fake.com/{i}", title=f"第{i}章", text="正文内容段落..." * 30, is_valid=True)
            for i in range(10)
        ]
        mock_download.return_value = (ch_contents, 0)

        report = orchestrator.run()

        # 期望：虽然生成了文件，但最终状态必须为 LOW_QUALITY，selected_source_qualified 为 False
        assert report.status == DownloadStatus.LOW_QUALITY
        assert report.selected_source_qualified is False
        assert report.output_file is not None

def test_case_5_validator_pass_but_severe_chapter_loss_results_in_partial():
    """Case 5: SourceValidator 达标，但抓取严重缺章 (1000章丢失220章) -> PARTIAL"""
    orchestrator = NovelDownloaderOrchestrator(
        novel_name="测试书",
        output_dir=TEST_OUT_DIR
    )

    with patch("novel_downloader.orchestrator.DiscoveryEngine") as MockEngine, \
         patch("novel_downloader.orchestrator.ParserRouter.probe") as mock_probe, \
         patch("novel_downloader.orchestrator.SourceValidator.validate") as mock_validate, \
         patch("novel_downloader.orchestrator.ConcurrentDownloader.download_all") as mock_download:

        engine_inst = MockEngine.return_value
        engine_inst.get_failures.return_value = []
        mock_pool = MagicMock()
        mock_cand = MagicMock(url="https://site.com/book", domain="site.com", discovered_by=["ddg"])
        mock_pool.count.return_value = 1
        mock_pool.rank_candidates.return_value = [mock_cand]
        engine_inst.discover_candidates.return_value = mock_pool

        chaps = [Chapter(title=f"第{i}章", url=f"https://site.com/{i}", index=i) for i in range(1000)]
        mock_probe.return_value = ProbeResult(engine="universal", title="测试书", chapters=chaps, downloader_func=lambda c: None)
        mock_validate.return_value = ValidationResult(total_score=85.0, is_qualified=True)

        # 1000 章中有 220 章失败 (占位符)
        ch_contents = []
        for i in range(780):
            ch_contents.append(ChapterContent(url=f"https://site.com/{i}", title=f"第{i}章", text="正文内容段落..." * 30, is_valid=True))
        for i in range(780, 1000):
            ch_contents.append(ChapterContent(url=f"https://site.com/{i}", title=f"第{i}章", text="【本章正文抓取失败，原章节地址: ...】", is_valid=False))

        mock_download.return_value = (ch_contents, 220)

        report = orchestrator.run()

        # 期望：缺章严重，产物验收未通过，最终状态必须为 PARTIAL (决不能为 SUCCESS)
        assert report.status == DownloadStatus.PARTIAL
        assert report.post_validation is not None
        assert report.post_validation.is_valid is False

def test_case_6_complete_success():
    """Case 6: 源质量验收合格 + 抓取完整 + 产物验收合格 -> SUCCESS"""
    orchestrator = NovelDownloaderOrchestrator(
        novel_name="测试书",
        output_dir=TEST_OUT_DIR
    )

    with patch("novel_downloader.orchestrator.DiscoveryEngine") as MockEngine, \
         patch("novel_downloader.orchestrator.ParserRouter.probe") as mock_probe, \
         patch("novel_downloader.orchestrator.SourceValidator.validate") as mock_validate, \
         patch("novel_downloader.orchestrator.ConcurrentDownloader.download_all") as mock_download:

        engine_inst = MockEngine.return_value
        engine_inst.get_failures.return_value = []
        mock_pool = MagicMock()
        mock_cand = MagicMock(url="https://site.com/book", domain="site.com", discovered_by=["ddg"])
        mock_pool.count.return_value = 1
        mock_pool.rank_candidates.return_value = [mock_cand]
        engine_inst.discover_candidates.return_value = mock_pool

        chaps = [Chapter(title=f"第{i}章", url=f"https://site.com/{i}", index=i) for i in range(250)]
        mock_probe.return_value = ProbeResult(engine="universal", title="测试书", chapters=chaps, downloader_func=lambda c: None)
        mock_validate.return_value = ValidationResult(total_score=95.0, is_qualified=True)

        ch_contents = [
            ChapterContent(url=f"https://site.com/{i}", title=f"第{i}章", text="天地不仁以万物为刍狗..." * 50, is_valid=True)
            for i in range(250)
        ]
        mock_download.return_value = (ch_contents, 0)

        report = orchestrator.run()

        assert report.status == DownloadStatus.SUCCESS
        assert report.selected_source_qualified is True
        assert report.post_validation.is_valid is True
        assert report.failed_chapters == 0
