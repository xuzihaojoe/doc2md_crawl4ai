#!/usr/bin/env python3
"""
数据库初始化脚本

用法:
    1. 配置 .env 文件中的数据库连接
    2. 运行: python init_db.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from webapp.backend.app.db import engine
from webapp.backend.app.models import Base, User
from webapp.backend.app.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_database():
    """初始化数据库表"""
    print("🔧 正在初始化数据库...")

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    print(f"✅ 数据库表创建成功！")
    print(f"📍 数据库连接: {settings.database_url}")


def create_admin_user(username: str = "admin", password: str = "admin123"):
    """创建管理员用户"""
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        # 检查用户是否已存在
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"⚠️  用户 '{username}' 已存在，跳过创建")
            return

        # 创建新用户
        user = User(
            username=username,
            password_hash=pwd_context.hash(password)
        )
        db.add(user)
        db.commit()

        print(f"✅ 管理员用户创建成功！")
        print(f"   用户名: {username}")
        print(f"   密码: {password}")
        print(f"   ⚠️  请登录后立即修改密码！")


def show_database_info():
    """显示数据库信息"""
    print("\n" + "=" * 50)
    print("📊 数据库结构说明")
    print("=" * 50)

    tables = [
        {
            "name": "users",
            "description": "用户表",
            "fields": [
                ("id", "Integer", "主键"),
                ("username", "String(64)", "用户名（唯一）"),
                ("password_hash", "String(255)", "密码哈希"),
                ("created_at", "DateTime", "创建时间"),
            ]
        },
        {
            "name": "crawl_jobs",
            "description": "爬取任务表",
            "fields": [
                ("id", "String(36)", "任务ID（UUID）"),
                ("name", "String(255)", "任务名称"),
                ("start_url", "Text", "起始URL"),
                ("status", "String(24)", "状态（pending/running/succeeded/failed）"),
                ("error", "Text", "错误信息"),
                ("max_pages", "Integer", "最大页数"),
                ("concurrency", "Integer", "并发数"),
                ("delay", "Float", "延迟（秒）"),
                ("engine", "String(24)", "引擎（http/playwright/auto）"),
                ("scope", "String(24)", "范围（same_origin/same_domain）"),
                ("include", "Text", "包含正则"),
                ("exclude", "Text", "排除正则"),
                ("user_id", "Integer", "用户ID（外键）"),
                ("anon_id", "String(64)", "匿名ID"),
                ("created_at", "DateTime", "创建时间"),
                ("finished_at", "DateTime", "完成时间"),
            ]
        },
        {
            "name": "documents",
            "description": "文档表",
            "fields": [
                ("id", "Integer", "主键"),
                ("job_id", "String(36)", "任务ID（外键）"),
                ("title", "String(255)", "标题"),
                ("url", "Text", "来源URL"),
                ("doc_index", "Integer", "文档索引"),
                ("is_merged", "Boolean", "是否为合并文档"),
                ("markdown_text", "LONGTEXT", "Markdown内容"),
                ("qiniu_key", "String(512)", "七牛云Key"),
                ("qiniu_url", "String(1024)", "七牛云URL"),
                ("created_at", "DateTime", "创建时间"),
            ]
        },
    ]

    for table in tables:
        print(f"\n📋 {table['name']} - {table['description']}")
        print("┌─────────────────────┬──────────────┬────────────────────────┐")
        print("│ 字段名              │ 类型         │ 说明                    │")
        print("├─────────────────────┼──────────────┼────────────────────────┤")
        for field_name, field_type, field_desc in table['fields']:
            print(f"│ {field_name:<19} │ {field_type:<12} │ {field_desc:<22} │")
        print("└─────────────────────┴──────────────┴────────────────────────┘")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库初始化脚本")
    parser.add_argument("--create-admin", action="store_true", help="创建管理员用户")
    parser.add_argument("--admin-username", default="admin", help="管理员用户名")
    parser.add_argument("--admin-password", default="admin123", help="管理员密码")

    args = parser.parse_args()

    try:
        # 初始化数据库
        init_database()

        # 显示数据库信息
        show_database_info()

        # 可选：创建管理员用户
        if args.create_admin:
            print()
            create_admin_user(args.admin_username, args.admin_password)
        else:
            print("\n💡 提示: 使用 --create-admin 参数创建管理员用户")
            print("   例如: python init_db.py --create-admin")

        print("\n" + "=" * 50)
        print("✅ 数据库初始化完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        print("\n请检查:")
        print("1. .env 文件中的数据库配置是否正确")
        print("2. 数据库服务是否已启动")
        print("3. 数据库用户是否有创建表的权限")
        sys.exit(1)
