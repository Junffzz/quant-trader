import json
import pandas as pd
from app.config.common import *


class CsvDriver:
    @staticmethod
    def get_stock_df_from_file(input_path: Path) -> pd.DataFrame:
        """
        Load Data from File (CSV / Feather / Parquet)
        :param input_path: File Name to Load
        :return: DataFrame
        """
        data = None
        if input_path.suffix == '.csv':
            data = pd.read_csv(input_path, index_col=None, encoding='utf-8-sig')
        elif input_path.suffix == '.parquet':
            data = pd.read_parquet(input_path)
        return data
