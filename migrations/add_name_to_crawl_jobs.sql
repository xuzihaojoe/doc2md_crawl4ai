-- 添加任务名称字段到 crawl_jobs 表
-- 执行前请备份数据库

-- 1. 添加 name 字段
ALTER TABLE crawl_jobs ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT '' AFTER id;

-- 2. 更新现有数据（使用 URL 作为默认名称）
UPDATE crawl_jobs SET name = CONCAT('任务-', SUBSTRING(start_url, 1, 50)) WHERE name = '';

-- 3. 设置非空约束
ALTER TABLE crawl_jobs MODIFY COLUMN name VARCHAR(255) NOT NULL;
