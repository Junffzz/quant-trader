import redis

from app.config.configure import config


def get_redis_conn():
    host = config.redis.get("host", "localhost")
    port = config.redis.get("port", "6379")
    password = config.redis.get("password", "")
    db = config.redis.get("db", 1)
    pool = redis.ConnectionPool(host=host, port=port, password=password, db=db)
    client = redis.Redis(connection_pool=pool)
    return client
