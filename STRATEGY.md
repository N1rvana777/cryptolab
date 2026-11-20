# CryptoLab 策略文档

## 概览

CryptoLab 是一个加密货币永续合约量化交易系统，核心策略为 **DonchianMTF**——基于多时间框架唐奇安通道突破的趋势跟踪策略，配合波动率目标仓位管理和动态风控。

- **交易品种**: 加密货币永续合约（BTC、SOL、ADA、XRP 等）
- **交易时间框架**: 4 小时 K 线
- **策略风格**: 趋势跟踪（Trend Following）
- **当前组合 OOS Sharpe**: 0.86

---

## 一、策略架构

系统分为两层策略：

| 策略 | 说明 | 状态 |
|------|------|------|
| `DonchianBreakout` | 单时间框架唐奇安突破，基础版本 | 已弃用，作为参考保留 |
| `DonchianMTF` | 多时间框架唐奇安突破 + 动态仓位管理 | **当前主策略** |

两者都继承自 `BaseStrategy` 抽象基类，输出统一的 `StrategySignal`。

---

## 二、核心策略：DonchianMTF

### 2.1 入场信号

**唐奇安通道突破**：使用"中间"时间框架（默认 72 根 4H K 线 = 12 天）的唐奇安通道作为主入场信号。

- 唐奇安通道 = 过去 N 根 K 线的最高价（上轨）和最低价（下轨）
- **通道计算排除当前 K 线**，避免前视偏差（look-ahead bias）
- 当收盘价突破上轨 → 做多信号
- 当收盘价突破下轨 → 做空信号

```
上轨 = max(过去 N 根 K 线的最高价)
下轨 = min(过去 N 根 K 线的最低价)
收盘价 > 上轨 → LONG
收盘价 < 下轨 → SHORT
```

### 2.2 多时间框架共识（MTF Agreement）

策略同时计算三个不同回看周期的唐奇安通道，用于衡量趋势强度：

| 时间框架 | 回看周期（4H K 线数） | 对应天数 | 默认权重 |
|----------|----------------------|----------|----------|
| 短期 | 24 | 4 天 | 0.33 |
| 中期 | 72 | 12 天 | 0.34 |
| 长期 | 168 | 28 天 | 0.33 |

每个时间框架独立判断趋势方向：
- 收盘价突破该 TF 上轨 → +1（看多）
- 收盘价突破该 TF 下轨 → -1（看空）
- 未突破 → 维持上次状态（有记忆性）

**共识分数**（combined score）= 各 TF 信号的加权平均，范围 [-1, +1]。

- 三个 TF 全部看多 → combined ≈ +1.0（满仓做多）
- 两个看多一个看空 → combined ≈ +0.33（轻仓做多）
- 低于死区阈值（默认 0.05）→ 不开仓

### 2.3 出场机制

策略使用**双重出场**机制：

#### ATR 追踪止损（Trailing Stop）
- 止损距离 = ATR(14) × 2.0
- ATR 使用 Wilder 平滑法（RMA），与 TradingView 一致
- 多头：止损只往上调，永不下移（`trail_stop = max(旧止损, 当前价 - 止损距离)`）
- 空头：止损只往下调，永不上移（`trail_stop = min(旧止损, 当前价 + 止损距离)`）

#### 反向突破出场
- 多头持仓中，收盘价跌破中期 TF 唐奇安下轨 → 平仓
- 空头持仓中，收盘价突破中期 TF 唐奇安上轨 → 平仓

**两个条件满足任一即平仓**，取先触发者。

#### 跳空止损（Gap Stop）
- 回测引擎额外检查：如果新 K 线的开盘价直接跳过止损位，以开盘价成交平仓
- 防止在极端行情中止损被跳过

---

## 三、仓位管理

### 3.1 基础仓位

```
risk_usd = 账户权益 × risk_per_trade（默认 2%）
stop_dist_pct = (ATR × atr_sl_mult) / 当前价
base_position = (risk_usd / stop_dist_pct) × leverage
```

含义：每笔交易风险控制在账户的 2%，根据止损距离反算仓位大小，再乘以杠杆。

### 3.2 共识缩放

```
position_usd = base_position × |combined_score| × vol_scalar × dd_scalar
```

仓位大小与多时间框架共识强度成正比——共识越强，仓位越大。

### 3.3 波动率目标（Vol Targeting）

```
ann_vol = (ATR / 价格) × sqrt(每年 K 线数)
vol_scalar = 目标年化波动率 / 实际年化波动率
vol_scalar 限制在 [0.5, 2.0] 范围内
```

- 目标年化波动率：15%
- 市场波动率高时自动缩小仓位，波动率低时放大仓位
- 使交易的风险暴露更加稳定

### 3.4 回撤缩放（Drawdown Scaling）

```
current_dd = (峰值权益 - 当前权益) / 峰值权益
dd_scalar = 1.0 - (1 - dd_floor) × (current_dd / dd_max)
```

- 最大回撤阈值（dd_max）：30%
- 回撤地板（dd_floor）：0.25
- 回撤越深，仓位自动缩小，最低缩至原始仓位的 25%
- 用于控制尾部风险，防止回撤螺旋

### 3.5 最大仓位限制

```
position_usd = min(position_usd, equity × leverage)
```

单个品种的仓位不超过权益 × 杠杆（默认 3 倍）。

---

## 四、可选模块（当前均已关闭）

以下功能已实现但在当前最优配置中权重为 0（关闭状态）：

### 4.1 TSMOM 动量混合（mom_weight = 0）

时间序列动量信号：过去 N 期的收益率除以已实现波动率，归一化到 [-1, 1]。

```
score = (收益率 / (波动率 × sqrt(回看期))) / 2.5
final_combined = (1 - mom_weight) × breakout_combined + mom_weight × mom_score
```

可与突破信号混合使用，也可独立触发入场（当 |mom_score| > 阈值时）。

### 4.2 成交量加权（vw_weight = 0）

用当前成交量与近期均量的比值来放大或衰减共识分数。放量突破仓位更大，缩量突破仓位更小。

### 4.3 RSI 均值回归过滤（mr_weight = 0）

在 RSI 极端值时削减入场仓位：做多时 RSI 过高（超买）→ 减仓；做空时 RSI 过低（超卖）→ 减仓。

### 4.4 截面动量（cs_weight = 0）

多品种组合中，根据各品种的动量排名调整仓位权重。强势品种加仓，弱势品种减仓。

### 4.5 金字塔加仓（pyramid_max_units = 1，即关闭）

趋势延续时追加仓位，每次加仓间隔 0.5 × ATR，最多加到 N 个单位。加仓时同步收紧止损。

---

## 五、回测引擎

### 5.1 执行模型

- **成交价**: 下一根 K 线的开盘价 + 滑点（避免前视偏差）
- **滑点**: 默认 15 bps（买入加价，卖出减价）
- **手续费**: Taker 3.5 bps，Maker 1.0 bps
- **权益计算**: 复利模式（每根 K 线的权益 = 现金 + 未实现盈亏）

### 5.2 信号流程

```
Bar 0: 生成初始信号（不执行）
Bar 1+:
  1. 检查跳空止损
  2. 以本 Bar 开盘价 + 滑点执行上一 Bar 的信号
  3. 更新权益（MTM）
  4. 生成本 Bar 的信号（供下一 Bar 执行）
```

### 5.3 评价指标

| 指标 | 说明 |
|------|------|
| Sharpe Ratio | 年化收益 / 年化波动率 |
| Sortino Ratio | 年化收益 / 年化下行波动率 |
| Calmar Ratio | 年化收益 / 最大回撤 |
| Profit Factor | 总盈利 / 总亏损 |
| Win Rate | 盈利交易占比 |
| Max Drawdown | 最大回撤幅度 |
| Time in Market | 持仓时间占比 |

---

## 六、组合管理

### 6.1 品种选择

当前组合（OOS 评级）：

| 品种 | 评级 | 说明 |
|------|------|------|
| BTC | G (Good) | 主流，流动性最佳 |
| SOL | G (Good) | 趋势性强 |
| ADA | G (Good) | 与 BTC 相关性适中 |
| XRP | F (Fair) | 表现尚可，分散化作用 |

### 6.2 资金分配

- 等权分配：总资金 / 品种数量，各品种独立回测
- 组合权益 = 各品种权益之和
- 不同品种的数据起始时间不同时，前向填充处理

### 6.3 验证框架

- **样本内（IS）**: 2021–2023，用于参数优化和策略开发
- **样本外（OOS）**: 2024–2026，用于验证策略稳健性
- 任何参数变更必须先在 OOS 上验证，防止过拟合

---

## 七、数据管道

### 7.1 数据源

| 来源 | 用途 | 说明 |
|------|------|------|
| OKX 永续合约 | 主要历史数据源 | 2020 年至今的永续合约 K 线 |
| Binance 现货 | 交叉验证 | 通过 Binance Vision API |
| Hyperliquid | 实时/近期数据 | 用于实盘 |

### 7.2 缓存

- 本地 Parquet 文件缓存，按品种和时间框架存储
- 首次使用需运行 `python scripts/seed_cache.py` 下载历史数据

---

## 八、风控参数汇总

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `risk_per_trade` | 2% | 单笔交易风险占权益比例 |
| `max_portfolio_heat` | 6% | 组合最大同时风险暴露 |
| `leverage` | 3x | 默认杠杆 |
| `atr_sl_mult` | 2.0 | 止损 = ATR × 此值 |
| `mtf_vol_target` | 15% | 目标年化波动率 |
| `mtf_dd_max` | 30% | 触发满额缩仓的回撤阈值 |
| `mtf_dd_floor` | 25% | 最大回撤时的仓位下限 |
| `slippage_bps` | 15 | 滑点假设（基点） |
| `taker_fee_bps` | 3.5 | Taker 手续费（基点） |
| `maker_fee_bps` | 1.0 | Maker 手续费（基点） |

---

## 九、文件结构

```
cryptolab/
  config.py              — 所有策略/风控/回测参数（Config dataclass）
  strategy/
    base.py              — BaseStrategy ABC + StrategySignal
    donchian.py          — DonchianBreakout（单 TF 基础版）
    donchian_mtf.py      — DonchianMTF（多 TF 主策略）
  indicators/
    core.py              — ATR, EMA, SMA, RSI, ADX, Bollinger, TSMOM 等
    donchian.py          — 唐奇安通道计算
    cross_sectional.py   — 截面动量排名
  backtest/
    engine.py            — 回测引擎（单品种）
    metrics.py           — Sharpe, Sortino, Calmar 等指标计算
  data/
    manager.py           — 数据管理器（统一接口）
    cache.py             — Parquet 缓存
    fetchers/            — OKX / Binance / Hyperliquid 数据获取
  execution/
    hl_client.py         — Hyperliquid 实盘执行客户端
    position_manager.py  — 仓位管理器
scripts/
  run_backtest.py        — 单品种回测脚本
  run_portfolio.py       — 组合回测脚本
  seed_cache.py          — 数据预下载
tests/                   — 测试套件
RESEARCH_LOG.md          — 实验记录（自动追加）
```
