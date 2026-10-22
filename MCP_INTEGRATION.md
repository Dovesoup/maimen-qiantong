# MCP 接入说明

本项目**真实调用**麦当劳中国 MCP Server 获取门店与价格数据，不含任何模拟或硬编码价格。

## 1. 接入信息

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp` |
| 传输方式 | `streamablehttp` |
| 端点 | `https://mcp.mcd.cn` |
| 协议版本 | MCP `2025-06-18` |
| 鉴权 | `Authorization: Bearer <MCD_MCP_TOKEN>` |
| Token 获取 | [open.mcd.cn](https://open.mcd.cn) 手机号登录 → 控制台 → 激活 |
| 服务端状态 | 无状态（不返回 `Mcp-Session-Id`，无需 `initialize` 后续会话） |

配置示例见 [`mcp-config.example.json`](./mcp-config.example.json)，**只含环境变量占位符**，不含任何真实 Token。

## 2. 使用的 Tool

本项目只使用 2 个只读 Tool，不涉及下单、支付、领券、抽奖等写操作。

### 2.1 `query-nearby-stores` — 定位门店

```json
{
  "beType": 1,
  "searchType": 2,
  "city": "杭州市",
  "keyword": "西湖"
}
```

| 参数 | 说明 |
|---|---|
| `beType` | 固定 `1`（到店自提）。该场景返回的门店**不含 `beCode`**，后续调用不得传 |
| `searchType` | 固定 `2`（按位置搜索）。`1` 是搜索用户收藏餐厅，非登录态下无结果 |
| `city` | 城市名。**`searchType=2` 时必填** |
| `keyword` | 位置关键词（地标/商圈）。**`searchType=2` 时必填** |

返回 `data[]`，本项目的关键字段：`storeCode`（门店唯一编号，作为下一步入参）、`storeName`、`address`、`distance`、`businessStatus`。

### 2.2 `query-meals` — 获取门店实时菜单与价格

```json
{
  "storeCode": "3330536",
  "orderType": 1,
  "beType": 1
}
```

| 参数 | 说明 |
|---|---|
| `storeCode` | 来自 `query-nearby-stores` |
| `orderType` | 固定 `1`（到店）。`2` 为外送，需先建立收货地址 |
| `beType` | 固定 `1`。到店自提场景**不要传 `beCode`**，传了会报错 |

本项目只取 `data.meals` 中名称精确等于 `巨无霸`（排除 `巨无霸三件套` 等套餐）的项，读取：

- `currentPrice` — 该门店**实时销售价**（本项目采集目标）
- `originalPrice` — 划线原价

## 3. 调用流程

```
城市名 + 地标关键词
        │
        ▼
query-nearby-stores (beType=1, searchType=2)
        │  返回 data[].storeCode（单城最多取 5 家）
        ▼
query-meals (storeCode, orderType=1, beType=1)
        │  返回 data.meals[code].currentPrice
        ▼
按门店聚合 → 城市中位数/最高/最低 → 巨无霸指数
```

单城市 5 家门店约需 6 次 MCP 调用；全国 39 城约 234 次，串行限速 1 秒/次，全程约 5 分钟。

## 4. 实际遇到的接口行为（踩坑记录）

这些是开发过程中实测到的、文档未明写的细节，一并记录以便复查：

1. **`searchType=2` 必须同时传 `city` 和 `keyword`。** 只传 `city` 会返回 `code 600058 城市名或者关键词不能为空`，报错文案容易误判为参数名错误。
2. **返回体不是纯 JSON。** MCP 响应是「字段说明 markdown + `## Original Response` + 原始 JSON + 尾部提示文字」的拼接体，需按 `## Original Response` 切分后对首个 `{` 做 `raw_decode`，尾部多余文字要能容忍。
3. **部分门店菜单为空。** 名称含「快捷小站」「景区餐厅」的小型点位返回 `data.meals = {}`，`items = 0`。本项目将其如实记为 `null` 而非剔除，用于区分「无此商品」和「无数据」。
4. **巨无霸同时存在单品与套餐。** 菜单中既有 `巨无霸`（单品）也有 `巨无霸三件套`，价格差异大（本批数据前者约 25.5–29 元，后者约 54.5 元）。必须按名称精确匹配，否则指数会整体失真。
5. **价格是实时挂牌价，含会员/促销差异。** 响应中含 `discountType` 字段（早餐卡/麦金卡/促销），本项目只取 `currentPrice`，并在 README 中声明其口径。

## 5. 业务价值

- **对消费者**：同一个巨无霸在不同城市、甚至同城不同门店的价格并不相同，本项目把这个差异量化，用于回答「这家店值不值得进」「出差到某地该去哪家点」。
- **对研究者/媒体**：巨无霸指数是《经济学人》1986 年起的购买力平价代理指标，但公开版本只有国家层面一个数字。本项目提供**城市级、门店级**的颗粒度。
- **对麦当劳**：价格透明度本身是品牌信任的一部分；本项目不评价商品，只呈现公开挂牌价。

## 6. 合规声明

- 全部调用均为只读查询，不创建订单、不支付、不领券、不抽奖。
- 数据来源为麦当劳官方 MCP 返回的公开挂牌价，采用串行限速采集，不并发压测。
- 本项目不对麦当劳及其商品作任何评价性表述，不与任何其他品牌比较。
- 仓库内不含任何真实 Token、手机号、订单号或用户标识。
