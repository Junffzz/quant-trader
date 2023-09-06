"""
General constants enums used in the trading platform.
"""

from enum import Enum


class OrderStatus(Enum):
    """Order status"""
    UNKNOWN = "UNKNOWN"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PART_FILLED = "PART_FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OrderStatus2(Enum):
    """
    委托状态
    """
    Unknown = 0
    New = 1  # 已报
    PartiallyFilled = 2  # 部成
    Filled = 3  # 已成
    Canceled = 5  # 已撤
    PendingCancel = 6  # 待撤
    Rejected = 8  # 已拒绝
    Suspended = 9  # 挂起 （无效）
    PendingNew = 10  # 待报
    Expired = 12  # 已过期


class OrderSide(Enum):
    """
    委托方向
    """
    Unknown = 0
    Buy = 1  # 买入
    Sell = 2  # 卖出


class OrderType(Enum):
    """Order type."""
    LIMIT = "LMT"
    MARKET = "MKT"
    STOP = "STOP"
    FAK = "FAK"
    FOK = "FOK"


class OrderType1(Enum):
    """
    委托类型
    """
    Unknown = 0
    Limit = 1  # 限价委托
    Market = 2  # 市价委托
    Stop = 3  # 止损止盈委托  （还不支持）


class OrderTimeInForce(Enum):
    """
    订单有效期
    """
    DAY = "DAY"  # 当日有效
    GTC = "GTC"  # 撤单前有效


class OrderDuration(Enum):
    """
    委托时间属性
    仅在实盘模式生效，具体执行模式请参考交易所给出的定义
    """
    Unknown = 0
    FAK = 1  # 即时成交剩余撤销(fill and kill)
    FOK = 2  # 即时全额成交或撤销(fill or kill)
    GFD = 3  # 当日有效(good for day)
    GFS = 4  # 本节有效(good for section)
    GTD = 5  # 指定日期前有效(goodltilldate)
    GTC = 6  # 撤销前有效(goodtillcancel)
    GFA = 7  # 集合竞价前有效(good for auction)
    AHT = 8  # 盘后定价交易(after hour trading)


class OrderQualifier:
    """
    委托成交属性
    仅在实盘模式生效，具体执行模式请参考交易所给出的定义
    """
    Unknown = 0
    BOC = 1  # 对方最优价格(best of counterparty)
    BOP = 2  # 己方最优价格(best of party)
    B5TC = 3  # 最优五档剩余撤销(best 5 then cancel)
    B5TL = 4  # 最优五档剩余转限价(best 5 then limit)


class OrderBusiness:
    """
    委托业务类型
    """
    NORMAL = 0  # 普通交易。默认值为空，以保持向前兼容
    CREDIT_BOM = 200  # 融资买入(buying on margin)
    CREDIT_SS = 201  # 融券卖出(short selling)
    CREDIT_RSBBS = 202  # 买券还券(repay share by buying share)
    CREDIT_RCBSS = 203  # 卖券还款(repay cash by selling share)
    CREDIT_DRS = 204  # 直接还券(directly repay share)
    # 直接还款: 不通过委托，参考接口...
    CREDIT_BOC = 207  # 担保品买入(buying on collateral)
    CREDIT_SOC = 208  # 担保品卖出(selling on collateral)
    CREDIT_CI = 209  # 担保品转入(collateral in)
    CREDIT_CO = 210  # 担保品转出(collateral out)
    BOND_CONVERTIBLE_CALL = 402  # 可转债转股
    BOND_CONVERTIBLE_PUT = 403  # 可转债回售
    BOND_CONVERTIBLE_PUT_CANCEL = 404  # 可转债回售撤销


class ExecType:
    """
    执行回报类型
    """
    ExecType_Unknown = 0
    ExecType_Trade = 15  # 成交
    ExecType_CancelRejected = 19  # 撤单被拒绝


class PositionEffect:
    """
    开平仓类型
    """
    Unknown = 0
    Open = 1  # 开仓
    Close = 2  # 平仓, 具体语义取决于对应的交易所
    CloseToday = 3  # 平今仓
    CloseYesterday = 4  # 平昨仓


class PositionSide:
    Unknown = 0
    Long = 1  # 多方向
    Short = 2  # 空方向


class OrderRejectReason:
    """
    订单拒绝原因
    （仿真有效，实盘需要参考具体的拒绝原因）
    """
    Unknown = 0  # 未知原因
    RiskRuleCheckFailed = 1  # 不符合风控规则
    NoEnoughCash = 2  # 资金不足
    NoEnoughPosition = 3  # 仓位不足
    IllegalAccountId = 4  # 非法账户ID
    IllegalStrategyId = 5  # 非法策略ID
    IllegalSymbol = 6  # 非法交易标的
    IllegalVolume = 7  # 非法委托量
    IllegalPrice = 8  # 非法委托价
    AccountDisabled = 10  # 交易账号被禁止交易
    AccountDisconnected = 11  # 交易账号未连接
    AccountLoggedout = 12  # 交易账号未登录
    NotInTradingSession = 13  # 非交易时段
    OrderTypeNotSupported = 14  # 委托类型不支持
    Throttle = 15  # 流控限制


class CancelOrderRejectReason:
    """
    取消订单拒绝原因
    """
    OrderFinalized = 101  # 委托已完成
    UnknownOrder = 102  # 未知委托
    BrokerOption = 103  # 柜台设置
    AlreadyInPendingCancel = 104  # 委托撤销中


class OrderStyle:
    """
    - 委托风格
    """
    Unknown = 0
    Volume = 1  # 按指定量委托
    Value = 2  # 按指定价值委托
    Percent = 3  # 按指定比例委托
    TargetVolume = 4  # 调仓到目标持仓量
    TargetValue = 5  # 调仓到目标持仓额
    TargetPercent = 6  # 调仓到目标持仓比例


class CashPositionChangeReason:
    """
    - 仓位变更原因
    """
    Unknown = 0
    Trade = 1  # 交易
    Inout = 2  # 出入金 / 出入持仓


class SecType:
    """
    - 标的类别
    """
    STOCK = 1  # 股票
    FUND = 2  # 基金
    INDEX = 3  # 指数
    FUTURE = 4  # 期货
    OPTION = 5  # 期权
    CREDIT = 6  # 信用交易
    BOND = 7  # 债券
    BOND_CONVERTIBLE = 8  # 可转债
    CONFUTURE = 10  # 虚拟合约


class AccountStatus:
    """
    - 交易账户状态
    """
    UNKNOWN = 0  # 未知
    CONNECTING = 1  # 连接中
    CONNECTED = 2  # 已连接
    LOGGEDIN = 3  # 已登录
    DISCONNECTING = 4  # 断开中
    DISCONNECTED = 5  # 已断开
    ERROR = 6  # 错误


class PositionSrc:
    """
    头寸来源(仅适用融券融券)
    """
    Unknown = 0
    L1 = 1  # 普通池
    L2 = 2  # 专项池


class AlgoOrderStatus:
    """
    算法单状态,暂停/恢复算法单时有效
    """
    Unknown = 0,
    Resume = 1,  # 恢复母单
    Pause = 2,  # 暂停母单
    PauseAndCancelSubOrders = 3  # 暂停母单并撤子单


# 交易大市场， 不是具体品种
class TradeMarket(Enum):
    """
    交易市场类型定义
    ..  py:class:: TrdMarket
     ..  py:attribute:: NONE
      未知not
     ..  py:attribute:: HK
      港股交易
     ..  py:attribute:: US
      美股交易
     ..  py:attribute:: CN
      A股交易
     ..  py:attribute:: HKCC
      A股通交易
    """
    NONE = "N/A"  # 未知
    HK = "HK"  # 香港市场
    US = "US"  # 美国市场
    CN = "CN"  # 大陆市场
    HKCC = "HKCC"  # 香港A股通市场
    FUTURES = "FUTURES"  # 期货市场
    # SG = "SG"


class TradeMode(Enum):
    """Trading mode"""
    BACKTEST = "BACKTEST"
    LIVETRADE = "LIVETRADE"
    SIMULATE = "SIMULATE"


class Exchange(Enum):
    """Exchanges"""
    SEHK = "SEHK"  # Stock Exchange of Hong Kong
    HKFE = "HKFE"  # Hong Kong Futures Exchange
    SSE = "SSE"  # Shanghai Stock Exchange
    SZSE = "SZSE"  # Shenzhen Stock Exchange
    CME = "CME"  # S&P Index, AUDUSD, etc 期货交易所
    COMEX = "COMEX"  # Gold, silver, copper, etc
    NYMEX = "NYMEX"  # Brent Oil, etc 纽约商品期货交易所
    CBOT = "CBOT"  # Bonds, soybean, rice, etc
    ECBOT = "ECBOT"  # Bonds, soybean, rice, etc
    SGE = "SGE"  # Shanghai Gold Exchange
    IDEALPRO = "IDEALPRO"  # currency
    GLOBEX = "GLOBEX"  # futures
    SMART = "SMART"  # SMART in IB
    SGX = "SGX"  # Singapore Exchange (https://www.sgx.com/) 新加坡
    ICE = "ICE"  # Products: QO (Brent Oil)
    NASDAQ = "NASDAQ"  # 纳斯达克证券交易所
    NYSE = "NYSE"  # 纽约证券交易所
    ASE = "ASE"  # 美国证券交易所


class Cash(Enum):
    """Currency"""
    NONE = "UNKNOWN"
    HKD = "HKD"
    USD = "USD"
    CNH = "CNH"


class Direction(Enum):
    """Direction of order/trade/position."""
    LONG = "LONG"
    SHORT = "SHORT"
    NET = "NET"


class Offset(Enum):
    """Offset of order/trade.
    开仓、平仓（股票没有开平仓概念）
    """
    NONE = ""
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSETODAY = "CLOSETODAY"
    CLOSEYESTERDAY = "CLOSEYESTERDAY"
