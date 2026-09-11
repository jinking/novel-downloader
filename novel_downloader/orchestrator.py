"""
Orchestrator for Novel Downloader V2.1
Strict validation boundaries, post-download verification, and failover support.
"""
import time
from typing import Optional, List, Tuple
from novel_downloader.models import (
    DownloadStatus, DownloadReport, FailureRecord, Candidate, ProbeResult, ValidationResult
)
from novel_downloader.discovery.pool import CandidatePool
from novel_downloader.discovery.engine import DiscoveryEngine
from novel_downloader.parsers.router import ParserRouter
from novel_downloader.validation.validator import SourceValidator
from novel_downloader.validation.post_download import PostDownloadValidator
from novel_downloader.ranking.source_ranker import SourceRanker
from novel_downloader.downloader.concurrent import ConcurrentDownloader
from novel_downloader.export.txt_exporter import TxtExporter

class NovelDownloaderOrchestrator:
    def __init__(
        self,
        novel_name: str,
        author: Optional[str] = None,
        url: Optional[str] = None,
        output_dir: str = "./downloads",
        concurrency: int = 12,
        allow_low_quality: bool = False
    ):
        self.novel_name = novel_name.strip()
        self.author = author.strip() if author else None
        self.manual_url = url.strip() if url else None
        self.output_dir = output_dir
        self.concurrency = concurrency
        self.allow_low_quality = allow_low_quality

    def run(self) -> DownloadReport:
        report = DownloadReport(
            status=DownloadStatus.NOT_FOUND,
            novel_name=self.novel_name,
            author=self.author
        )

        # 模式一：手动直连 URL 模式 (跳过搜索)
        if self.manual_url:
            print(f"[*] 模式: 手动直连 URL 模式 ({self.manual_url})")
            report.providers_used = ["manual_url"]
            report.candidates_found = 1
            
            probe = ParserRouter.probe(self.manual_url, self.novel_name)
            if not probe or not probe.chapters:
                report.status = DownloadStatus.UNPARSABLE
                report.failures.append(FailureRecord(
                    stage="parser",
                    target=self.manual_url,
                    reason="指定 URL 无法提取到有效章节目录"
                ))
                return report

            report.candidates_parsed = 1
            val = SourceValidator.validate(probe, self.novel_name, self.author)
            report.selected_source_score = val.total_score
            report.selected_source_qualified = val.is_qualified
            report.quality_reasons = val.reasons

            if not val.is_qualified and not self.allow_low_quality:
                report.status = DownloadStatus.LOW_QUALITY
                report.failures.append(FailureRecord(
                    stage="validation",
                    target=self.manual_url,
                    reason=f"手动指定源质量校验未通过 ({'; '.join(val.reasons)})"
                ))
                return report

            if val.is_qualified:
                report.candidates_qualified = 1

            return self._execute_download(probe, self.manual_url, val, report)

        # 模式二：全网多源智能发现与严格质量闭环
        print(f"[*] 启动全网多源搜寻: 《{self.novel_name}》" + (f" (作者: {self.author})" if self.author else ""))
        discovery_engine = DiscoveryEngine(self.novel_name, self.author)

        evaluated_sources: List[Tuple[Candidate, ProbeResult, ValidationResult]] = []
        probed_urls = set()
        accessible_count = 0
        parsable_count = 0

        def probe_candidates(candidates: List[Candidate]):
            nonlocal accessible_count, parsable_count
            for cand in candidates:
                if cand.url in probed_urls:
                    continue
                probed_urls.add(cand.url)

                for prov in cand.discovered_by:
                    if prov not in report.providers_used:
                        report.providers_used.append(prov)

                probe = ParserRouter.probe(cand.url, self.novel_name)
                # probe 成功返回结果说明页面至少是可访问的
                if probe:
                    accessible_count += 1

                if not probe or not probe.chapters:
                    report.failures.append(FailureRecord(
                        stage="probe",
                        target=cand.url,
                        reason="未能提取章节列表或页面无响应"
                    ))
                    continue

                parsable_count += 1
                report.candidates_parsed += 1
                val = SourceValidator.validate(probe, self.novel_name, self.author, candidate=cand)
                if val.is_qualified:
                    report.candidates_qualified += 1
                    print(f"    [✓] 发现达标可用源! [{probe.engine}] {cand.domain} | 章节: {len(probe.chapters)} | 质量分: {val.total_score:.1f}")
                else:
                    reason_msg = "; ".join(val.reasons) if val.reasons else "综合评分不足"
                    print(f"    [-] 排除低质/残缺源: {cand.domain} (得分: {val.total_score:.1f}, 章节: {len(probe.chapters)}, 原因: {reason_msg})")

                evaluated_sources.append((cand, probe, val))

        # 第 1 轮：常规搜索
        print("[阶段 1] 发起基础全网搜索 (Google + Yandex + DuckDuckGo + Builtin)...")
        pool = discovery_engine.discover_candidates(deep=False)
        report.candidates_found = pool.count()
        cand_list = pool.rank_candidates()
        probe_candidates(cand_list[:12])

        # 第 2 轮：深度兜底搜索 (以达标源数量 < 2 作为收敛准则，修复伪兜底)
        qualified_count = sum(1 for s in evaluated_sources if s[2].is_qualified)
        if qualified_count < 2:
            print("[阶段 2] 达标全本源储备不足，启动深度拓展检索...")
            pool = discovery_engine.discover_candidates(deep=True)
            report.candidates_found = pool.count()
            cand_list_deep = pool.rank_candidates()
            probe_candidates(cand_list_deep[:15])

        # 汇总 Provider 异常记录
        for pf in discovery_engine.get_failures():
            report.failures.append(pf)

        # 细粒度失败状态诊断
        if report.candidates_found == 0:
            report.status = DownloadStatus.NOT_FOUND
            report.failures.append(FailureRecord(stage="discovery", target=self.novel_name, reason="所有搜索引擎均未检索到相关页面"))
            return report

        if accessible_count == 0 and not evaluated_sources:
            report.status = DownloadStatus.UNREACHABLE
            report.failures.append(FailureRecord(stage="network", target=self.novel_name, reason="搜索命中的候选站点均无法连接或无响应"))
            return report

        if parsable_count == 0 and not evaluated_sources:
            report.status = DownloadStatus.UNPARSABLE
            report.failures.append(FailureRecord(stage="parser", target=self.novel_name, reason="候选页面均无法解析出有效小说章节列表"))
            return report

        ranked_sources = SourceRanker.rank(evaluated_sources)
        qualified_ranked = [s for s in ranked_sources if s[2].is_qualified]

        # 核心质量门槛：未达标源默认坚决不予进入正式下载
        if not qualified_ranked:
            sorted_all = sorted(evaluated_sources, key=lambda x: (x[2].total_score, len(x[1].chapters)), reverse=True)
            best_cand, best_probe, best_val = sorted_all[0]
            
            report.selected_source = best_cand.url
            report.selected_source_score = best_val.total_score
            report.selected_source_qualified = False
            report.quality_reasons = best_val.reasons

            if not self.allow_low_quality:
                report.status = DownloadStatus.LOW_QUALITY
                report.failures.append(FailureRecord(
                    stage="validation",
                    target=best_cand.url,
                    reason=f"所有候选源均未能通过质量校验 ({'; '.join(best_val.reasons)})"
                ))
                return report
            else:
                print(f"[!] 警告: 启用 --allow-low-quality，显式允许下载未达标最佳候选源: {best_cand.domain} (评分: {best_val.total_score})")
                return self._execute_download(best_probe, best_cand.url, best_val, report)

        # 多源故障转移调度执行 (Failover)
        for idx, (cand, probe, val) in enumerate(qualified_ranked):
            if idx > 0:
                print(f"\n[!] 触发源站故障转移，切换至备选顺位源: {cand.domain} (评分: {val.total_score})")
            else:
                print(f"\n[★] 选定最佳优质源: {cand.domain} | 章节: {len(probe.chapters)} | 质量分: {val.total_score}")

            report.selected_source_score = val.total_score
            report.selected_source_qualified = val.is_qualified
            report.quality_reasons = val.reasons

            self._execute_download(probe, cand.url, val, report)

            # 判定本顺位是否顺利通过产物验证
            if report.post_validation and report.post_validation.is_valid:
                break
            if report.chapter_count > 0 and (report.failed_chapters / float(report.chapter_count)) <= 0.15:
                break

        return report

    def _execute_download(
        self,
        probe: ProbeResult,
        source_url: str,
        val: ValidationResult,
        report: DownloadReport
    ) -> DownloadReport:
        report.selected_source = source_url
        report.chapter_count = len(probe.chapters)

        # 启动平稳并发抓取
        chapters_content, failed_cnt = ConcurrentDownloader.download_all(
            chapters=probe.chapters,
            downloader_func=probe.downloader_func,
            max_workers=self.concurrency,
            verbose=True
        )

        report.failed_chapters = failed_cnt

        # 产物完整性与健康度校验 (Post-Download Validation)
        post_res = PostDownloadValidator.validate(chapters_content)
        report.post_validation = post_res

        # 写入导出文件
        out_path = TxtExporter.export(
            novel_name=self.novel_name,
            chapters=chapters_content,
            output_dir=self.output_dir,
            author=probe.author or self.author,
            source_url=source_url
        )
        report.output_file = out_path

        # 最终状态语义判定
        if not val.is_qualified:
            # 即使开启 allow_low_quality 并下载了 100% 章节，也绝不能标记为 SUCCESS
            report.status = DownloadStatus.LOW_QUALITY
        elif len(chapters_content) == 0 or (len(chapters_content) == failed_cnt):
            report.status = DownloadStatus.DOWNLOAD_FAILED
            report.failures.append(FailureRecord(
                stage="download",
                target=source_url,
                reason="章节正文全部抓取失败"
            ))
        elif not post_res.is_valid:
            report.status = DownloadStatus.PARTIAL
            report.failures.append(FailureRecord(
                stage="post_validation",
                target=out_path,
                reason=f"产物验收不合格: {'; '.join(post_res.reasons)}"
            ))
        elif failed_cnt == 0 or (failed_cnt / float(len(probe.chapters))) <= 0.10:
            report.status = DownloadStatus.SUCCESS
        else:
            report.status = DownloadStatus.PARTIAL

        return report
