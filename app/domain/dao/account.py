import mariadb

import app.infra.db as dbDriver


class Account:
    def __init__(self):
        driver = dbDriver.MariadbDriver()

        self._cur = driver.get_conn_cursor()
        self._table = "account"

    def find_one_by_id(self, id: int):
        try:
            self._cur.execute("SELECT * FROM {self._table} WHERE id=?", (id,))
        except mariadb.Error as e:
            print(f"Error: {e}")
