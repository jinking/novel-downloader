from novel_downloader.validation.validator import SourceValidator
from novel_downloader.models import ProbeResult, Chapter, ChapterContent

def test_source_validator_rejects_irrelevant_title():
    probe = ProbeResult(
        engine="universal",
        title="某不相干的仙侠传奇",
        chapters=[Chapter(title=f"第{i}章", url=f"https://x.com/{i}", index=i) for i in range(50)],
        downloader_func=lambda ch: ChapterContent(url=ch.url, title=ch.title, text="内容" * 50, is_valid=True)
    )
    val = SourceValidator.validate(probe, "全职高手", "蝴蝶蓝")
    assert val.is_qualified is False
    assert any("未命中书名" in r for r in val.reasons)

def test_source_validator_rejects_fake_catalog():
    # 章节标题全是推荐书名，没有“第X章”
    probe = ProbeResult(
        engine="universal",
        title="诛仙 全集在线阅读",
        chapters=[
            Chapter(title="穿越封神", url="https://x.com/1", index=0),
            Chapter(title="洪荒日记", url="https://x.com/2", index=1),
            Chapter(title="太玄忘情篇", url="https://x.com/3", index=2),
            Chapter(title="七零小孤女", url="https://x.com/4", index=3),
            Chapter(title="养生宝妈", url="https://x.com/5", index=4),
        ],
        downloader_func=lambda ch: ChapterContent(url=ch.url, title=ch.title, text="内容" * 50, is_valid=True)
    )
    val = SourceValidator.validate(probe, "诛仙")
    assert val.is_qualified is False
    assert any("正规率极低" in r or "伪目录" in r for r in val.reasons)

def test_source_validator_passes_qualified_source():
    probe = ProbeResult(
        engine="universal",
        title="诛仙(萧鼎所著小说)_小说在线阅读",
        author="萧鼎",
        chapters=[Chapter(title=f"第{i}章 青云", url=f"https://x.com/{i}", index=i) for i in range(120)],
        downloader_func=lambda ch: ChapterContent(url=ch.url, title=ch.title, text="天地不仁以万物为刍狗，神州浩土..." * 40, is_valid=True)
    )
    val = SourceValidator.validate(probe, "诛仙", "萧鼎")
    assert val.is_qualified is True
    assert val.total_score >= 70.0
