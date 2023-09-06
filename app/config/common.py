import configparser
import time
from pathlib import Path

PATH = Path.cwd()
PATH_CONFIG = PATH / 'config'
PATH_DATA = PATH / 'data'
PATH_LOG = PATH / 'log'

DATETIME_FORMAT_DW = '%Y-%m-%d'
DATETIME_FORMAT_M = ''

ORDER_RETRY_MAX = 3

config = configparser.ConfigParser()
config.read(
    PATH_CONFIG / 'config.ini' if (PATH_CONFIG / 'config.ini').is_file() else PATH_CONFIG / 'config_template.ini')