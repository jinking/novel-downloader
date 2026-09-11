"""
Multi-dimensional Quality Validator for Novel Downloader V2.1
Combines identity matching, catalog health, 5-point content sampling, and completeness checks.
"""
import re
from typing import List, Optional
from novel_downloader.models import ProbeResult, Candidate, ValidationResult, ChapterContent

TRUNCATED_MARKERS = [
    "请安装app", "请下载客户端", "付费章节", "购买后继续",
    "试读结束", "vip会员", "前往正版", "由于版权原因", "系统正在转码",
    "书库收录了全网最齐全"
]

FINISH_MARKERS = [
    "大结局", "完结", "完本", "终章", "尾声", "番外", "后记", "全书完"
]

CHAPTER_REGEX = re.compile(
    r"(第\s*[0-9一二三四五六七八九十百千万零]+\s*[章回卷节篇]|序[章言]|楔子|尾声|番外|后记|终章|^\s*\d{1,4}[\.、\s]|\b\d{1,4}\b)"
)

class SourceValidator:
    """小说源质量验收器"""

    @classmethod
    def validate(cls, probe: ProbeResult, novel_name: str, author: Optional[str] = None, candidate: Optional[Candidate] = None) -> ValidationResult:
        reasons = []

        # 1. 身份吻合度评分 (30分)
        identity_score = cls._score_identity(probe, novel_name, author, reasons)

        # 2. 目录健康度评分 (20分)
        catalog_score = cls._score_catalog(probe, reasons)

        # 3. 5点正文抽样评分 (30分)
        content_score = cls._score_content_samples(probe, reasons)

        # 4. 产物完整度与完本特征评分 (15分)
        completeness_score = cls._score_completeness(probe, reasons)

        # 5. 发现层信誉分 (5分)
        discovery_score = 0.0
        if candidate:
            discovery_score = min(5.0, candidate.discovery_score * 0.05)

        total_score = identity_score + catalog_score + content_score + completeness_score + discovery_score

        # 达标条件判断
        is_qualified = True
        if identity_score < 15.0:
            is_qualified = False
            reasons.append("书名或作者严重不匹配")
        if content_score < 12.0:
            is_qualified = False
            reasons.append("正文抽样均长过短或包含大面积截断广告/书库推广")
        if catalog_score < 8.0:
            is_qualified = False
            reasons.append("目录章节数过少、重复率过高或非正规章节标题")
        if total_score < 60.0:
            is_qualified = False
            reasons.append(f"综合评分不足60分 ({total_score:.1f})")

        return ValidationResult(
            identity_score=round(identity_score, 1),
            catalog_score=round(catalog_score, 1),
            content_score=round(content_score, 1),
            completeness_score=round(completeness_score, 1),
            total_score=round(total_score, 1),
            is_qualified=is_qualified,
            reasons=reasons
        )

    @classmethod
    def _score_identity(cls, probe: ProbeResult, novel_name: str, author: Optional[str], reasons: List[str]) -> float:
        score = 0.0
        clean_target = re.sub(r"[^\w\u4e00-\u9fa5]", "", novel_name).lower()
        clean_title = re.sub(r"[^\w\u4e00-\u9fa5]", "", probe.title).lower()

        # 书名匹配 (最高 20 分)
        if clean_target in clean_title:
            score += 20.0
        elif any(part in clean_title for part in clean_target.split() if len(part) >= 2):
            score += 10.0
        else:
            reasons.append(f"页面标题《{probe.title}》未命中书名《{novel_name}》")
            return 0.0

        # 作者匹配 (最高 10 分)
        if author:
            clean_author = re.sub(r"[^\w\u4e00-\u9fa5]", "", author).lower()
            if probe.author:
                clean_probe_author = re.sub(r"[^\w\u4e00-\u9fa5]", "", probe.author).lower()
                if clean_author in clean_probe_author or clean_probe_author in clean_author:
                    score += 10.0
                else:
                    reasons.append(f"作者不匹配: 预期={author}, 页面={probe.author}")
                    score += 2.0
            elif clean_author in clean_title:
                score += 10.0
            else:
                score += 5.0
        else:
            score += 10.0

        return score

    @classmethod
    def _score_catalog(cls, probe: ProbeResult, reasons: List[str]) -> float:
        score = 0.0
        ch_count = len(probe.chapters)
        if ch_count == 0:
            reasons.append("章节目录为空")
            return 0.0

        valid_chap_titles = sum(1 for ch in probe.chapters if CHAPTER_REGEX.search(ch.title))
        format_ratio = valid_chap_titles / float(ch_count)
        if format_ratio < 0.40 or (valid_chap_titles == 0 and ch_count >= 3):
            reasons.append(f"章节标题正规率极低 ({format_ratio*100:.1f}%)，判定为伪目录或推荐流")
            return 0.0

        if ch_count >= 100:
            score += 10.0
        elif ch_count >= 30:
            score += 8.0
        elif ch_count >= 10:
            score += 5.0
        else:
            score += 2.0
            reasons.append(f"章节总数偏少 ({ch_count} 章)")

        titles = [ch.title for ch in probe.chapters]
        unique_count = len(set(titles))
        repeat_rate = 1.0 - (unique_count / float(ch_count))
        if repeat_rate > 0.25:
            reasons.append(f"章节标题重复率异常高 ({repeat_rate * 100:.1f}%)")
            score += 0.0
        elif repeat_rate > 0.10:
            score += 5.0
        else:
            score += 10.0

        return score

    @classmethod
    def _score_content_samples(cls, probe: ProbeResult, reasons: List[str]) -> float:
        """5点抽样法：第1章、25%、50%、75%与尾章"""
        ch_len = len(probe.chapters)
        if ch_len == 0:
            return 0.0

        if ch_len <= 5:
            sample_indices = list(range(ch_len))
        else:
            sample_indices = [
                0,
                int(ch_len * 0.25),
                int(ch_len * 0.50),
                int(ch_len * 0.75),
                ch_len - 1
            ]

        valid_samples = 0
        total_chars = 0
        truncated_count = 0

        for idx in sample_indices:
            ch = probe.chapters[idx]
            try:
                content: ChapterContent = probe.downloader_func(ch)
                if content and content.is_valid and len(content.text) > 80:
                    valid_samples += 1
                    total_chars += len(content.text)
                    if any(marker in content.text for marker in TRUNCATED_MARKERS):
                        truncated_count += 1
            except Exception:
                pass

        if not valid_samples:
            reasons.append("抽样章节正文抓取全部失败")
            return 0.0

        avg_len = total_chars / float(valid_samples)
        sample_success_rate = valid_samples / float(len(sample_indices))

        score = 0.0
        score += sample_success_rate * 12.0

        if avg_len >= 3000:
            score += 14.0
        elif avg_len >= 1800:
            score += 11.0
        elif avg_len >= 800:
            score += 8.0
        elif avg_len >= 400:
            score += 4.0
        else:
            score += 1.0
            reasons.append(f"抽样章节平均字数过短 ({int(avg_len)} 字)")

        if truncated_count == 0:
            score += 4.0
        else:
            reasons.append(f"检测到 {truncated_count} 处包含防爬/截断/推广关键词的抽样章节")

        return score

    @classmethod
    def _score_completeness(cls, probe: ProbeResult, reasons: List[str]) -> float:
        score = 8.0
        if not probe.chapters:
            return 0.0

        last_title = probe.chapters[-1].title
        if any(marker in last_title for marker in FINISH_MARKERS):
            score += 7.0
        elif len(probe.chapters) > 200:
            score += 4.0

        return min(15.0, score)
