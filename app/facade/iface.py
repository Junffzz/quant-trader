#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import abc
from abc import abstractmethod

class IStock(abc.ABC):
    """
    获取股票、指数、债券、期货、基金等历史K线行情
    code可以是股票或指数（包括美股港股等）代码或简称
    start和end为起始和结束日期，年月日
    freq:时间频率，默认日，1 : 分钟；5 : 5 分钟；15 : 15 分钟；30 : 30 分钟；
    60 : 60 分钟；101或'D'或'd'：日；102或‘w’或'W'：周; 103或'm'或'M': 月
    注意1分钟只能获取最近5个交易日一分钟数据
    fqt:复权类型，0：不复权，1：前复权；2：后复权，默认前复权
    """

    @abstractmethod
    def get_kline_data(self, code_list, start, end=None, freq='d', fqt=1): pass  # 获取k线数据

    '''
    获取财务数据
    查询财务数据，详细的财务数据表及字段描述请点击财务数据文档查看，Query 对象的使用方法请参考Query的简单教程

    date和statDate参数只能传入一个:
    
    传入date时, 查询指定日期date收盘后所能看到的最近(对市值表来说, 最近一天, 对其他表来说, 最近一个季度)的数据, 我们会查找上市公司在这个日期之前(包括此日期)发布的数据, 不会有未来函数.
    传入statDate时, 查询 statDate 指定的季度或者年份的财务数据. 注意:
    由于公司发布财报不及时, 一般是看不到当季度或年份的财务报表的, 回测中使用这个数据可能会有未来函数, 请注意规避.
    由于估值表每天更新, 当按季度或者年份查询时, 返回季度或者年份最后一天的数据
    由于“资产负债数据”这个表是存量性质的， 查询年度数据是返回第四季度的数据。
    银行业、券商、保险专项数据只有年报数据，需传入statDate参数，当传入 date 参数 或 statDate 传入季度时返回空，请自行避免未来函数。
    当 date 和 statDate 都不传入时, 相当于使用 date 参数, date 的默认值下面会描述.
    
    参数

    query_object: 一个sqlalchemy.orm.query.Query对象, 可以通过全局的 query 函数获取 Query 对象,Query对象的简单使用教程
    date: 查询日期, 一个字符串(格式类似'2015-10-15')或者[datetime.date]/[datetime.datetime]对象, 可以是None, 使用默认日期. 这个默认日期在回测和研究模块上有点差别:
    回测模块: 默认值会随着回测日期变化而变化, 等于 context.current_dt 的前一天(实际生活中我们只能看到前一天的财报和市值数据, 所以要用前一天)
    研究模块: 使用平台财务数据的最新日期, 一般是昨天.
    statDate: 财报统计的季度或者年份, 一个字符串, 有两种格式:
    季度: 格式是: 年 + 'q' + 季度序号, 例如: '2015q1', '2013q4'.
    年份: 格式就是年份的数字, 例如: '2015', '2016'.
    返回 返回一个 [pandas.DataFrame], 每一行对应数据库返回的每一行(可能是几个表的联合查询结果的一行), 列索引是你查询的所有字段 注意：
    
    为了防止返回数据量过大, 我们每次最多返回5000行
    当相关股票上市前、退市后，财务数据返回各字段为空
    '''

    @abstractmethod
    def get_fundamentals(query_object, date=None, statDate=None): pass
