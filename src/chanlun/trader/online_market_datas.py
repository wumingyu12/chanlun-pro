"""
线上行情数据获取对象，用于实盘交易执行
"""
from typing import List

import pandas as pd

from chanlun import cl
from chanlun.backtesting.base import MarketDatas
from chanlun.cl_interface import ICL
from chanlun.exchange.exchange import Exchange


class OnlineMarketDatas(MarketDatas):
    """
    线上实盘交易数据获取类
    """

    def __init__(self, market: str, frequencys: List[str], ex: Exchange, cl_config: dict):
        super().__init__(market, frequencys, cl_config)
        self.ex = ex

    def klines(self, code, frequency) -> pd.DataFrame:
        return self.ex.klines(code, frequency)

    def last_k_info(self, code) -> dict:
        klines = self.klines(code, self.frequencys[-1])
        return {
            'date': klines.iloc[-1]['date'],
            'open': float(klines.iloc[-1]['open']),
            'close': float(klines.iloc[-1]['close']),
            'high': float(klines.iloc[-1]['high']),
            'low': float(klines.iloc[-1]['low']),
        }

    def get_cl_data(self, code, frequency) -> ICL:
        key = '%s-%s' % (code, frequency)

        # 根据回测配置，可自定义不同周期所使用的缠论配置项
        if frequency in self.cl_config.keys():
            cl_config = self.cl_config[frequency]
        elif 'default' in self.cl_config.keys():
            cl_config = self.cl_config['default']
        else:
            cl_config = self.cl_config

        klines = self.klines(code, frequency)
        if key not in self.cl_datas.keys():
            self.cl_datas[key] = cl.CL(code, frequency, cl_config).process_klines(klines)
        else:
            self.cl_datas[key].process_klines(klines)

        return self.cl_datas[key]
