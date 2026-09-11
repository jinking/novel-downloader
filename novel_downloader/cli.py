"""
Novel Downloader V2 CLI Interface
"""
import sys
import json
import argparse
from novel_downloader.orchestrator import NovelDownloaderOrchestrator
from novel_downloader.models import DownloadStatus

def main():
    parser = argparse.ArgumentParser(
        description="Novel Downloader V2 - 全网小说反爬逆向与智能质量校验下载引擎",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("novel_name", nargs="?", default="", help="小说书名 (若未提供可配合 --url 使用)")
    parser.add_argument("--author", "-a", default=None, help="小说原作者 (可选，提供后大幅提高源站精准匹配)")
    parser.add_argument("--url", "-u", default=None, help="指定小说目录页或简介页 URL (直连模式，跳过全网搜索)")
    parser.add_argument("--output-dir", "-o", default="./downloads", help="保存 TXT 小说的目标目录 (默认: ./downloads)")
    parser.add_argument("--concurrency", "-c", type=int, default=25, help="章节并发抓取线程数 (默认: 25)")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出最终的诊断与执行报告")

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
        concurrency=args.concurrency
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
            "chapter_count": report.chapter_count,
            "failed_chapters": report.failed_chapters,
            "output_file": report.output_file,
            "failures": [
                {"stage": f.stage, "target": f.target, "reason": f.reason}
                for f in report.failures
            ]
        }
        print(json.dumps(report_dict, ensure_ascii=False, indent=2))
    else:
        print("\n" + report.summary())

    if report.status in (DownloadStatus.SUCCESS, DownloadStatus.PARTIAL):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
