---
name: data-aggregation-task
description: 根据需求直接生成数据聚合定时任务代码（硬编码方式）。当用户说"生成数据聚合任务"、"创建统计任务"、"定时聚合数据"、"实时数据转统计数据"时触发。适用：Java + Spring Boot + MyBatis。直接生成完整可运行的代码，不是模板。
---

# 数据聚合任务生成器

## 技术栈
Java 8+ / Spring Boot 2.x+ / Spring Scheduler / MyBatis

## 生成清单
✅ **必须生成**：
1. 聚合任务类（硬编码配置）
2. 源数据实体类（如不存在）
3. 统计数据实体类（如不存在）

❌ **不生成**：Mapper接口、Mapper XML、Service、Controller、配置文件、指南文档

## 使用流程

### 1. 收集需求
必须获取：
- **表信息**：源表名、统计表名、时间字段名、分组字段
- **聚合规则**：字段级聚合策略（SUM/AVG/MAX/MIN/COUNT/COUNT_DISTINCT/LAST/FIRST）
- **调度配置**：时间窗口（5分钟/1小时/1天）、Cron表达式

### 2. 探测项目结构
**生成代码前必须探测**：
1. 查找项目根目录（向上查找 `pom.xml` 或 `build.gradle`）
2. 确认 `src/main/java` 存在
3. 探测包结构（查找 `**/entity/`、`**/mapper/`、`**/task/` 等目录）
4. 提取基础包名（从任意Java文件读取package声明）

**探测完成后向用户展示并确认**：
```
📂 项目结构探测结果：
- 项目根目录：{项目根目录}
- 源码目录：src/main/java
- 基础包名：{基础包名}
- 实体类路径：{entity目录路径} {存在/将创建}
- 任务类路径：{task目录路径} {存在/将创建}

是否使用以上路径？[是/修改]
```

**用户确认后才能生成代码**。用户要求修改时，询问每个文件类型的目标路径，重新确认后再生成。

### 3. 生成代码
**根据实际需求生成完整可运行的代码**（不是模板）。

使用步骤2中用户确认的路径和包名。

#### 聚合任务类模板
```java
package {用户确认的基础包名}.task;

import {用户确认的基础包名}.mapper.{Stat}Mapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.time.DateFormatUtils;
import org.apache.commons.lang3.time.DateUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.Date;

@Component
@Slf4j
public class {Entity}AggregationTask {

    @Autowired
    private {Stat}Mapper {stat}Mapper;

    @Scheduled(cron = "{cron表达式}")
    public void aggregate() {
        Date now = new Date();
        Date startTime = {计算起始时间};
        Date endTime = now;
        String timeWindow = DateFormatUtils.format({时间}, "{格式}");

        log.info("【{业务}】开始, 时间窗口: {}", timeWindow);

        try {
            int deleted = {stat}Mapper.deleteByTimeWindow(timeWindow);
            if (deleted > 0) {
                log.warn("【{业务}】删除已存在数据, 条数: {}", deleted);
            }

            int inserted = {stat}Mapper.insertAggregatedData(startTime, endTime, timeWindow);
            log.info("【{业务}】完成, 插入条数: {}", inserted);
        } catch (Exception e) {
            log.error("【{业务}】失败, 时间窗口: " + timeWindow, e);
        }
    }
}
```

**时间窗口计算参考**：
| 时间窗口 | 起始时间计算 | 时间窗口格式 | Cron示例 |
|---------|-------------|-------------|----------|
| 5分钟 | `DateUtils.addMinutes(now, -5)` | `yyyy-MM-dd HH:mm:00` | `0 */5 * * * ?` |
| 1小时 | `DateUtils.addHours(now, -1)` | `yyyy-MM-dd HH:00:00` | `0 0 * * * ?` |
| 1天 | `DateUtils.addDays(now, -1)` | `yyyy-MM-dd 00:00:00` | `0 0 0 * * ?` |

#### 源数据实体类模板
```java
package {用户确认的基础包名}.entity;

import lombok.Data;
import java.util.Date;

@Data
public class {Source}Data {
    private Long id;
    {分组字段}
    {聚合字段}
    private Date {时间字段名};
}
```

#### 统计数据实体类模板
```java
package {用户确认的基础包名}.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.util.Date;

@Data
@TableName("{统计表名}")
public class {Stat}Data {
    private Long id;
    private String timeWindow;
    {分组字段}
    {统计字段}
    private Date createTime;
}
```

### 4. 输出结果
生成代码后，输出（使用用户确认的实际路径）：
```
✅ 已生成以下文件：

1. {用户确认的task目录路径}/{Entity}AggregationTask.java
2. {用户确认的entity目录路径}/{Source}Data.java (如不存在)
3. {用户确认的entity目录路径}/{Stat}Data.java (如不存在)

📝 请手动添加以下内容到已有文件：

1. 在 {Stat}Mapper.java 添加：
   - deleteByTimeWindow(String timeWindow)
   - insertAggregatedData(Date startTime, Date endTime, String timeWindow)

2. 在 {Stat}Mapper.xml 添加：
   - <delete id="deleteByTimeWindow">
   - <insert id="insertAggregatedData">
```

**不输出**：详细修改指南、SQL代码示例、索引建议、配置说明、注意事项。

## SQL参考
在 `references/sql-patterns.md` 中查看：LAST/FIRST、COUNT_DISTINCT 的 SQL 实现。

## Cron参考
在 `references/cron-reference.md` 中查看：常用 Cron 表达式、自然语言转 Cron。
