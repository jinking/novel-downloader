# Novel Downloader (小说全网智能嗅探精校下载引擎 V2.1)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-V2.1%20Decoupled-brightgreen.svg)]()

全自动全网小说嗅探、逆向解密、多维质量验收、产物完整度核验、多源故障转移与纯净全本精校 TXT 生成引擎。

通过多搜索引擎（Google、Yandex、DuckDuckGo 及内置专用源池）、候选池去重排序、通用自适应解析器与前后双重质量验收器，尽可能提高公开可访问小说来源的发现与下载成功率；当未达到严格质量阈值时，明确返回失败或低质量诊断状态，绝不以残次内容冒充成功。

---

## 🌟 核心架构与多层闭环

```
用户输入: 书名 / --author [作者] / --url [直连目录] / --allow-low-quality
  │
  ├──► [直连模式] 若指定 --url: 跳过搜索，直达解析与质量校验层
  │
  └──► [多搜索引擎发现层 (Discovery)]
         ├── 内置专用源池 (BuiltinProvider: 海马 AES-CBC / 八叉 Base64 / 小说狂人等)
         ├── 全网主流搜索引擎 (Google Provider)
         ├── 独立索引补充 (Yandex Provider，独立异常隔离)
         └── 轻量免验证表单引擎 (DuckDuckGo Lite)
         └──► 候选 URL 池 (CandidatePool: 统一入口、URL归一化、去追踪参数、置信加权)
  │
  ├──► [解析与路由分发层 (Parser Router)]
  │      ├── 专用站点适配器 (海马 AES 解密、八叉 Base64 还原、移动端连贯子分页等)
  │      └── 通用自适应解析器 (UniversalParser: 目录容器定位、目录页跃迁、正文字符密度提取)
  │
  ├──► [多维质量验收器 (SourceValidator)] 严格准入门槛
  │      ├── 身份吻合度 (30%): 书名与作者元信息严格交叉比对
  │      ├── 目录健康度 (20%): 章节量级、重复率及正规章节格式率 (严防伪目录与推荐书单)
  │      ├── 5 点正文抽样 (30%): 首章/25%/50%/75%/尾章均长检验与截断/防盗词排查
  │      ├── 完本特征 (15%): 终章/大结局特征判定
  │      └── 发现置信度 (5%)
  │
  ├──► [综合排序与故障转移 (SourceRanker & Failover)]
  │      ├── 锁定通过校验的合格源 (is_qualified == True 且质量分优先)
  │      ├── 若合格源不足: 自动由 qualified source 数量驱动 Deep Discovery 深度兜底
  │      └── 故障转移: 若首选源遭遇突发限流 (403/503)，自动平滑切换至备选达标源
  │
  ├──► [平稳并发抓取流水线 (Downloader)]
  │      ├── 自适应并发控制 (内置随机 Jitter 防风控)
  │      └── 丢包快速并发补漏重试 (确保零空章)
  │
  └──► [产物校验与导出层 (PostDownloadValidator & Exporter)]
         ├── 产物质量核验: 校验全书缺章率、有效章节均长与短章比例
         ├── 严格状态判定:
         │     ├── 来源合格 + 抓取完整 + 产物合格 = SUCCESS (exit 0)
         │     ├── 抓取缺章超限 = PARTIAL (exit 1)
         │     └── 未达质量阈值 = LOW_QUALITY (即使强制下载也绝不标 SUCCESS, exit 1)
         └── 纯净全本 TXT 规范组装落盘
```

---

## 🛠️ 安装与快速上手

### 环境要求
- Python 3.9+
- 推荐开启系统代理以确保海外 CDN 镜像站点畅通

### 1. 安装依赖
```bash
git clone https://github.com/jinking/novel-downloader.git
cd novel-downloader
pip install -r requirements.txt
pip install -e .
```

---

### 2. 常用执行命令

#### 基础用法（全网自动发现与优选）
```bash
python3 scripts/download.py "诛仙"
```

#### 作者联合高精度匹配（推荐）
```bash
python3 scripts/download.py "诛仙" --author "萧鼎"
```

#### 手动直连目录 URL 模式（跳过搜索）
```bash
python3 scripts/download.py "诛仙" --url "https://www.wyshu.com/wl/zhuxian"
```

#### 允许下载最佳低质量源（明确不标记为 SUCCESS）
```bash
python3 scripts/download.py "某冷门古籍" --allow-low-quality
```

#### JSON 诊断格式输出（便于 Agent 或外部脚本集成）
```bash
python3 scripts/download.py "诛仙" --author "萧鼎" --json
```

---

## 🚦 状态机与语义说明

| 最终状态 (`status`) | 退出码 | 业务含义 |
| :--- | :---: | :--- |
| `SUCCESS` | `0` | 来源通过 `SourceValidator` 且产物通过 `PostDownloadValidator`，全本完整 |
| `PARTIAL` | `1` | 来源合格，但抓取过程中存在部分章节丢失或产物缺章率超限 |
| `LOW_QUALITY` | `1` | 候选源未通过质量验收（如正文截断、假目录等）；若开启 `--allow-low-quality` 仍为该状态 |
| `UNPARSABLE` | `1` | 页面可访问但所有候选页面均无法识别并解析出有效小说目录 |
| `UNREACHABLE` | `1` | 搜索命中的候选站点均网络不可达或拒绝连接 |
| `NOT_FOUND` | `1` | 所有搜索引擎均未检索到任何相关候选网页 |
| `DOWNLOAD_FAILED`| `1` | 章节正文抓取 100% 失败 |

---

## 🧪 自动化测试套件

项目包含完整的自动化单元测试与集成测试（基于 `pytest`）：

```bash
pytest tests/ -v
```

测试覆盖范围：
- `tests/discovery/`: Yandex 单点异常隔离、Google/DDG/Builtin 多源候选池合并与去重。
- `tests/ranking/`: 质量达标源优先于章节数量多但残缺的低质量源。
- `tests/validation/`: 伪目录/推荐书单拦截、截断正文剔除、下载后产物完整性核验（PostDownloadValidator）。
- `tests/integration/`: 涵盖伪兜底纠正、全低质拦截、显式低质下载状态语义、严重缺章 PARTIAL 及完整 SUCCESS 流程。

---

## 🤖 接入 AI Agent / Antigravity / Claude Code

已原生封装为智能体 Agent Skill 规格：

1. 软链或拷贝至 Skill 目录：
   ```bash
   ln -s /path/to/novel-downloader ~/.gemini/config/skills/novel-downloader
   ```
2. 在 Agent 对话中下达指令：
   > “帮我下载《诛仙》，作者是萧鼎”
   > “使用 JSON 格式下载这篇小说并报告质量诊断：https://www.wyshu.com/wl/zhuxian”
3. Agent 将按数据契约解析返回的 `selected_source_score`、`selected_source_qualified` 及 `post_validation` 状态。

---

## ⚖️ 开源协议与免责声明

- 本项目基于 **[MIT License](LICENSE)** 开源。
- 本项目代码仅供网络数据抓取、信息检索技术学习与逆向工程安全研究之用。所爬取的小说内容版权均归原作者及版权方所有，请在下载后 24 小时内删除，严禁用于商业牟利或侵权传播。
