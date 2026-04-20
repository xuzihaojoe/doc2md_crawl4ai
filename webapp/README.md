# doc2md web（无登录也可用的抓取 + 在线 Markdown 预览）

## 功能

- 前端页面：输入 URL 一键抓取
- 后台异步抓取（复用本仓库的 `doc2md_crawl4ai`）
- 抓取结果写入数据库（MySQL）
- 可选：把 Markdown 上传到七牛云（OOS/对象存储），并在页面提供链接
- 不登录也能用：前端会自动生成匿名会话 ID（**刷新页面会变化**，因此不登录不会保留历史列表）

## 1) 后端启动（FastAPI）

安装依赖：

```bash
pip install -r requirements.txt --break-system-packages
```

准备配置：

```bash
cp .env.example .env
# 然后按你的 MySQL / 七牛配置去填写 .env
```

启动后端：

```bash
python -m webapp.backend.run_server
```

默认地址：
- API: http://localhost:8000/api

## 2) 前端启动（Vite + React）

```bash
cd webapp/frontend
npm install
npm run dev
```

默认地址：
- 前端: http://localhost:5173

> 开发模式下已配置代理：前端请求 `/api/**` 会自动转发到 `http://localhost:8000`。

## 3) 一体化部署（可选）

前端构建：

```bash
cd webapp/frontend
npm run build
```

构建完成后会输出到 `webapp/frontend/dist`，后端启动时会自动把该目录挂载为静态站点（`/`）。

