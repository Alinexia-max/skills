# SQL 聚合模式参考

本文档提供不同数据库中特殊聚合策略的 SQL 实现。

## 1. LAST（取最后一条）

### MySQL

使用 `GROUP_CONCAT` + `SUBSTRING_INDEX`：

```sql
SELECT 
    device_id,
    -- 按 collect_time 倒序，取最后一个 status
    SUBSTRING_INDEX(
        GROUP_CONCAT(status ORDER BY collect_time DESC SEPARATOR ','), 
        ',', 
        1
    ) as last_status
FROM t_device_metric
GROUP BY device_id
```

**注意**：`GROUP_CONCAT` 有长度限制（默认1024），可通过 `group_concat_max_len` 调整。

### Oracle

使用窗口函数 `FIRST_VALUE`：

```sql
SELECT 
    device_id,
    last_status
FROM (
    SELECT 
        device_id,
        FIRST_VALUE(status) OVER (
            PARTITION BY device_id 
            ORDER BY collect_time DESC
        ) as last_status,
        ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY collect_time DESC) as rn
    FROM t_device_metric
)
WHERE rn = 1
```

### PostgreSQL

使用窗口函数 `FIRST_VALUE`：

```sql
SELECT DISTINCT
    device_id,
    FIRST_VALUE(status) OVER (
        PARTITION BY device_id 
        ORDER BY collect_time DESC
    ) as last_status
FROM t_device_metric
```

## 2. FIRST（取第一条）

### MySQL

```sql
SELECT 
    device_id,
    SUBSTRING_INDEX(
        GROUP_CONCAT(status ORDER BY collect_time ASC SEPARATOR ','), 
        ',', 
        1
    ) as first_status
FROM t_device_metric
GROUP BY device_id
```

### Oracle

```sql
SELECT 
    device_id,
    first_status
FROM (
    SELECT 
        device_id,
        FIRST_VALUE(status) OVER (
            PARTITION BY device_id 
            ORDER BY collect_time ASC
        ) as first_status,
        ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY collect_time ASC) as rn
    FROM t_device_metric
)
WHERE rn = 1
```

### PostgreSQL

```sql
SELECT DISTINCT
    device_id,
    FIRST_VALUE(status) OVER (
        PARTITION BY device_id 
        ORDER BY collect_time ASC
    ) as first_status
FROM t_device_metric
```

## 3. COUNT_DISTINCT（去重计数）

### 所有数据库通用

```sql
SELECT 
    device_id,
    COUNT(DISTINCT user_id) as distinct_user_count
FROM t_device_metric
GROUP BY device_id
```

## 4. 完整聚合 SQL 示例（MySQL）

```sql
INSERT INTO t_device_metric_stat (
    time_window,
    device_id,
    total_traffic,
    avg_cpu_usage,
    max_memory_usage,
    last_status,
    first_error_code,
    distinct_user_count,
    create_time
)
SELECT 
    '2026-05-27 09:00:00' as time_window,
    device_id,
    SUM(traffic_bytes) as total_traffic,
    AVG(cpu_usage) as avg_cpu_usage,
    MAX(memory_usage) as max_memory_usage,
    -- LAST 取值
    SUBSTRING_INDEX(
        GROUP_CONCAT(status ORDER BY collect_time DESC SEPARATOR ','), 
        ',', 
        1
    ) as last_status,
    -- FIRST 取值
    SUBSTRING_INDEX(
        GROUP_CONCAT(error_code ORDER BY collect_time ASC SEPARATOR ','), 
        ',', 
        1
    ) as first_error_code,
    COUNT(DISTINCT user_id) as distinct_user_count,
    NOW() as create_time
FROM t_device_metric
WHERE collect_time >= '2026-05-27 09:00:00'
  AND collect_time < '2026-05-27 09:05:00'
GROUP BY device_id
```

## 5. 推荐方案

### 方案1：单 SQL 聚合（推荐）

在数据库端完成所有聚合，性能最好。

**优点**：
- 性能最好
- 网络传输少

**缺点**：
- LAST/FIRST 需要用 `GROUP_CONCAT`（MySQL）或窗口函数
- SQL 较复杂

### 方案2：应用端聚合

先查询数据，在 Java 内存中聚合。

**优点**：
- 灵活，可实现复杂逻辑
- 不依赖数据库特性

**缺点**：
- 性能差（数据量大时）
- 占用应用内存

**推荐**：优先使用方案1（单 SQL 聚合）。
