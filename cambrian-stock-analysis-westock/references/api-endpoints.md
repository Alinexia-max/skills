# 股票数据来源参考（westock 优先）

> **本文件只负责一件事**：记录 `westock` 覆盖不到、需要走 HTTP 端点的**两个缺口**。
> 其余所有定量数据一律走 `westock`，见 `SKILL.md` 的「数据来源铁律」。

**状态实测时间：2026-10-04**（测试标的：中钢国际 000928；测试方式：Node.js `fetch`）

---

## 零、数据来源分层（先看这里）

| 层级 | 来源 | 使用条件 |
|------|------|---------|
| 1 | **westock CLI**（主源） | 只要 westock 有，**必须**用 westock |
| 2 | **HTTP 端点**（仅本文件 #4、#5） | 仅当 westock 没有该字段 |
| 3 | ❌ 联网搜索 / 编造 | **任何情况都禁止** |

### 只有这两个缺口允许走 HTTP

| 缺口 | 使用端点 | 对应评分项 |
|------|---------|-----------|
| 营业总收入构成 / 主营占比 | **#5 营收构成** | 因子 #5 主营集中 |
| 实控人 / 央企归属（westock 判不出时） | **#4 公司概况** `gsjj` | 风控一、因子 #1 |

**其余端点（#1/#2/#3/#6/#7/#8/#9/#10/#11/#12）已全部被 westock 替代，不得用于取数。**

---

## 一、端点实测状态（2026-10-04）

| # | 端点 | 文件原标记 | 实测 | 结论 |
|---|------|-----------|------|------|
| #1 | 东方财富实时行情 | ❌ | **HTTP 200**（304ms） | ✅ 已恢复，但**改用 `westock quote`** |
| #2 | 腾讯实时行情 | ✅ | **HTTP 200**（226ms） | ✅ 可用，但**改用 `westock quote`** |
| #3 | 新浪实时行情 | ❌ | **HTTP 403 Forbidden** | ❌ 确实不可用 |
| #4 | 公司概况 | ✅ | **HTTP 200**（10172ms） | ⚠️ **保留**（慢，需 40s 超时） |
| #5 | 营收构成 | ✅ | **HTTP 200**（216ms） | ⚠️ **保留**（westock 无替代） |
| #6 | 股东人数 | ✅ | **HTTP 200**（283ms） | ✅ 可用，但股东数据**改用 `westock shareholder`** |
| #7 | 利润表 datacenter | ✅ | **HTTP 200**（152ms） | ✅ 可用，但**改用 `westock finance`** |
| #7b | 现金流量表 | ✅ | **HTTP 200**（115ms） | ✅ 可用，但**改用 `westock finance --type cashflow`** |
| #8 | 新浪利润表 | ✅ | **HTTP 200**（219ms，HTML） | ✅ 可用，但**改用 `westock finance`**（免正则解析） |
| #9 | 日K线 push2his | ❌ | **HTTP 200**（177ms） | ✅ **已恢复**，但 K 线**改用 `westock kline`** |
| #10 | 月K线 klt=103 | ❌ | 未复测 | 已废弃 → 用 `westock kline --period month` |
| #11 | 周K线 klt=102 | ❌ | 未复测 | 已废弃 → 用 `westock kline --period week` |
| #12 | 腾讯K线 | ✅ | **HTTP 200**（227ms） | ✅ 可用，但 K 线**改用 `westock kline`** |

### 重要修正记录

- **#1、#9 当初被标记为 ❌，2026-10-04 实测均已恢复**（HTTP 200）。原文件中"东财 K 线全部失败""实时行情不可用"的结论已过时。
- 但**即使恢复也不使用**——westock 已完整覆盖行情与 K 线，按铁律必须走 westock。
- **#3 新浪实时行情确认为死链**（403），永久移除。

---

## 二、westock ↔ HTTP 字段映射表

| 原端点 | 原字段 / 索引 | westock 替代 | westock 字段 |
|--------|--------------|-------------|-------------|
| #1/#2/#3 实时行情 | 现价、昨收、成交量 | `westock quote <代码>` | `price` `prev_close` `volume` |
| #1 总市值 | f116 | `westock quote` | `total_market_cap`（**单位：元**） |
| #1 流通市值 | f117 | `westock quote` | `circulating_market_cap`（单位：元） |
| #1 动态PE | f162（÷100） | `westock quote` | `pe_ratio` |
| #6 股东人数 | gdrs[] | `westock shareholder <代码>` | 十大股东 / 十大流通股东 / 股东户数 |
| #7 营收 | TOTAL_OPERATE_INCOME | `westock finance --type income` | `OperatingRevenue` |
| #7 归母净利 | PARENT_NETPROFIT | 同上 | `NPParentCompanyOwners` |
| #7b 经营现金流 | NETCASH_OPERATE | `westock finance --type cashflow` | `NetOperateCashFlow` |
| #7b 资本开支 | CONSTRUCT_LONG_ASSET | ⚠️ **westock 无对应字段** | 见下方第五节 |
| #8 利润表 | HTML 正则 | `westock finance --type income` | 结构化字段，无需解析 |
| #9/#10/#11/#12 K线 | klines / qfqday | `westock kline <代码> --period day\|week\|month` | `date` `open` `last` `high` `low` `volume` |
| #7 扣非净利润 | ❌ 不存在（需 EPS 反推） | `westock finance --type income` | **`NPDeductNonRecurringPL`（原生字段）** |
| — | — | `westock dividend <代码>` | 分红（原无对应端点） |
| — | — | `westock report list <代码>` | 研报（原无对应端点） |
| — | — | `westock notice list <代码>` | 公告（原无对应端点） |
| — | — | `westock fund flow <代码>` | 资金流向（原无对应端点） |

> 结论：**12 个端点里，10 个已被 westock 完全覆盖**，只剩 #4、#5 两个缺口。

---

## 三、缺口一：#5 营收构成（因子 #5 唯一来源）

### 端点

```
GET https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code=SZ000928
Header: User-Agent: Mozilla/5.0
```

### 取数方式（本机必须用 Node，PowerShell/curl 的 HTTPS 是坏的）

```bash
node -e "
fetch('https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code=SZ000928',{headers:{'User-Agent':'Mozilla/5.0'}})
 .then(r=>r.json()).then(j=>{
   const rows=(j.zygcfx||[]).filter(x=>/^\d{4}-\d{2}-\d{2}/.test(x.REPORT_DATE||''));
   const latest='2026-06-30';
   rows.filter(x=>x.REPORT_DATE.startsWith(latest)).slice(0,8)
     .forEach(x=>console.log(x.ITEM_NAME, x.MBI_RATIO, x.MAIN_BUSINESS_INCOME));
 });
"
```

### 字段

`zygcfx` 数组，每项含：
- `ITEM_NAME` 产品/业务名称
- `MAIN_BUSINESS_INCOME` 营业收入（元）
- `MBI_RATIO` 营收占比（如 `0.890503` = 89.05%）
- `GROSS_RPOFIT_RATIO` 毛利率
- `REPORT_DATE` 报告期

### 用法

取**最新报告期**、**占比最大**的业务项 `MBI_RATIO`，与 75% 阈值比较，据此给因子 #5 打分。

**2026-10-04 实测（中钢国际 000928，2026-06-30）：**

| 业务 | 营收占比 | 收入(元) |
|------|---------|---------|
| 工程总承包 | **89.05%** | 5,942,815,576.01 |
| 工程单机备件 | 8.48% | 565,981,080.89 |
| 工程咨询与服务 | 2.26% | 150,509,019.98 |
| 其他(补充) | 0.21% | 14,244,702.44 |

→ 主营占比 89.05% ≥ 75%，因子 #5 满足。

### 注意

- 返回 `zygcfx` 可能有 200 条历史记录，**必须按 `REPORT_DATE` 过滤到最新期**，否则会混入往期数据。
- 接口返回 UTF-8-sig（带 BOM），Node 的 `.json()` 可直接处理。

---

## 四、缺口二：#4 公司概况（实控人 / 央企归属）

**仅在 `westock profile` + `westock shareholder` 仍判断不出央企/省国资委属性时使用。**

### 端点

```
GET https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code=SZ000928
Header: User-Agent: Mozilla/5.0
```

### 字段

- `jbzl` 对象：`sshy`所属行业 `sszjhhy`证监会行业 `frdb`法人代表 `dsz`董事长 `zqlb`证券类别 `clrq`成立日期 `ssrq`上市日期
- **`gsjj`（公司简介）：常直接写明央企归属**（例："是中国宝武钢铁集团有限公司的成员企业"），是判断实控人**最可靠**的字段。

### 注意

- ⚠️ **该接口很慢，实测 10.2 秒**。健康检查脚本默认 10s 超时会把误标为 ❌，**实际使用请把超时提到 40s**。
- 实控人字段（`jbzl` 内）**不稳定**，不可单独依赖；以 `gsjj` 文字为准。
- **仍判断不出时标注"待确认"**，不得推测认定为民企或央企。

---

## 五、CAPEX 缺失说明（维度 B FCF）

原流程用东财 `CONSTRUCT_LONG_ASSET`（购建固定资产、无形资产和其他长期资产支付的现金）取 CAPEX。

**`westock` 现金流表没有这个字段。** 处理规则：

1. 优先尝试从 `NetInvestCashFlow`（投资活动现金流净额）中拆解；
2. **拆不出精确值时，按 SKILL.md 规定标注 `FCF ≈ CFO（轻资产近似）` 并给出估算区间**；
3. ❌ **严禁编造 CAPEX 数值**。

> 注意口径差异：`westock` 另有 `FCFF` / `FCFE`（已是现金流口径的总额）与 `ShareholderFreeCFPS` / `EnterpriseFreeCFPS`（**每股**口径），**与 `CFO − CAPEX` 口径不同，不可混用**；若使用必须在报告中注明口径来源。

---

## 六、通用注意事项

1. **只有 Node 能联网**：本机 `Invoke-WebRequest` 与 `curl` 的 HTTPS 均失败（`SEC_E_NO_CREDENTIALS`）。所有 HTTP 取数必须用 Node `fetch`。
2. 东财接口返回 UTF-8-sig（BOM）；腾讯接口 GBK。
3. 所有请求必须带 `User-Agent: Mozilla/5.0`。
4. URL 中 `"` 需编码为 `%22`。
5. `datacenter.eastmoney.com` 数据在 `result.data`；`push2.eastmoney.com` 在顶层 `data`。
6. 浏览器自动化不可用（Chrome sandbox 限制），且**本 skill 禁止联网检索**，不要依赖浏览器。
7. westock 代码必须带市场前缀：`sh`/`sz`/`bj`、`hk`、`us`、`pt`、`fu`、`fx`。
8. **健康检查脚本不再作为分析前置步骤**；westock 是主源，本文件仅两个缺口按需调用。
