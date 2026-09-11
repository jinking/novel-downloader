# Novel Downloader (小说全网嗅探精校下载器)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)]()

全自动全网小说嗅探、逆向解密、防验证码多级调度与全本纯净精校 TXT 生成工具。

无论是知名网文大作（如《全职高手》全千章），还是各类被强反爬、混淆加密、防盗截断保护的小说（如风月经典、武侠、短篇），仅需输入书名，即可实现一键检索、解密、下载并拼接为规范精校全集。同时无缝兼容作为 **Agent 智能体专属技能（Skill）** 直接调用。

---

## 🌟 核心特性与架构

```
用户输入《书名》
  │
  ├──► [Level 1] 内置专用源池直查（0 验证码、纯本地解密、毫秒级命中）
  │      ├── 海马读书 (AES-128-CBC 动态密钥注入逆向 + 零宽字符清洗)
  │      ├── 八叉书库 (18+ Cookie 拦截绕过 + Base64 atob() 混淆还原)
  │      ├── 第一版主 (移动端 m.111bz 子分页递归嗅探与无缝连贯拼接)
  │      ├── 辣文/笔趣阁镜像 (连续数字 ID 聚合与反垃圾过滤)
  │      └── 小说狂人 (繁简对齐规范)
  │      └─► 命中即直接进入高并发抓取
  │
  └──► [Level 2] 未命中时：免二次验证搜索引擎回退 (Zero-Captcha Fallback)
         │  采用 DuckDuckGo Lite 纯 HTTP 表单协议
         │  原理：无 JavaScript 渲染环境，无反爬指纹追踪，100% 免疫 CAPTCHA 拦截
         │  自动黑名单过滤起点、创世、爱奇艺文学等官方付费截断站点
         │
         ├──► [Level 3] 兜底：本地受信任 Chrome Google 会话 (可选通过 OpenCLI)
         │      复用日常 Chrome 浏览器的真实用户指纹与 Cookies，绝不走易风控的 Yandex
         │
         └──► [通用自适应解析器 (Universal Adaptive Parser)]
                ├── 自动目录容器定位 (识别 div#list, div.dir, dl dd 等结构)
                ├── 书籍信息页智能跃迁 (自动探测并跟进「查看全部章节」链接)
                ├── 正文有效性抽样校验 (抽样均长 <400 字自动识别假站/重定向并丢弃)
                └── 30 线程高并发流水线 (1700+ 章长篇小说 40 秒全量落盘)
```

### 1. 彻底解决搜索引擎二次验证（CAPTCHA）
传统脚本使用无头浏览器请求 Yandex、Google 等引擎时，由于缺少本地环境指纹与用户鼠标微动作，极易被标记为 Bot 并强制弹出字符点选验证码（如 Yandex SmartCaptcha）。
本项目采用：
- **专用库直查优先**：优先走内置的无验证码逆向专用源站。
- **纯 HTTP 表单引擎（DuckDuckGo Lite）**：无 JS 引擎、无追踪 SDK，1 秒返回结果，绝对零验证码。
- **正文质量抽样机制**：自动识破 302 劫持与截断试读站点，保障全本真实饱满。

### 2. 深度逆向反爬技术覆盖
- **AES-128-CBC 动态解密**：逆向提取 Webpack 打包的混淆密文与动态生成的 IV / Key。
- **隐式零宽字符净化**：自动剔除 `\u200b`, `\u00ad`, `\ufeff` 等水印字符。
- **双向排版与字典映射修复**：修复 RTL（BiDi）字符颠倒及 Unicode 康熙字典偏旁部首置换。

---

## 🚀 快速上手

### 环境要求
- Python 3.9+

### 1. 安装依赖
```bash
git clone https://github.com/jinking/novel-downloader.git
cd novel-downloader
pip install -r requirements.txt
```

或者本地以可编辑方式安装 CLI：
```bash
pip install -e .
```

### 2. 运行下载

**直接使用脚本：**
```bash
python3 scripts/download.py "全职高手"
```

**指定保存目录：**
```bash
python3 scripts/download.py "全职高手" --output-dir "./my_books"
```

**若已执行 `pip install -e .`，可直接使用全局命令：**
```bash
novel-dl "全职高手"
```

生成的文件将自动保存在指定目录下（默认为 `./downloads/<书名>.txt`）。

---

## 🤖 接入 AI Agent / Antigravity / Claude Code

本项目开箱支持作为智能体专属 Skill 使用：

1. 将本项目目录软链或拷贝至 Skill 根目录：
   ```bash
   ln -s /path/to/novel-downloader ~/.gemini/config/skills/novel-downloader
   ```
2. 在任意 Agent 对话中输入：
   > “帮我下载《全职高手》”
3. Agent 将自动调用该技能，在后台执行多级探测、逆向解密、章节补全与全本写入。

---

## 📂 目录结构

```
novel-downloader/
├── README.md               # 项目主说明文档
├── LICENSE                 # MIT 开源协议
├── requirements.txt        # 依赖列表 (beautifulsoup4, cryptography)
├── pyproject.toml          # 打包与 CLI 配置
├── SKILL.md                # Agent Skill 规范定义文件
├── scripts/
│   └── download.py         # 核心可独立执行 CLI 脚本
├── novel_downloader/       # 模块化 Python 包代码
│   ├── __init__.py
│   └── cli.py
├── references/
│   └── anti_crawling_handbook.md # 逆向与反爬虫分析手册
└── downloads/              # 小说导出默认存放目录
```

---

## 📖 技术文档

详细的网站逆向工程与防爬对抗经验见：[逆向与反爬分析技术手册 (anti_crawling_handbook.md)](references/anti_crawling_handbook.md)。

---

## ⚖️ 开源协议与免责声明

- 本项目基于 **[MIT License](LICENSE)** 开源。
- 本项目代码仅供网络爬虫技术学习与逆向工程安全研究之用。所爬取的小说内容版权均归原作者及版权方所有，请在下载后 24 小时内删除，严禁用于商业牟利或侵权传播。
