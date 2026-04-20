# doc2md-crawl4ai

> 🚀 一个强大的文档爬取工具，将在线文档站转换为本地 Markdown 文件

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ 特性

- 🌐 **智能网页发现**：自动发现同域文档页面，支持导航树递归和链接 BFS
- 🤖 **AI 驱动**：基于 Crawl4AI，支持动态页面渲染和智能内容提取
- 📝 **Markdown 输出**：自动转换为格式清晰的 Markdown 文档
- 🔄 **多种爬取模式**：HTTP、Playwright 浏览器渲染、自动模式
- 🎯 **精准控制**：支持正则过滤、并发控制、延迟设置
- 🖥️ **Web 界面**：提供友好的 Web UI（可选）
- 📦 **本地优先**：所有数据存储在本地数据库，支持导出

## 🎯 适用场景

- 将小众框架/SDK文档站离线化
- 为 AI 总结/检索/RAG 准备语料
- 技术文档备份和归档
- 知识库建设和维护

## 📦 安装

### 环境要求

- Python 3.10+（推荐 3.11）
- Node.js 18+（仅 Web UI 需要）
- MySQL 8.0+（仅 Web UI 需要）

### 命令行工具安装

```bash
# 克隆项目
git clone https://github.com/yourusername/doc2md-crawl4ai.git
cd doc2md-crawl4ai

# 安装 Python 依赖
pip install -r requirements.txt
```

### Web UI 安装（可选）

```bash
# 安装前端依赖
cd webapp/frontend
npm install

# 配置环境变量
cp ../../.env.example ../../.env
# 编辑 .env 文件，配置数据库等信息

# 启动后端（项目根目录）
cd ../..
PYTHONPATH=$(pwd) python3.11 -m uvicorn webapp.backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端（新终端）
cd webapp/frontend
npm run dev
```

访问 http://localhost:5174 即可使用 Web UI。

## 🚀 快速开始

### 命令行模式

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
  --start-url "https://example.com/docs" \
  --out "./output" \
  --engine playwright \
  --max-pages 100 \
  --delay 0.5 \
  --include "^https://example.com/docs" \
  --exclude "api/legacy"

# 合并为单个 Markdown 文档
python -m doc2md_crawl4ai bundle \
  --in "./output" \
  --out "./output/merged.md" \
  --doc-title "My Documentation"
```

### Web UI 模式

1. 访问 http://localhost:5174
2. 注册或登录
3. 输入文档站 URL
4. 配置爬取参数
5. 开始爬取
6. 查看和下载结果

## ⚙️ 配置说明

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--start-url` | 起始 URL | 必填 |
| `--out` | 输出目录 | `./output` |
| `--max-pages` | 最大页面数 | 50 |
| `--concurrency` | 并发数 | 6 |
| `--delay` | 请求延迟（秒） | 0 |
| `--engine` | 爬取引擎 | `auto` |
| `--scope` | 抓取范围 | `same_origin` |
| `--include` | URL 包含正则 | 无 |
| `--exclude` | URL 排除正则 | 无 |
| `--main-selector` | 主内容选择器 | 无 |

### Web UI 配置

在 `.env` 文件中配置：

```env
# 应用配置
APP_SECRET_KEY=your-secret-key
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/doc2md?charset=utf8mb4

# 七牛云配置（可选）
QINIU_ENABLED=false
QINIU_ACCESS_KEY=your-access-key
QINIU_SECRET_KEY=your-secret-key
QINIU_BUCKET=your-bucket
QINIU_PUBLIC_DOMAIN=https://your-cdn-domain.com/
```

## 🏗️ 项目结构

```
doc2md_crawl4ai/
├── doc2md_crawl4ai/      # 核心爬虫模块
│   ├── __init__.py
│   ├── cli.py            # 命令行入口
│   ├── crawler.py        # 爬虫引擎
│   ├── discovery.py      # URL 发现
│   └── writer.py         # Markdown 写入
├── webapp/               # Web 应用
│   ├── backend/          # FastAPI 后端
│   │   └── app/
│   │       ├── main.py   # API 入口
│   │       ├── models.py # 数据模型
│   │       ├── schemas.py # Pydantic 模型
│   │       └── ...
│   └── frontend/         # React 前端
│       └── src/
├── requirements.txt      # Python 依赖
└── README.md
```

## 🛠️ 开发指南

### 本地开发

```bash
# 后端开发
cd webapp/backend
PYTHONPATH=$(pwd)/../.. python3.11 -m uvicorn app.main:app --reload

# 前端开发
cd webapp/frontend
npm run dev

# 运行测试
python -m pytest tests/
```

### 代码规范

- Python：遵循 PEP 8
- 前端：使用 ESLint + Prettier
- 提交前运行 `black .` 格式化代码

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎贡献！请随时提交 Issue 或 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## ⚠️ 免责声明

请确保你有权限抓取目标站点，并遵守 robots.txt 和网站使用条款。对公共站点建议：
- 设置较低的并发数
- 添加适当的延迟
- 遵守网站的爬取政策

## 📮 联系方式

- 作者：Your Name
- 项目链接：[https://github.com/yourusername/doc2md-crawl4ai](https://github.com/yourusername/doc2md-crawl4ai)

## 🙏 致谢

- [Crawl4AI](https://github.com/unclecode/crawl4ai) - 强大的 LLM 友好网页爬取工具
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [React](https://react.dev/) - 用户界面库
