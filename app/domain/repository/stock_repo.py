import mariadb

import pandas as pd
import app.infra.db as db


class StockRepo:
    def __init__(self):
        self.db = db.get_mariadb_conn()
        self.db_engine = db.mariadb_engine()
        self.table = "stocks_basic"
        self._fields = ['name', 'ts_code', 'region_tag', 'fullname', 'enname', 'symbol', 'exchange', 'industry',
                        'listed_date', 'delisted_date', 'list_status', 'classify', 'is_hs', 'curr_type', 'stores',
                        'area']

    def get_stock_basic(self, region_tag: str, where: str = "listed_status='L'",
                        fields=['ts_code', 'name', 'symbol', 'exchange', 'industry']) -> list:
        if len(region_tag) == 0:
            return
        if len(where) > 0:
            where = f' WHERE {where}'

        columns = ','.join(fields)
        sql = f'SELECT {columns} FROM {self.table} {where} ORDER BY id ASC'
        cursor = self.db.cursor()
        result = []
        try:
            cursor.execute(sql)
            self.db.commit()
            for row in cursor:
                print(row)
                result.append(row)

        except Exception as e:
            self.db.rollback()
            print(f"Error: {e}")

        cursor.close()
        return result

    def adds(self, data_list: list):
        if data_list is False:
            return

        sql = f'INSERT INTO {self.table} (name,ts_code,region_tag,fullname,enname,symbol,exchange,industry,listed_date,delisted_date,listed_status,classify,is_hs,curr_type,stores,area) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        cursor = self.db.cursor()
        try:
            cursor.executemany(sql, data_list)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error: {e}")

        cursor.close()

    def upset(self, data: pd.Series | dict):
        sql = "INSERT INTO {self.table} (first_name,last_name) VALUES (?, ?)"
        cursor = self.db.cursor()
        try:
            cursor.execute(sql)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error: {e}")

        cursor.close()
