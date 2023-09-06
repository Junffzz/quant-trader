SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

---- 参考：https://www.myquant.cn/docs/python/python_object_trade#Cash%20-%20资金对象
---- 枚举常量：https://www.myquant.cn/docs/python/python_enum_constant#OrderDuration%20-%20委托时间属性

----一个账户对应多个资金对象
CREATE TABLE `account` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(32) NOT NULL DEFAULT '',
  `password` char(32) NOT NULL DEFAULT '',
  `account_name` varchar(60) NOT NULL DEFAULT '',
  `email` varchar(120) NOT NULL DEFAULT '',
  `avatar` varchar(150) NOT NULL DEFAULT '',
  `gender` enum('unknown','male','female') NOT NULL DEFAULT 'unknown',
  `description` varchar(200) NOT NULL DEFAULT '' ,
  `login_num` tinyint(1) UNSIGNED NOT NULL DEFAULT '0',
  `last_login_ip` varchar(16) NOT NULL DEFAULT '',
  `last_login_time` datetime NOT NULL DEFAULT '0001-01-01 00:00:00',
  `status` enum('default','banned','locked','deleted') NOT NULL DEFAULT 'default',
  `created_time` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_time` datetime NOT NULL DEFAULT current_timestamp() COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 账户资金对象
CREATE TABLE `account_cash` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `account_id` int(10) NOT NULL DEFAULT 0,
  `currency` tinyint(2) NOT NULL DEFAULT 0 COMMENT '币种',
  `nav` float NOT NULL DEFAULT 0 COMMENT '总资金',
  `fpnl` float NOT NULL DEFAULT 0 COMMENT '浮动盈亏',
  `frozen` float NOT NULL DEFAULT 0 COMMENT '持仓占用资金 （仅期货实盘支持，股票实盘不支持）',
  `order_frozen` float NOT NULL DEFAULT 0 COMMENT '冻结资金',
  `available` float NOT NULL DEFAULT 0 COMMENT '可用资金',
  `market_value` float unsigned NOT NULL DEFAULT 0 COMMENT '市值',
  `balance` float NOT NULL DEFAULT 0 COMMENT '资金余额',
  `status` enum('default','banned','locked','deleted') NOT NULL DEFAULT 'default' COMMENT '用户状态 0：禁用 1：正常',
  `created_time` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_time` datetime NOT NULL DEFAULT current_timestamp() COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `accountid_index` (`account_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---委托对象
CREATE TABLE `orders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `strategy_id` int(10) NOT NULL DEFAULT 0 COMMENT '策略ID',
  `account_id` int(10) NOT NULL DEFAULT 0,
  `account_name` varchar(80) NOT NULL DEFAULT '',
  `cl_ord_id` varchar(80) NOT NULL DEFAULT '' COMMENT '委托客户端ID，下单生成，固定不变（平台维护，下单唯一标识）',
  `counter_order_id` varchar(80) NOT NULL DEFAULT '' COMMENT '委托柜台ID（系统字段，下单不会立刻生成，委托报到柜台才会生成）',
  `ex_ord_id` varchar(32) NOT NULL DEFAULT '' COMMENT '委托交易所ID（系统字段，下单不会立刻生成，委托报到柜台才会生成）',
  `algo_order_id` varchar(32) NOT NULL DEFAULT '' COMMENT '算法单ID',
  `symbol` varchar(60) NOT NULL DEFAULT '' COMMENT '标的代码',
  `side` tinyint(1) NOT NULL DEFAULT 0 COMMENT '委托方向 unknown:0 buy:1 sell:2',
  `position_effect` tinyint(1) NOT NULL DEFAULT 0 COMMENT '开平标志Unknown = 0 ,Open = 1开仓 ,Close = 2 平仓, 具体语义取决于对应的交易所,CloseToday = 3 平今仓,CloseYesterday = 4 平昨仓',
  `position_side` tinyint(1) NOT NULL DEFAULT 0 COMMENT '持仓方向.Unknown = 0,Long = 1 多方向,Short = 2空方向',
  `order_type` tinyint(1) NOT NULL DEFAULT 0 COMMENT '委托类型 深市：’1’市价， ‘2’限价， ‘U’本方最优，沪市：’A’新增委托订单，’D’删除委托订单',
  `order_duration` tinyint(1) NOT NULL DEFAULT 0 COMMENT '委托时间属性(仅实盘有效).OrderDuration_Unknown = 0,FAK = 1 即时成交剩余撤销(fill and kill),FOK = 2 即时全额成交或撤销(fill or kill),GFD = 3 # 当日有效(good for day),GFS = 4 本节有效(good for section),GTD = 5 指定日期前有效(goodltilldate),GTC = 6  # 撤销前有效(goodtillcancel),GFA = 7 # 集合竞价前有效(good for auction),AHT = 8 # 盘后定价交易(after hour trading)',
  `order_qualifier` tinyint(1) NOT NULL DEFAULT 0 COMMENT '委托成交属性(仅实盘有效).Unknown = 0,BOC  = 1 对方最优价格(best of counterparty),BOP = 2 己方最优价格(best of party),B5TC = 3  最优五档剩余撤销(best 5 then cancel),B5TL = 4  最优五档剩余转限价(best 5 then limit)',
  `order_business` tinyint(1) NOT NULL DEFAULT 0 COMMENT '委托业务属性.NORMAL = 0 普通交易。默认值为空，以保持向前兼容,CREDIT_BOM = 200 # 融资买入(buying on margin),CREDIT_SS = 201       # 融券卖出(short selling),CREDIT_RSBBS = 202 # 买券还券(repay share by buying share),CREDIT_RCBSS = 203 # 卖券还款(repay cash by selling share),CREDIT_DRS = 204 # 直接还券(directly repay share),CREDIT_BOC = 207  # 担保品买入(buying on collateral),CREDIT_SOC = 208 # 担保品卖出(selling on collateral),CREDIT_CI = 209  # 担保品转入(collateral in),CREDIT_CO = 210 # 担保品转出(collateral out),BOND_CONVERTIBLE_CALL = 402  #可转债转股,BOND_CONVERTIBLE_PUT = 403  #可转债回售,BOND_CONVERTIBLE_PUT_CANCEL = 404  #可转债回售撤销',
  `ord_rej_reason` tinyint(1) NOT NULL DEFAULT 0 COMMENT '委托拒绝原因.Unknown = 0  # 未知原因,RiskRuleCheckFailed = 1  # 不符合风控规则,NoEnoughCash = 2 # 资金不足,NoEnoughPosition = 3  # 仓位不足,IllegalAccountId = 4 # 非法账户ID,IllegalStrategyId = 5 # 非法策略ID,IllegalSymbol = 6 # 非法交易标的,IllegalVolume = 7 # 非法委托量,IllegalPrice = 8 # 非法委托价,AccountDisabled = 10 # 交易账号被禁止交易,AccountDisconnected = 11 # 交易账号未连接,AccountLoggedout = 12 # 交易账号未登录,NotInTradingSession = 13  # 非交易时段,OrderTypeNotSupported = 14 # 委托类型不支持,Throttle = 15 # 流控限制',
  `ord_rej_reason_detail` varchar(200) NOT NULL DEFAULT '0' COMMENT '委托拒绝原因描述',
  `position_src` int(10) NOT NULL DEFAULT 0 COMMENT '头寸来源（系统字段）',
  `price` float NOT NULL DEFAULT 0 COMMENT '委托价',
  `volume` int(10) NOT NULL DEFAULT 0 COMMENT '委托量',
  `value` int(10) NOT NULL DEFAULT 0 COMMENT '委托额',
  `percent` float NOT NULL DEFAULT 0 COMMENT '委托百分比',
  `target_volume` int(10) NOT NULL DEFAULT 0 COMMENT '委托目标量',
  `target_value` int(10) NOT NULL DEFAULT 0 COMMENT '委托目标额',
  `target_percent` float NOT NULL DEFAULT 0 COMMENT '委托目标百分比',
  `filled_volume` int(10) NOT NULL DEFAULT 0 COMMENT '已成量 （一笔委托对应多笔成交为累计值）',
  `filled_vwap` float NOT NULL DEFAULT 0 COMMENT '已成均价，公式为(price*(1+backtest_slippage_ratio)) （仅股票实盘支持，期货实盘不支持）',
  `filled_amount` float NOT NULL DEFAULT 0 COMMENT '已成金额，公式为(filled_volume*filled_vwap) （仅股票实盘支持，期货实盘不支持）',
  `status` tinyint(1) unsigned NOT NULL DEFAULT 1 COMMENT '委托状态 unknow:0 已报new:1 PartiallyFilled:2 Filled:3 Canceled:5 PendingCancel:6 Rejected:8 Suspended:9 PendingNew:10 Expired:12',
  `created_time` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_time` datetime NOT NULL DEFAULT current_timestamp() COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `clordid_index` (`cl_ord_id`) USING BTREE,
  KEY `accountid_index` (`account_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 持仓对象（账户持仓一对多）
CREATE TABLE `account_positions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `account_id` int(10) NOT NULL DEFAULT 0,
  `symbol` varchar(60) NOT NULL DEFAULT '' COMMENT '标的代码',
  `side` tinyint(1) NOT NULL DEFAULT 0 COMMENT '持仓方向 unknown:0 buy:1 sell:2',
  `volume` int(10) NOT NULL DEFAULT 0 COMMENT '委托量',
  `volume_today` int(10) NOT NULL DEFAULT 0 COMMENT '今日买入量',
  `market_value` float NOT NULL DEFAULT 0 COMMENT '持仓市值',
  `vwap` float NOT NULL DEFAULT 0 COMMENT '持仓均价 new_vwap=((position.vwap * position.volume)+(trade.volume*trade.price))/(position.volume+trade.volume) （实盘时，期货跨天持仓，会自动变成昨结价，仿真是开仓均价）',
  `vwap_open` float NOT NULL DEFAULT 0 COMMENT '开仓均价（期货适用，实盘适用）',
  `vwap_diluted` float NOT NULL DEFAULT 0 COMMENT '摊薄成本（股票适用，实盘适用）',
  `amount` float NOT NULL DEFAULT 0 COMMENT '持仓额 (volume*vwap*multiplier)',
  `price` float NOT NULL DEFAULT 0 COMMENT '当前行情价格（回测时值为0）',
  `fpnl` float NOT NULL DEFAULT 0 COMMENT '持仓浮动盈亏 ((price - vwap) * volume * multiplier) （基于效率的考虑，回测模式fpnl只有仓位变化时或者一天更新一次,仿真模式3s更新一次, 回测的price为当天的收盘价） （根据持仓均价计算）',
  `fpnl_open` float NOT NULL DEFAULT 0 COMMENT '浮动盈亏（期货适用， 根据开仓均价计算）',
  `cost` float NOT NULL DEFAULT 0 COMMENT '持仓成本 (vwap * volume * multiplier * margin_ratio)',
  `order_frozen` int(10) NOT NULL DEFAULT 0 COMMENT '挂单冻结仓位',
  `order_frozen_today` int(10) NOT NULL DEFAULT 0 COMMENT '挂单冻结今仓仓位(仅上期所和上海能源交易所标的支持)',
  `available` int(10) NOT NULL DEFAULT 0 COMMENT '非挂单冻结仓位 ，公式为(volume - order_frozen); 如果要得到可平昨仓位，公式为 (available - available_today)' ,
  `available_today` int(10) NOT NULL DEFAULT 0 COMMENT '非挂单冻结今仓位，公式为 (volume_today - order_frozen_today)(仅上期所和上海能源交易所标的支持)',
  `available_now` int(10) NOT NULL DEFAULT 0 COMMENT '当前可用仓位',
  `credit_position_sellable_volume` int(10) NOT NULL DEFAULT 0 COMMENT '可卖担保品数',
  `created_time` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_time` datetime NOT NULL DEFAULT current_timestamp() COMMENT '更新时间',
  PRIMARY KEY (`id`)
  KEY `accountid_index` (`account_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

---绩效指标对象
CREATE TABLE `indicator` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `account_id` int(10) NOT NULL DEFAULT 0,
  `pnl_ratio` float NOT NULL DEFAULT 0 COMMENT '累计收益率 (pnl/cum_inout)',
  `pnl_ratio_annual` float NOT NULL DEFAULT 0 COMMENT '年化收益率 (pnl_ratio/自然天数*365)',
  `sharp_ratio` float NOT NULL DEFAULT 0 COMMENT '夏普比率 （[E(Rp)-Rf]/δp*sqrt(250),E(Rp) = mean(pnl_ratio),Rf = 0,δp = std(pnl_ratio) )',
  `max_drawdown` float NOT NULL DEFAULT 0 COMMENT '最大回撤 max_drawdown=max（Di-Dj）/Di；D为某一天的净值（j>i)',
  `risk_ratio` float NOT NULL DEFAULT 0 COMMENT '风险比率 （持仓市值/nav）',
  `calmar_ratio` float NOT NULL DEFAULT 0 COMMENT '卡玛比率 年化收益率/最大回撤',
  `open_count` int(10) NOT NULL DEFAULT 0 COMMENT '开仓次数',
  `close_count` int(10) NOT NULL DEFAULT 0 COMMENT '平仓次数',
  `win_count` int(10) NOT NULL DEFAULT 0 COMMENT '盈利次数（平仓价格大于持仓均价vwap的次数）',
  `lose_count` int(10) NOT NULL DEFAULT 0 COMMENT '亏损次数 （平仓价格小于或者等于持仓均价vwap的次数）',
  `win_ratio` float NOT NULL DEFAULT 0 COMMENT '胜率 (win_count / (win_count + lose_count))',
  `count` int(10) NOT NULL DEFAULT 0 COMMENT '',
  `created_time` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_time` datetime NOT NULL DEFAULT current_timestamp() COMMENT '更新时间',
  PRIMARY KEY (`id`)
  KEY `accountid_index` (`account_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE `stocks_basic` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `region_tag` varchar(32) NOT NULL DEFAULT '',
  `name` varchar(60) NOT NULL DEFAULT '',
  `fullname` varchar(120) NOT NULL DEFAULT '',
  `enname` varchar(120) NOT NULL DEFAULT '',
  `ts_code` varchar(30) NOT NULL DEFAULT '' COMMENT '如：000001.SZ',
  `symbol` varchar(30) NOT NULL DEFAULT '' COMMENT '如：000001',
  `exchange` varchar(20) NOT NULL DEFAULT '' COMMENT '交易所 SSE上交所,SZSE深交所,CFFEX 中金所,SHFE 上期所,CZCE 郑商所,DCE 大商所,INE 上能源',
  `industry` varchar(60) DEFAULT '' COMMENT '所属行业',
  `listed_date` varchar(10) NOT NULL DEFAULT '',
  `delisted_date` varchar(10) DEFAULT NULL COMMENT '退市日期',
  `listed_status` varchar(10) NOT NULL DEFAULT '' COMMENT '上市状态',
  `classify` varchar(20) NOT NULL DEFAULT '' COMMENT '美股分类ADR/GDR/EQ',
  `is_hs` varchar(10) DEFAULT 'N' COMMENT '是否沪深港通标的，N否 H沪股通 S深股通',
  `curr_type` varchar(20) NOT NULL DEFAULT '' COMMENT '交易货币',
  `market` varchar(60) NOT NULL DEFAULT '' COMMENT '市场类型（主板/创业板/科创板/CDR）',
  `area` varchar(60) DEFAULT '',
  `created_time` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_time` datetime NOT NULL DEFAULT current_timestamp() COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `tscode_index` (`ts_code`) USING BTREE,
  UNIQUE KEY `symbol_index` (`symbol`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=8192 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;