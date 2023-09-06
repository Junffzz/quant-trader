import os
import json
import requests
import pandas as pd
from sqlalchemy import create_engine

sql_path = 'sqlite:///'


def sql_engine(my_path='c:\\zjy\\Mystock', db_name='stock_data.db'):
    if not os.path.exists(my_path):
        os.makedirs(my_path)
    file_path = os.path.join(my_path, db_name)
    file_path = os.path.abspath(file_path)
    db_path = sql_path + file_path
    engine = create_engine(db_path)
    return engine


def cut_data(data, cut_points, labels=None):
    min_num = data.min()
    max_num = data.max()
    break_points = [min_num] + cut_points + [max_num]
    if not labels:
        labels = range(len(cut_points) + 1)
    else:
        labels = [labels[i] for i in range(len(cut_points) + 1)]
    dataBin = pd.cut(data, bins=break_points,
                     labels=labels, include_lowest=True)
    return dataBin
