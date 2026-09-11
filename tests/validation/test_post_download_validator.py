from novel_downloader.validation.post_download import PostDownloadValidator
from novel_downloader.models import ChapterContent

def test_post_download_validator_detects_severe_chapter_loss():
    # 模拟 1000 章，其中 220 章失败
    chapters = []
    for i in range(780):
        chapters.append(ChapterContent(
            url=f"https://example.com/{i}",
            title=f"第{i}章",
            text="这是正常的正文段落。" * 30,
            is_valid=True
        ))
    for i in range(780, 1000):
        chapters.append(ChapterContent(
            url=f"https://example.com/{i}",
            title=f"第{i}章",
            text="【本章正文抓取失败，原章节地址: ...】",
            is_valid=False
        ))

    result = PostDownloadValidator.validate(chapters)
    # 缺章率 22% > 15%，必须判定为 invalid
    assert result.is_valid is False
    assert result.failed_chapters == 220
    assert result.failed_ratio >= 0.20
    assert any("缺章率过高" in r for r in result.reasons)

def test_post_download_validator_passes_on_complete_content():
    chapters = [
        ChapterContent(
            url=f"https://example.com/{i}",
            title=f"第{i}章",
            text="青云山脉巍峨高耸，虎踞中原..." * 20,
            is_valid=True
        )
        for i in range(100)
    ]
    result = PostDownloadValidator.validate(chapters)
    assert result.is_valid is True
    assert result.failed_chapters == 0
    assert result.failed_ratio == 0.0
    assert len(result.reasons) == 0
