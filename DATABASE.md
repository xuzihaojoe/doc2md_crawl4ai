# 数据库结构说明

本文档详细说明了 `doc2md-crawl4ai` Web UI 所使用的数据库结构。

## 📊 数据库概览

项目使用关系型数据库存储用户、爬取任务和文档数据。支持 MySQL 和 SQLite。

### 数据库表

- **users** - 用户表
- **crawl_jobs** - 爬取任务表
- **documents** - 文档表

## 📋 表结构详解

### 1. users（用户表）

存储用户认证信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | Integer | 主键 | PRIMARY KEY, AUTO_INCREMENT |
| `username` | String(64) | 用户名 | NOT NULL, UNIQUE, INDEX |
| `password_hash` | String(255) | 密码哈希（bcrypt） | NOT NULL |
| `created_at` | DateTime | 创建时间 | NOT NULL |

**关系**:
- 一个用户可以拥有多个爬取任务（`crawl_jobs`）

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_username (username)
);
```

---

### 2. crawl_jobs（爬取任务表）

存储爬取任务的信息和配置参数。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | String(36) | 任务ID（UUID） | PRIMARY KEY |
| `name` | String(255) | 任务名称 | NOT NULL |
| `start_url` | Text | 起始URL | NOT NULL |
| `status` | String(24) | 任务状态 | NOT NULL, DEFAULT 'pending' |
| `error` | Text | 错误信息 | NULLABLE |
| `max_pages` | Integer | 最大页面数 | DEFAULT 200 |
| `concurrency` | Integer | 并发数 | DEFAULT 6 |
| `delay` | Float | 请求延迟（秒） | DEFAULT 0.2 |
| `engine` | String(24) | 爬取引擎 | DEFAULT 'http' |
| `scope` | String(24) | 抓取范围 | DEFAULT 'same_origin' |
| `include` | Text | 包含正则 | NULLABLE |
| `exclude` | Text | 排除正则 | NULLABLE |
| `user_id` | Integer | 用户ID（外键） | INDEX, NULLABLE |
| `anon_id` | String(64) | 匿名会话ID | INDEX, NULLABLE |
| `created_at` | DateTime | 创建时间 | NOT NULL |
| `finished_at` | DateTime | 完成时间 | NULLABLE |

**状态值**:
- `pending` - 等待执行
- `running` - 正在执行
- `succeeded` - 执行成功
- `failed` - 执行失败

**引擎值**:
- `http` - HTTP 轻量模式
- `playwright` - 浏览器渲染模式
- `auto` - 自动模式（优先 playwright，失败回退 http）

**关系**:
- 属于一个用户（`users`），可为空（匿名任务）
- 包含多个文档（`documents`）

```sql
CREATE TABLE crawl_jobs (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    start_url TEXT NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'pending',
    error TEXT,
    max_pages INT NOT NULL DEFAULT 200,
    concurrency INT NOT NULL DEFAULT 6,
    delay FLOAT NOT NULL DEFAULT 0.2,
    engine VARCHAR(24) NOT NULL DEFAULT 'http',
    scope VARCHAR(24) NOT NULL DEFAULT 'same_origin',
    include TEXT,
    exclude TEXT,
    user_id INT,
    anon_id VARCHAR(64),
    created_at DATETIME NOT NULL,
    finished_at DATETIME,
    INDEX idx_user_id (user_id),
    INDEX idx_anon_id (anon_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

---

### 3. documents（文档表）

存储爬取的 Markdown 文档内容。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | Integer | 主键 | PRIMARY KEY, AUTO_INCREMENT |
| `job_id` | String(36) | 任务ID（外键） | INDEX, NOT NULL |
| `title` | String(255) | 文档标题 | NOT NULL |
| `url` | Text | 来源URL | NOT NULL |
| `doc_index` | Integer | 文档索引 | DEFAULT 0 |
| `is_merged` | Boolean | 是否为合并文档 | DEFAULT false |
| `markdown_text` | LONGTEXT | Markdown内容 | NOT NULL |
| `qiniu_key` | String(512) | 七牛云Key | NULLABLE |
| `qiniu_url` | String(1024) | 七牛云URL | NULLABLE |
| `created_at` | DateTime | 创建时间 | NOT NULL |

**字段说明**:
- `is_merged` - 标识是否为合并文档（将多个页面合并为一个 Markdown）
- `markdown_text` - 使用 MySQL 的 LONGTEXT 类型，最大存储 4GB
- `qiniu_key` / `qiniu_url` - 如果启用了七牛云存储，文档会同步到云端

**关系**:
- 属于一个爬取任务（`crawl_jobs`）

```sql
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    doc_index INT NOT NULL DEFAULT 0,
    is_merged BOOLEAN NOT NULL DEFAULT false,
    markdown_text LONGTEXT NOT NULL,
    qiniu_key VARCHAR(512),
    qiniu_url VARCHAR(1024),
    created_at DATETIME NOT NULL,
    INDEX idx_job_id (job_id),
    FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE
);
```

---

## 🔄 ER 图

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│    users    │1       N│ crawl_jobs  │1       N│  documents  │
├─────────────┤         ├─────────────┤         ├─────────────┤
│ id          │──┐   ┌──│ id          │──┐   ┌──│ id          │
│ username    │  │   │  │ name        │  │   │  │ title       │
│ password... │  │   │  │ start_url   │  │   │  │ url         │
│ created_at  │  │   │  │ status      │  │   │  │ markdown... │
└─────────────┘  │   │  │ ...         │  │   │  │ ...         │
                 │   │  └─────────────┘  │   │  └─────────────┘
                 │   │                   │   │
                 │   └───────────────────┘   │
                 └───────────────────────────┘
```

---

## 🚀 初始化数据库

### 方法 1：使用初始化脚本（推荐）

```bash
# 1. 配置 .env 文件
cp .env.example .env
# 编辑 .env，设置 DATABASE_URL

# 2. 运行初始化脚本
python init_db.py

# 3. （可选）创建管理员用户
python init_db.py --create-admin
```

### 方法 2：手动创建 MySQL 数据库

```bash
# 1. 登录 MySQL
mysql -u root -p

# 2. 创建数据库
CREATE DATABASE doc2md CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 3. 创建用户并授权
CREATE USER 'doc2md_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON doc2md.* TO 'doc2md_user'@'localhost';
FLUSH PRIVILEGES;

# 4. 退出
EXIT;
```

然后在 `.env` 中配置：

```env
DATABASE_URL=mysql+pymysql://doc2md_user:your_password@127.0.0.1:3306/doc2md?charset=utf8mb4
```

### 方法 3：使用 SQLite（开发环境）

无需创建数据库，只需修改 `.env`：

```env
DATABASE_URL=sqlite:///./dev.db
```

然后运行初始化脚本：

```bash
python init_db.py
```

---

## 🔧 维护命令

### 查看表结构

```bash
python -c "from webapp.backend.app.models import Base; from sqlalchemy import schema; import pprint; pprint.pprint([str(t) for t in Base.metadata.tables.values()])"
```

### 重置数据库（⚠️ 警告：会删除所有数据）

```bash
# MySQL
mysql -u root -p -e "DROP DATABASE doc2md; CREATE DATABASE doc2md CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# SQLite
rm dev.db

# 重新初始化
python init_db.py
```

### 备份数据库

```bash
# MySQL
mysqldump -u root -p doc2md > backup_$(date +%Y%m%d).sql

# SQLite
cp dev.db dev.db.backup
```

---

## 📝 注意事项

1. **字符集**：建议使用 `utf8mb4` 字符集以支持完整的 Unicode 字符
2. **索引**：已为常用查询字段添加索引（如 `username`, `user_id`, `job_id` 等）
3. **级联删除**：删除 `crawl_jobs` 时会自动删除关联的 `documents`
4. **匿名支持**：`crawl_jobs.user_id` 可为空，支持未登录用户创建任务（使用 `anon_id`）
5. **大文本存储**：`markdown_text` 使用 `LONGTEXT`，可存储最大 4GB 的内容

---

## 🛠️ 开发相关

### ORM 模型定义

模型定义位于 `webapp/backend/app/models.py`：

```python
from webapp.backend.app.models import User, CrawlJob, Document

# 创建用户
user = User(username="test", password_hash="...")
# 创建任务
job = CrawlJob(name="我的任务", start_url="https://example.com", ...)
# 创建文档
doc = Document(job_id=job.id, title="标题", markdown_text="...", ...)
```

### 数据库会话

```python
from webapp.backend.app.db import SessionLocal

db = SessionLocal()
try:
    # 查询
    jobs = db.query(CrawlJob).all()
    # 添加
    db.add(new_job)
    # 提交
    db.commit()
finally:
    db.close()
```
