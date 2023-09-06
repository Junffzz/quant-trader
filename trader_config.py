# -*- coding: utf-8 -*-

BACKTEST_GATEWAY = {
    "broker_name": "BACKTEST",
    "broker_account": "",
    "host": "",
    "port": -1,
    "pwd_unlock": -1,
}

IB_GATEWAY = {
    "broker_name": "IB",
    "broker_account": "",
    "host": "127.0.0.1",
    "port": 7497,
    "clientid": 1,
    "pwd_unlock": -1,
}

CQG_GATEWAY = {
    "broker_name": "CQG",
    "broker_account": "Demo",
    "password": "pass",
    "host": "127.0.0.1",
    "port": 2823,
}

FUTU_GATEWAY = {
    "broker_name": "FUTU",
    "broker_account": "28028766",
    "host": "182.44.51.119",
    "port": 11111,
    "pwd_unlock": 199212,
    "rsa_file": "/Users/ZhaoJunfeng/tools/futu_openD.rsa.private",
}

FUTUFUTURES_GATEWAY = {
    "broker_name": "FUTUFUTURES",
    "broker_account": "TEST123456",
    "host": "127.0.0.1",
    "port": 11111,
    "pwd_unlock": 123456,
}

GATEWAYS = {
    "Ib": IB_GATEWAY,
    "Backtest": BACKTEST_GATEWAY,
    "Cqg": CQG_GATEWAY,
    "Futu": FUTU_GATEWAY,
    "Futufutures": FUTUFUTURES_GATEWAY
}

TIME_STEP = 60000 * 60 * 24  # time step in milliseconds

DATA_PATH = {
    "kline": "/Users/ZhaoJunfeng/workspace/python/quant-trader/data/k_line",
}

DATA_MODEL = {
    "kline": "Bar",
}

DB = {
    "sqlite3": "/Users/ZhaoJunfeng/workspace/python/quant-trader/data",
    "mariadb": "/Users/ZhaoJunfeng/workspace/python/quant-trader/data"
}

CLICKHOUSE = {
    "host": "localhost",
    "port": 9000,
    "user": "default",
    "password": ""
}

MARIADB = {
    "host": "182.44.51.119",
    "port": 3306,
    "user": "admin",
    "password": "zjf20230319",
    "database": "quant_trader_test"
}

ACTIVATED_PLUGINS = ["mariadb", "analysis", "dingtalk"]
LOCAL_PACKAGE_PATHS = []
ADD_LOCAL_PACKAGE_PATHS_TO_SYSPATH = False

DINGTALK_TOKEN = "04d64ff4c7b463fcf2cd3d47e6ebba1b2df1776cd6f9e612aa4a147106fdae57"
DINGTALK_SECRET = "SEC001539b6ba3feeac2c646e54973c86bef86bed2184692acf5faf5a90c9f67555"

AUTO_OPEN_PLOT = True
IGNORE_TIMESTEP_OVERFLOW = False
DATA_FFILL = True
