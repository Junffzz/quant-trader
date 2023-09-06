# -*- coding: utf-8 -*-
"""
Created on Fri Sep 30 13:38:58 2022

@author: Jinyi Zhang
"""

import requests
import pandas as pd
import signal
from tqdm import tqdm
from func_timeout import func_set_timeout
import multitasking
from bs4 import BeautifulSoup
from datetime import datetime
from functools import lru_cache
from app.facade.helper import ths_code_name, trans_num,ths_header
from app.facade.trade import latest_trade_date
from app.utils import demjson


# 同花顺概念板块
# 获取同花顺概念板块名称
def ths_index_name(flag='概念'):
    '''
    获取同花顺概念或行业板块名称
    flag='概念板块' or '行业板块'
    '''
    if flag == '概念板块' or flag == '概念':
        return ths_concept_name()
    else:
        names = list(ths_code_name.values())
    return names


# 概念板块成分股
def ths_index_member(code=None):
    '''
    获取同花顺概念或行业板块成份股
    code:输入板块行业或概念代码或简称
    '''
    code_list = list(ths_code_name) + list(ths_code_name.values())
    if code in code_list:
        return ths_industry_member(code)
    else:
        return ths_concept_member(code)


# 多线程获取同花顺指数数据
def ths_index_price(flag='概念'):
    df_list = []
    codes = ths_index_name(flag)
    pbar = tqdm(total=len(codes))

    @multitasking.task
    @func_set_timeout(5)
    def run(code):
        try:
            temp = ths_index_data(code)
            temp[code] = temp.close
            df_list.append(temp[code])
            pbar.update()
        except:
            pass

    for code in codes:
        try:
            run(code)
        except:
            continue
    multitasking.wait_for_tasks()
    # 转换为dataframe
    df = pd.concat(df_list, axis=1)
    return df.dropna(axis=1)


# 概念指数行情数据
def ths_index_data(code=None):
    '''
    获取同花顺概念或行业板块指数行情数据
    code:输入板块行业或概念代码或简称
    '''
    code_list = list(ths_code_name) + list(ths_code_name.values())
    if code in code_list:
        return ths_industry_data(code)
    else:
        return ths_concept_data(code)


def ths_name_code(code):
    """
    获取同花顺行业对应代码
    """
    if code.isdigit():
        return code
    name_code = {value: key for key, value in ths_code_name.items()}
    code = name_code[code]
    return code


def ths_industry_member(code="机器人"):
    """
    获取同花顺行业板块的成份股
    http://q.10jqka.com.cn/thshy/detail/code/881121/
    code:输入板块名称或代码，如code='881101'或'种植业与林业'
    """

    if code.isdigit():
        symbol = code
    else:
        symbol = ths_name_code(code)
    page = 1
    url = f"http://q.10jqka.com.cn/thshy/detail/field/199112/order/desc/page/{page}/ajax/1/code/{symbol}"
    res = requests.get(url, headers=ths_header())
    soup = BeautifulSoup(res.text, "lxml")
    try:
        page_num = int(
            soup.find_all("a", attrs={"class": "changePage"})[-1]["page"])
    except:
        page_num = 1
    df = pd.DataFrame()
    for page in tqdm(range(1, page_num + 1), leave=False):
        res = requests.get(url, headers=ths_header())
        temp = pd.read_html(res.text)[0]
        df = pd.concat([df, temp], ignore_index=True)
    df.rename({"涨跌幅(%)": "涨跌幅", "涨速(%)": "涨速",
               "换手(%)": "换手", "振幅(%)": "振幅", '成交额': '成交额(亿)',
               '流通股': '流通股(亿)', '流通市值': '流通市值(亿)',
               }, inplace=True, axis=1, )
    del df["加自选"]
    del df['序号']
    del df['涨跌']
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df[['成交额(亿)', '流通股(亿)', '流通市值(亿)']] = df[['成交额(亿)', '流通股(亿)',
                                                           '流通市值(亿)']].apply(lambda s: s.str.strip('亿'))
    ignore_cols = ['代码', '名称']
    df = trans_num(df, ignore_cols)
    return df.drop_duplicates()


def ths_industry_data(code="半导体及元件", start="20200101", end=None):
    """
    获取同花顺行业板块指数数据
    http://q.10jqka.com.cn/gn/detail/code/301558/
    start: 开始时间
    end: 结束时间
    """
    if end is None:
        end = latest_trade_date()
    if code.isdigit():
        symbol = code
    else:
        symbol = ths_name_code(code)
    df = pd.DataFrame()
    current_year = datetime.now().year
    for year in range(2000, current_year + 1):
        url = f"http://d.10jqka.com.cn/v4/line/bk_{symbol}/01/{year}.js"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
            "Referer": "http://q.10jqka.com.cn",
            "Host": "d.10jqka.com.cn",
        }
        res = requests.get(url, headers=headers)
        data_text = res.text
        try:
            demjson.decode(data_text[data_text.find("{"): -1])
        except:
            continue
        temp_df = demjson.decode(data_text[data_text.find("{"): -1])
        temp_df = pd.DataFrame(temp_df["data"].split(";"))
        temp_df = temp_df.iloc[:, 0].str.split(",", expand=True)
        df = pd.concat([df, temp_df], ignore_index=True)

    if len(df.columns) == 11:
        df.columns = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量",
                      "成交额", "_", "_", "_", "_", ]
    else:
        df.columns = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量",
                      "成交额", "_", "_", "_", "_", "_", ]

    df["日期"] = pd.to_datetime(df["日期"]).dt.date
    c1 = pd.to_datetime(start) < df["日期"]
    c2 = pd.to_datetime(end) > df["日期"]
    df = df[c1 & c2]
    cols1 = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量"]
    cols2 = ['date', 'open', 'high', 'low', 'close', 'volume']
    df = df.rename(columns=dict(zip(cols1, cols2)))[cols2]
    df.set_index('date', inplace=True)
    ignore_cols = ['date']
    df = trans_num(df, ignore_cols)
    return df


@lru_cache()
def ths_concept_name_code():
    """
    同花顺概念板块概念名称
    http://q.10jqka.com.cn/gn/detail/code/301558/
    """
    page = 1
    url = f"http://q.10jqka.com.cn/gn/index/field/addtime/order/desc/page/{page}/ajax/1/"

    res = requests.get(url, headers=ths_header())
    soup = BeautifulSoup(res.text, "lxml")
    total_page = soup.find("span", attrs={"class": "page_info"}).text.split("/")[1]
    df = pd.DataFrame()
    for page in tqdm(range(1, int(total_page) + 1), leave=False):
        r = requests.get(url, headers=ths_header())
        soup = BeautifulSoup(r.text, "lxml")
        url_list = []
        for item in (
                soup.find("table", attrs={"class": "m-table m-pager-table"})
                        .find("tbody")
                        .find_all("tr")):
            inner_url = item.find_all("td")[1].find("a")["href"]
            url_list.append(inner_url)
        temp_df = pd.read_html(r.text)[0]
        temp_df["网址"] = url_list
        df = pd.concat([df, temp_df], ignore_index=True)
    df = df[["日期", "概念名称", "成分股数量", "网址"]]
    df["日期"] = pd.to_datetime(df["日期"]).dt.date
    df["成分股数量"] = pd.to_numeric(df["成分股数量"])
    df["代码"] = df["网址"].str.split("/", expand=True).iloc[:, 6]
    df.drop_duplicates(keep="last", inplace=True)
    df.reset_index(inplace=True, drop=True)

    # 处理遗漏的板块
    url = "http://q.10jqka.com.cn/gn/detail/code/301558/"
    r = requests.get(url, headers=ths_header())
    soup = BeautifulSoup(r.text, "lxml")
    need_list = [
        item.find_all("a")
        for item in soup.find_all(attrs={"class": "cate_group"})
    ]
    temp_list = []
    for item in need_list:
        temp_list.extend(item)
    temp_df = pd.DataFrame(
        [
            [item.text for item in temp_list],
            [item["href"] for item in temp_list],
        ]
    ).T
    temp_df.columns = ["概念名称", "网址"]
    temp_df["日期"] = None
    temp_df["成分股数量"] = None
    temp_df["代码"] = (
        temp_df["网址"].str.split("/", expand=True).iloc[:, 6].tolist()
    )
    temp_df = temp_df[["日期", "概念名称", "成分股数量", "网址", "代码"]]
    df = pd.concat([df, temp_df], ignore_index=True)
    df.drop_duplicates(subset=["概念名称"], keep="first", inplace=True)
    return df


def ths_concept_name():
    """
    获取同花顺概念板块-概念名称
    """
    ths_df = ths_concept_name_code()
    name_list = ths_df["概念名称"].tolist()
    return name_list


def ths_concept_code():
    """
    获取同花顺概念板块-概念代码
    """
    ths_df = ths_concept_name_code()
    name_list = ths_df["概念名称"].tolist()
    code_list = list(ths_df['代码'])
    name_code_dict = dict(zip(name_list, code_list))
    return name_code_dict


def ths_concept_member(code="阿里巴巴概念"):
    """
    同花顺-板块-概念板块-成份股
    http://q.10jqka.com.cn/gn/detail/code/301558/
    code: 板块名称或代码
    """
    if code.isdigit():
        symbol = code
    else:
        symbol = ths_concept_code()[code]
    page = 1
    url = f"http://q.10jqka.com.cn/gn/detail/field/264648/order/desc/page/{page}/ajax/1/code/{symbol}"
    res = requests.get(url, headers=ths_header())
    soup = BeautifulSoup(res.text, "lxml")
    try:
        page_num = int(
            soup.find_all("a", attrs={"class": "changePage"})[-1]["page"]
        )
    except:
        page_num = 1
    df = pd.DataFrame()
    for page in tqdm(range(1, page_num + 1), leave=False):
        r = requests.get(url, headers=ths_header())
        temp_df = pd.read_html(r.text)[0]
        df = pd.concat([df, temp_df], ignore_index=True)
    df.rename({"涨跌幅(%)": "涨跌幅", "涨速(%)": "涨速",
               "换手(%)": "换手", "振幅(%)": "振幅", '成交额': '成交额(亿)',
               '流通股': '流通股(亿)', '流通市值': '流通市值(亿)',
               }, inplace=True, axis=1, )
    del df["加自选"]
    del df['序号']
    del df['涨跌']
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df[['成交额(亿)', '流通股(亿)', '流通市值(亿)']] = df[['成交额(亿)', '流通股(亿)',
                                                           '流通市值(亿)']].apply(lambda s: s.str.strip('亿'))
    ignore_cols = ['代码', '名称']
    df = trans_num(df, ignore_cols)
    return df.drop_duplicates()


def ths_concept_data(code='白酒概念', start="2020"):
    """
    同花顺-板块-概念板块-指数数据
    http://q.10jqka.com.cn/gn/detail/code/301558/
    start: 开始年份; e.g., 2019
    """
    code_map = ths_concept_code()
    symbol_url = f"http://q.10jqka.com.cn/gn/detail/code/{code_map[code]}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
    }
    r = requests.get(symbol_url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")
    symbol_code = (
        soup.find("div", attrs={"class": "board-hq"}).find("span").text
    )
    df = pd.DataFrame()
    current_year = datetime.now().year
    for year in range(int(start), current_year + 1):
        url = f"http://d.10jqka.com.cn/v4/line/bk_{symbol_code}/01/{year}.js"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
            "Referer": "http://q.10jqka.com.cn",
            "Host": "d.10jqka.com.cn",
        }
        r = requests.get(url, headers=headers)
        data_text = r.text
        try:
            demjson.decode(data_text[data_text.find("{"): -1])
        except:
            continue
        temp_df = demjson.decode(data_text[data_text.find("{"): -1])
        temp_df = pd.DataFrame(temp_df["data"].split(";"))
        temp_df = temp_df.iloc[:, 0].str.split(",", expand=True)
        df = pd.concat([df, temp_df], ignore_index=True)
    if df.columns.shape[0] == 12:
        df.columns = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量",
                      "成交额", "_", "_", "_", "_", "_", ]
    else:
        df.columns = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量",
                      "成交额", "_", "_", "_", "_", ]
    df = df[["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量", "成交额", ]]
    cols1 = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量"]
    cols2 = ['date', 'open', 'high', 'low', 'close', 'volume']
    df = df.rename(columns=dict(zip(cols1, cols2)))[cols2]
    df.set_index('date', inplace=True)
    ignore_cols = ['date']
    df = trans_num(df, ignore_cols)
    return df