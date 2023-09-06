import mariadb
import sys


def get_mariadb_conn() -> mariadb.connections.Connection:
    return mariadb.connect(
        user="root",
        password="root",
        host="127.0.0.1",
        port=3306,
        database="quant_trader_db"
    )


conn = get_mariadb_conn()
cursor = conn.cursor()


def main():
    data_list = [('000002.SZ','fsfs'),('000003.SZ','fsfs2')]
    sql = "INSERT INTO stocks_basic (ts_code,fullname) VALUES (?,?)"

    try:
        cursor.executemany(sql, data_list)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")

    cursor.close()


if __name__ == '__main__':
    main()
