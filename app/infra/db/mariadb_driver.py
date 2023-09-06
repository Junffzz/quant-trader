import mariadb
import sys

from sqlalchemy import create_engine


def get_mariadb_conn() -> mariadb.connections.Connection:
    return mariadb.connect(
        user="root",
        password="root",
        host="127.0.0.1",
        port=3306,
        database="quant_trader_db"
    )


def mariadb_engine():
    engine = create_engine("mariadb+mariadbconnector://root:root@127.0.0.1:3306/quant_trader_db")
    return engine


class MariadbDriver:
    def __init__(self):
        # Connect to MariaDB Platform
        try:
            self.conn = mariadb.connect(
                user="root",
                password="root",
                host="127.0.0.1",
                port=3306,
                database="quant_trader_db"
            )
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
            sys.exit(1)

        # Get Cursor
        self._cur = self.conn.cursor()

    def get_conn_cursor(self):
        return self._cur

    def close(self):
        self.conn.close()
