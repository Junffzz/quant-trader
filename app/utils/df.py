#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd

def trans_num(df, ignore_cols):
    '''df为需要转换数据类型的dataframe
    ignore_cols为dataframe中忽略要转换的列名的list
    如ignore_cols=['代码','名称','所处行业']
    '''
    trans_cols = list(set(df.columns) - set(ignore_cols))
    df[trans_cols] = df[trans_cols].apply(lambda s: pd.to_numeric(s, errors='coerce'))
    return df