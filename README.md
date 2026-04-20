# doc2md-crawl4ai

> 基于 Crawl4AI 的智能文档爬取工具，将在线文档站转换为本地 Markdown 文件

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📖 项目简介

`doc2md-crawl4ai` 提供两种使用方式：

### 1️⃣ 命令行工具 (CLI)
- ✅ 轻量级，无需数据库
- ✅ 适合一次性任务和脚本自动化
- ✅ 支持批量爬取和文档合并

### 2️⃣ Web 管理台
- ✅ 可视化界面，易于使用
- ✅ 支持任务管理和历史记录
- ✅ 实时预览和在线搜索
- ✅ 支持多用户和云存储

---

## ✨ 特性

- 🌐 **智能页面发现**：自动发现同域文档页面，支持导航树递归和 BFS 遍历
- 🤖 **AI 驱动**：基于 [Crawl4AI](https://github.com/unclecode/crawl4ai)，支持动态页面渲染
- 📝 **Markdown 转换**：自动转换为格式清晰的 Markdown，支持内容去噪
- 🔄 **多种爬取模式**：HTTP 轻量模式、Playwright 浏览器渲染、自动回退
- 🎯 **精准控制**：支持正则过滤、并发控制、CSS 选择器、延迟设置
- 📦 **文档合并**：支持将多个页面合并为单个 Markdown 文件
- ☁️ **云存储集成**：Web UI 支持七牛云上传（可选）

## 🎯 适用场景

- 📚 将在线技术文档离线化（API 文档、框架文档等）
- 🤖 为 AI 总结/检索/RAG 准备高质量语料
- 💾 技术文档备份和归档
- 📖 知识库建设和维护

---

## 📦 安装

### 环境要求

**CLI 模式**:
- Python 3.10+ （推荐 3.11）

**Web UI 模式**:
- Python 3.10+
- Node.js 18+
- MySQL 8.0+ 或 SQLite

### 基础安装（两种模式都需要）

```bash
# 克隆项目
git clone https://github.com/xuzihaojoe/doc2md_crawl4ai.git
cd doc2md_crawl4ai

# 安装 Python 依赖
pip install -r requirements.txt
```

---

## 🚀 使用方式

### 方式一：命令行工具 (CLI)

CLI 模式无需额外配置，安装完成后直接使用。

#### 基础爬取

```bash
python -m doc2md_crawl4ai crawl \
  --start-url "https://docs.crawl4ai.com/" \
  --out "./output" \
  --max-pages 50 \
  --concurrency 6
```

#### 高级选项

```bash
# 使用浏览器渲染（处理动态页面）
python -m doc2md_crawl4ai crawl \
  --start-url "https://example.com/docs/" \
  --out "./output" \
  --engine playwright \
  --max-pages 100 \
  --delay 0.5 \
  --scope same_domain \
  --include "^https://example.com/docs" \
  --exclude "api/legacy"

# 指定主内容选择器（提取特定区域）
python -m doc2md_crawl4ai crawl \
  --start-url "https://docs.example.com/" \
  --out "./output" \
  --main-selector "main" \
  --ignore-links

# 只爬取单页（URL 不以 / 结尾）
python -m doc2md_crawl4ai crawl \
  --start-url "https://example.com/page.html" \
  --out "./output"
```

#### 文档合并

```bash
# 将爬取的多个页面合并为单个 Markdown 文件
python -m doc2md_crawl4ai bundle \
  --in "./output" \
  --out "./output/merged.md" \
  --doc-title "技术文档合集" \
  --title-mode breadcrumb
```

#### CLI 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--start-url` | 起始 URL | 必填 |
| `--out` | 输出目录 | `./output` |
| `--max-pages` | 最大页面数 | 200 |
| `--concurrency` | 并发数 | 6 |
| `--delay` | 请求延迟（秒） | 0 |
| `--engine` | 爬取引擎 (auto/playwright/http) | `auto` |
| `--scope` | 抓取范围 (same_origin/same_domain) | `same_origin` |
| `--include` | URL 包含正则 | 无 |
| `--exclude` | URL 排除正则 | 无 |
| `--main-selector` | CSS 主内容选择器 | 无 |
| `--ignore-links` | 忽略超链接 | false |
| `--verbose` | 详细日志 | false |

#### 查看帮助

```bash
# 查看所有命令
python -m doc2md_crawl4ai --help

# 查看 crawl 命令帮助
python -m doc2md_crawl4ai crawl --help

# 查看 bundle 命令帮助
python -m doc2md_crawl4ai bundle --help
```

#### CLI 输出示例

```
output/
├── index.md                           # 总索引
├── docs.example.com/                  # 按域名分组
│   ├── core/
│   │   ├── quickstart/
│   │   │   └── index.md              # 页面内容
│   │   └── advanced/
│   │       └── index.md
│   └── api/
│       └── reference/
│           └── index.md
└── merged.md                          # 合并后的文档（如果使用 bundle）
```

---

### 方式二：Web 管理台

Web UI 提供可视化界面，需要额外的安装步骤。

#### 1. 安装前端依赖

```bash
cd webapp/frontend
npm install
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp ../../.env.example ../../.env

# 编辑 .env 文件
nano ../../.env  # 或使用你喜欢的编辑器
```

在 `.env` 文件中配置：

```env
# 应用配置
APP_SECRET_KEY=your-secret-key-here  # 修改为随机字符串
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# 数据库配置（选择一种）

# 方式 A: MySQL
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/doc2md?charset=utf8mb4

# 方式 B: SQLite（开发环境推荐，无需额外配置）
# DATABASE_URL=sqlite:///./dev.db

# 七牛云配置（可选，不使用可以忽略）
QINIU_ENABLED=false
```

#### 3. 创建数据库

**使用 MySQL**:

```bash
mysql -u root -p
CREATE DATABASE doc2md CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

**使用 SQLite**: 无需创建，会自动生成。

#### 4. 初始化数据库表结构

```bash
cd ../..
python init_db.py
```

这将创建以下数据表：
- `users` - 用户表
- `crawl_jobs` - 爬取任务表
- `documents` - 文档表

#### 5. （可选）创建管理员用户

```bash
python init_db.py --create-admin --admin-username admin --admin-password your_password
```

#### 6. 启动服务

**启动后端**（终端 1）:

```bash
# 项目根目录
PYTHONPATH=$(pwd) python -m uvicorn webapp.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**启动前端**（终端 2）:

```bash
cd webapp/frontend
npm run dev
```

#### 7. 访问应用

打开浏览器访问: **http://localhost:5173**

#### Web UI 功能说明

**URL 格式规则**:
- **以 `/` 结尾**：抓取该目录下的所有子页面
  - 例如：`https://doc.dcloud.net.cn/uni-app-x/uts/` 会抓取 `/uts/` 目录下的文档
- **不以 `/` 结尾**：只抓取当前单页
  - 例如：`https://example.com/page.html` 只抓这一个页面

**功能特性**:
- 📋 **任务管理**：创建、查看、删除爬取任务
- 📄 **文档预览**：实时查看 Markdown 渲染效果
- 📥 **下载导出**：支持单页下载和任务打包下载
- 🔍 **搜索过滤**：快速定位任务和文档
- 👤 **用户系统**：支持注册登录，数据隔离
- ☁️ **云存储**：支持七牛云上传（需配置）

---

## 🏗️ 项目结构

```
doc2md_crawl4ai/
├── doc2md_crawl4ai/           # CLI 核心模块
│   ├── __init__.py
│   ├── cli.py                 # 命令行入口
│   ├── crawler.py             # 爬虫引擎
│   ├── discovery.py           # URL 发现
│   └── writer.py              # Markdown 写入
├── webapp/                    # Web UI 应用
│   ├── backend/               # FastAPI 后端
│   │   └── app/
│   │       ├── main.py        # API 入口
│   │       ├── models.py      # 数据模型
│   │       ├── schemas.py     # Pydantic 模型
│   │       ├── crawler_runner.py  # 爬虫执行器
│   │       ├── db.py          # 数据库配置
│   │       └── ...
│   └── frontend/              # React 前端
│       ├── src/
│       │   ├── App.tsx        # 主应用组件
│       │   ├── api.ts         # API 客户端
│       │   └── main.tsx       # 入口文件
│       ├── package.json
│       └── vite.config.ts
├── init_db.py                 # 数据库初始化脚本
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量示例
├── DATABASE.md                # 数据库文档
└── README.md
```

---

## 🛠️ 开发指南

### CLI 开发

```bash
# 运行 CLI
python -m doc2md_crawl4ai crawl --help

# 测试爬取
python -m doc2md_crawl4ai crawl --start-url "https://example.com" --out "./test"
```

### Web UI 开发

```bash
# 后端开发（带热重载）
PYTHONPATH=$(pwd) python -m uvicorn webapp.backend.app.main:app --reload

# 前端开发（带热重载）
cd webapp/frontend && npm run dev
```

### 构建前端

```bash
cd webapp/frontend
npm run build
```

构建产物位于 `webapp/frontend/dist/`，可由 FastAPI 静态文件服务提供。

---

## 📚 更多文档

- **[DATABASE.md](DATABASE.md)** - 数据库结构详细说明
- **[.env.example](.env.example)** - 环境变量配置示例

---

## ⚠️ 注意事项

1. **爬取礼仪**：请遵守目标网站的 robots.txt 和使用条款
2. **并发控制**：建议设置较低的并发数和适当的延迟
3. **动态页面**：遇到 JavaScript 渲染的页面，使用 `--engine playwright`
4. **内容过滤**：使用 `--main-selector` 可以提高提取精度

---

## 🤝 贡献

欢迎贡献！请随时提交 Issue 或 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Crawl4AI](https://github.com/unclecode/crawl4ai) - 强大的 LLM 友好网页爬取工具
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [Ant Design](https://ant.design/) - React UI 组件库

---

**作者**: xuzihaojoe

**项目链接**: [https://github.com/xuzihaojoe/doc2md_crawl4ai](https://github.com/xuzihaojoe/doc2md_crawl4ai)

**⭐ 如果这个项目对你有帮助，请给个 Star！**
