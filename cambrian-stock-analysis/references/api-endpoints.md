# 股票数据 API 端点参考

分析中钢国际(000928)时实际验证可用的接口。标记 ✅ 可用，❌ 不可用。

---

## 一、实时行情

### #1 东方财富实时行情 ❌

```
GET https://push2.eastmoney.com/api/qt/stock/get
  ?secid=0.000928          (0=深市, 1=沪市)
  &fields=f57,f58,f43,f44,f45,f46,f47,f48,f116,f117,f162,f169,f170
```

字段：f57代码 f58名称 f43现价(分÷100) f44最高 f45最低 f46昨收 f47成交量(手) f48成交额(元) f116总市值 f117流通市值 f162动态PE(÷100) f169涨跌额(分) f170涨跌幅(%÷100)

注意：返回 JSON 顶层直接含 `data`，非嵌套在 `result` 下。

### #2 腾讯实时行情 ✅

```
GET https://qt.gtimg.cn/q=sz000928
Header: User-Agent: Mozilla/5.0
```

编码 GBK，中文可能乱码但数字可解析。格式：`v_sz000928="51~名称~代码~现价~今开~昨收~成交量~..."`，用 `~` split 后按索引取：`[3]`现价 `[4]`今开 `[5]`昨收 `[6]`成交量 `[44]`总市值(亿) `[45]`流通市值(亿)。

### #3 新浪实时行情 ❌

返回 403 Forbidden，不可用。

---

## 二、基本面

### #4 公司概况 ✅（慢，但可用）

```
GET https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code=SZ000928
```

返回 `jbzl` 对象含：`sshy`所属行业 `sszjhhy`证监会行业 `frdb`法人代表 `dsz`董事长 `zqlb`证券类别 `clrq`成立日期 `ssrq`上市日期。

实控人字段不稳定，建议结合已知央企名单判断。

返回的 `gsjj`（公司简介）常直接写明央企归属（例："是中国宝武钢铁集团有限公司的成员企业"），是判断实控人**最可靠**的字段。

⚠️ 健康检查脚本默认 10s 超时，该接口常被误标 ❌。**实际请求把 timeout 提到 40s 即可成功**（2026-09 实测：10s 超时、40s 返回完整数据）。

### #5 营收构成（主营占比）✅

```
GET https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code=SZ000928
```

返回 `zygcfx` 数组，每项含：
- `ITEM_NAME` 产品/业务名称
- `MAIN_BUSINESS_INCOME` 营业收入(元)
- `MBI_RATIO` 营收占比（如 0.9076 = 90.76%）
- `GROSS_RPOFIT_RATIO` 毛利率
- `REPORT_DATE` 报告期

### #6 股东人数统计 ✅

```
GET https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code=SZ000928&type=skg
```

返回 `gdrs` 数组含股东人数变化，但股东名称详情字段常为乱码，不可靠。

---

## 三、财务数据

### #7 利润表（归母净利润）✅

```
GET https://datacenter.eastmoney.com/securities/api/data/v1/get
  ?reportName=RPT_DMSK_FN_INCOME
  &columns=SECURITY_CODE,REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT
  &filter=(SECURITY_CODE="000928")
  &pageNumber=1
  &pageSize=30
  &sortTypes=-1
  &sortColumns=REPORT_DATE
```

可用字段：`TOTAL_OPERATE_INCOME`(营收) `PARENT_NETPROFIT`(归母净利润)。

❌ 不可用字段（已确认不存在）：
- `DEDUCTED_PARENT_NETPROFIT` — 扣非净利润
- `BASIC_EPS` — 基本每股收益
- `WEIGHTAVG_ROE` — 加权ROE

⚠️ 数据在 `result.data` 下（非顶层 `data`），`result.pages` 为总页数。

### #7b 现金流量表（FCF 用）✅

```
GET https://datacenter.eastmoney.com/securities/api/data/v1/get
  ?reportName=RPT_DMSK_FN_CASHFLOW
  &columns=ALL                      ← 直接写 ALL，省得猜字段名
  &filter=(SECURITY_CODE="000928")
  &pageNumber=1&pageSize=40
  &sortTypes=-1&sortColumns=REPORT_DATE
  &source=WEB&client=WEB
```

- ❌ `CASH_PAY_ACQUI_FIX_INTAN` **字段不存在**（会报 `code:9501`）。
- ✅ **资本开支（CAPEX）实际字段名：`CONSTRUCT_LONG_ASSET`**（购建固定资产、无形资产和其他长期资产支付的现金）。
- ✅ 经营活动现金流净额：`NETCASH_OPERATE`。
- 取不到字段时直接 `columns=ALL` 拉全量再挑，比猜名字快。

### #8 新浪利润表 ✅

```
GET https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_ProfitStatement/stockid/000928/ctrl/part/displaytype/4.phtml
```

编码 GBK，返回 HTML 表格，需正则解析。归母净利润可提取，扣非净利润不可靠。

---

## 四、K线数据

### #9 日K线 ✅

```
GET https://push2his.eastmoney.com/api/qt/stock/kline/get
  ?secid=0.000928
  &fields1=f1,f2,f3,f4,f5,f6
  &fields2=f51,f52,f53,f54,f55,f56,f57
  &klt=101              (101=日线)
  &fqt=0                (0=不复权)
  &end=20500101
  &lmt=500              (返回条数，够聚合2年月线)
```

每条数据：`日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率`

⚠️ **2026-09 实测：全部 `Remote end closed connection without response`**（日/周/月、`push2`/`push2his`/`63.push2his`、`lmt` 200/500/900、http/https 全部失败）。
**K 线请直接用下面 #12 腾讯接口**，不要再在东方财富 K 线上浪费轮次。

### #10 月K线 ✅

`klt=103` 返回空，不可用。改用 #12 腾讯 `month`（推荐）或日线聚合为月线。

### #11 周K线 ✅

`klt=102` 同样不可用。改用 #12 腾讯 `week`（推荐）或日线聚合。

### #12 腾讯K线 ✅（K 线首选，2026-09 实测稳定）

```
GET https://web.ifzq.gtimg.cn/appstock/app/fqkline/get
  ?param=sz000928,day,,,900,qfq
```

- `kind` 取值：`day` / `week` / `month`；倒数第二参数为条数；末位 `qfq`=前复权（`hfq` 后复权，留空=不复权）。深市前缀 `sz`，沪市 `sh`。
- **返回结构**：`data["sz000928"]["qfqday"]` —— **键名是 `qfq` + kind**。周线 `qfqweek`、月线 `qfqmonth`。不加 `qfq` 前缀取到的是 `None`。
- 每条：`[日期, 开, 收, 高, 低, 成交量(手)]`。
- 实测：day 640 根、week 320 根、month 80 根，全部正常。

---

## 五、最佳实践：一次分析的标准数据拉取流程

用 `execute_code` + Python `urllib` 一次脚本完成以下全部，避免多次 tool call：

```python
# 伪代码
secid = "0.000928"
code = "000928"

# 并行拉取4个接口
实时行情    ← 接口#1 (push2.eastmoney.com/.../get)
利润表      ← 接口#7 (datacenter.eastmoney.com/.../get) × 3页（覆盖2020-2025年报）
营收构成    ← 接口#5 (emweb.../BusinessAnalysis/PageAjax)
日K线       ← 接口#9 (push2his.../kline/get) lmt=500

# 数据处理
年报净利 ← 过滤 REPORT_DATE 含 '-12-31' 的记录，计算同比增长
主营占比 ← 取最新报告期 MBI_RATIO 最大值对应业务
月线聚合 ← 日线按 YYYY-MM 分组，取月末收盘价 + 月总成交量
底部判定 ← 24个月收盘价排序，计算30%分位、当前分位
放量判定 ← 近3月均量 / 前12月均量
```

实控人：从接口#4获取行业信息后，结合已知央企/国企名单判断（中钢集团→国资委、中国XX→央企等），不明时在报告中标注"待确认"。

---

## 六、通用注意事项

1. 所有 eastmoney API 返回 utf-8-sig 编码（BOM头），Python 用 `decode('utf-8-sig')`
2. 腾讯接口 GBK 编码，中文可能乱码但数字字段可靠
3. 所有请求必须带 `User-Agent: Mozilla/5.0` 头
4. 扣非净利润 → datacenter 无该字段。用 `RPT_LICO_FN_CPD` 的 `DEDUCT_BASIC_EPS × (PARENT_NETPROFIT / BASIC_EPS)` 还原（**逐年算隐含股本**），详见 SKILL.md 常见误区 #7
5. 浏览器 Chrome sandbox 限制 → 不依赖 browser_navigate
6. `datacenter.eastmoney.com` 数据在 `result.data`，非顶层 `data`
7. `push2.eastmoney.com` 数据在顶层 `data`
8. URL 中 `"` 需编码为 `%22`
