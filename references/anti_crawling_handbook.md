# 小说站点反爬与混淆破解手册

本文档汇总了主流中文成人向/武侠小说聚合站的反爬机制与逆向还原方案。

---

### 1. 海马读书网 (`haimashu.com`)
- **反爬手段**：
  1. 目录 Base64 混淆：`<a>` 标签使用 `data-cocf2c99="L2Jvb2svNDg4NC8xNDI3ODYuaHRtbA=="` 隐藏真实 URL，需 Base64 解码。
  2. 真实章节名在 `data-co3ff514="分卷阅读X"` 中，静态文案故意显示为乱序的 `Chapter 01`。
  3. 正文采用 AES-128-CBC 加密，调用 `$('#id').html(d(ciphertext, key_str))`。
  4. 正文中夹杂大量零宽字符（`\u200b`, `\u00ad` 等）防止分词与拷贝。
- **解密算法**：
  ```python
  md5 = hashlib.md5(key_str.encode()).hexdigest()
  iv = md5[:16].encode()
  key = md5[16:].encode()
  cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
  decrypted = cipher.decryptor().update(b64decode(cipher_b64))
  ```

---

### 2. 八叉书库 (`8xsk.com` / `bachashuku.org`)
- **反爬手段**：
  1. 18+ 年龄拦截：全站强制跳转到年龄确认页面。
  2. 正文外层混淆：正文包裹在 `<script>` 内，通过 `document.getElementById("content").innerHTML=decodeURIComponent(escape(atob("...")))` 渲染。
- **破解方案**：
  1. 请求头直接带 Cookie：`age18_ok=1; jieqiVisitId=article_articleviews%3D{bid}` 即可绕过。
  2. 使用正则提取 `atob("...")` 中的字符串，使用 Base64 解码获得纯正文。
  3. 目录分页需遍历 `book/{id}_{page}.html`。

---

### 3. 第一版主网 (`111bz.cc` / `diyibanzhu`)
- **反爬手段**：
  1. PC 端隐藏正文，提示跳转移动端。
  2. 单章节长文拆分为多个子页（如 `140971.html`, `140971_2.html`, `140971_3.html`）。
- **破解方案**：
  1. 从 PC 端目录解析全量章节入口。
  2. 将 URL 映射为移动端 `http://m.111bz.cc/...`。
  3. 循环判断是否存在 `下一页`（链接以 `_X.html` 结尾），自动将所有子分页内容连贯拼接为完整章节。

---

### 4. 笔趣阁/辣文库 (`aakkcc.com` / `aaddkk.com`)
- **结构特点**：
  - 标准 CMS 静态渲染，章节 ID 连续递增。
  - 正文位于 `div#content` 中，注意清洗广告特征文本（如 `请记住本书首发域名`）。

---

### 5. 新笔趣阁 / Nuxt SSR (如《陈皮皮的斗争》)
- **反爬手段**：
  1. 康熙字典部首替换：如用 `\u2f6a`（康熙部首皮）代替汉字 `皮`。
  2. RTL 字符倒置：插入 `\u202e` 使文字在前端视觉倒排。
- **破解方案**：
  1. 使用 `unicodedata.normalize('NFKC', text)` 还原康熙部首至标准汉字。
  2. 对带 `\u202e` 的文本切片做倒序翻转修复。

---

### 6. 搜索引擎防二次验证规约 (Anti-Verification Search Policy)

- **为什么必须废弃 Yandex 直链导航？**
  - Yandex 对非俄区住宅 IP（尤其是数据中心代理）检测极其严格。
  - 直接携带中文关键词跳转 `yandex.ru/search?text=...` 会触发底层的 `SmartCaptcha` 进阶交互（俄文字符顺序点击题库），极其消耗精力。
- **两级免验证搜索引擎替代方案**：
  1. **DuckDuckGo Lite HTTP API (`lite.duckduckgo.com/lite/`)**：
     - 使用纯 HTTP 表单 POST 提交，不加载 JavaScript，不向反爬联盟提供设备指纹，**100% 不会弹出验证码**。
  2. **本地 Chrome 驱动 Google 引擎 (`google.com`)**：
     - 利用本地已授权的 Chrome 浏览器（通过 OpenCLI 连通）。
     - Google 在正常浏览器环境内享有正常用户信誉，搜索中文小说目录不会弹窗阻断。
