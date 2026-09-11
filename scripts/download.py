#!/usr/bin/env python3
"""
Novel Downloader V2.1 Compatibility Entrypoint
Delegates execution to novel_downloader.orchestrator.
"""
import sys
import os
import json
import argparse

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from novel_downloader.orchestrator import NovelDownloaderOrchestrator
from novel_downloader.models import DownloadStatus

def download_novel(
    name: str,
    output_dir: str = "./downloads",
    author: str = None,
    url: str = None,
    concurrency: int = 12,
    allow_low_quality: bool = False
) -> bool:
    orchestrator = NovelDownloaderOrchestrator(
        novel_name=name,
        author=author,
        url=url,
        output_dir=output_dir,
        concurrency=concurrency,
        allow_low_quality=allow_low_quality
    )
    report = orchestrator.run()
    print("\n" + report.summary())
    return report.status == DownloadStatus.SUCCESS

def main():
    parser = argparse.ArgumentParser(description="Novel Downloader V2.1 CLI")
    parser.add_argument("novel_name", nargs="?", default="", help="小说书名")
    parser.add_argument("--author", "-a", default=None, help="小说原作者")
    parser.add_argument("--url", "-u", default=None, help="直连目标小说目录页 URL")
    parser.add_argument("--output-dir", "-o", default="./downloads", help="保存 TXT 的目标目录")
    parser.add_argument("--concurrency", "-c", type=int, default=12, help="并发抓取线程数")
    parser.add_argument("--allow-low-quality", action="store_true", help="允许在无达标源时下载最佳低质量源 (不标记为 SUCCESS)")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    if not args.novel_name and not args.url:
        parser.print_help()
        print("\n[错误] 请提供小说书名 或 --url 参数！")
        sys.exit(1)

    novel_title = args.novel_name or "未命名小说"
    orchestrator = NovelDownloaderOrchestrator(
        novel_name=novel_title,
        author=args.author,
        url=args.url,
        output_dir=args.output_dir,
        concurrency=args.concurrency,
        allow_low_quality=args.allow_low_quality
    )
    report = orchestrator.run()

    if args.json:
        report_dict = {
            "status": report.status.value,
            "novel_name": report.novel_name,
            "author": report.author,
            "providers_used": report.providers_used,
            "candidates_found": report.candidates_found,
            "candidates_parsed": report.candidates_parsed,
            "candidates_qualified": report.candidates_qualified,
            "selected_source": report.selected_source,
            "selected_source_score": report.selected_source_score,
            "selected_source_qualified": report.selected_source_qualified,
            "quality_reasons": report.quality_reasons,
            "chapter_count": report.chapter_count,
            "failed_chapters": report.failed_chapters,
            "output_file": report.output_file,
            "post_validation": {
                "is_valid": report.post_validation.is_valid,
                "total_chapters": report.post_validation.total_chapters,
                "success_chapters": report.post_validation.success_chapters,
                "failed_chapters": report.post_validation.failed_chapters,
                "failed_ratio": report.post_validation.failed_ratio,
                "reasons": report.post_validation.reasons
            } if report.post_validation else None,
            "failures": [
                {"stage": f.stage, "target": f.target, "reason": f.reason}
                for f in report.failures
            ]
        }
        print(json.dumps(report_dict, ensure_ascii=False, indent=2))
    else:
        print("\n" + report.summary())

    sys.exit(0 if report.status == DownloadStatus.SUCCESS else 1)

if __name__ == "__main__":
    main()
