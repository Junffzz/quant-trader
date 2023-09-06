
## 技术选型
web服务框架:tornado

## 流程设计

### worker服务
1.定时任务

2.每天存储当天的日k交易数据

### 概念
offset=CLOSE时，direction会统一转换为SHORT
#### STOCK
买: LONG OPEN
卖: SHORT CLOSE

#### FUTURES
买：None:(Long,Open); Short:(Long,Close)
卖：None:(Short,Open); Long:(Short,Close)

