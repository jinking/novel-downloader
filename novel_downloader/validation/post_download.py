"""
Post-Download Artifact Validator for Novel Downloader V2.1
Validates full text completeness, chapter loss ratio, and text health.
"""
from typing import List
from novel_downloader.models import ChapterContent, PostDownloadValidationResult

class PostDownloadValidator:
    @classmethod
    def validate(cls, chapters: List[ChapterContent]) -> PostDownloadValidationResult:
        total = len(chapters)
        reasons = []
        if total == 0:
            return PostDownloadValidationResult(
                is_valid=False,
                total_chapters=0,
                success_chapters=0,
                failed_chapters=0,
                failed_ratio=1.0,
                reasons=["抓取产物章节为空"]
            )

        success_chapters = 0
        failed_chapters = 0
        short_chapters = 0
        total_chars = 0

        for ch in chapters:
            if not ch.is_valid or not ch.text or ch.text.startswith("【本章正文抓取失败"):
                failed_chapters += 1
            else:
                success_chapters += 1
                t_len = len(ch.text)
                total_chars += t_len
                if t_len < 100:
                    short_chapters += 1

        failed_ratio = failed_chapters / float(total)
        short_ratio = short_chapters / float(total)

        is_valid = True
        if failed_ratio > 0.15:
            is_valid = False
            reasons.append(f"产物缺章率过高 ({failed_ratio*100:.1f}%, 丢失 {failed_chapters}/{total} 章)")

        if success_chapters > 0:
            avg_len = total_chars / float(success_chapters)
            if avg_len < 150:
                is_valid = False
                reasons.append(f"有效章节平均长度异常过短 ({int(avg_len)} 字)")

        if short_ratio > 0.40 and total > 10:
            is_valid = False
            reasons.append(f"异常短小章节比例过高 ({short_ratio*100:.1f}%)")

        return PostDownloadValidationResult(
            is_valid=is_valid,
            total_chapters=total,
            success_chapters=success_chapters,
            failed_chapters=failed_chapters,
            failed_ratio=round(failed_ratio, 3),
            reasons=reasons
        )
