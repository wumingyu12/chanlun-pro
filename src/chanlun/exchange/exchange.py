import datetime
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict
from chanlun import fun

import pandas as pd


@dataclass
class Tick:
    code: str
    last: float
    buy1: float
    sell1: float
    high: float
    low: float
    open: float
    volume: float


class Exchange(ABC):
    """
    交易所类
    """

    @abstractmethod
    def all_stocks(self):
        """
        获取支持的所有股票列表
        :return:
        """

    @abstractmethod
    def now_trading(self):
        """
        返回当前是否可交易
        :return bool
        """

    @abstractmethod
    def klines(
            self, code: str,
            frequency: str,
            start_date: str = None,
            end_date: str = None,
            args=None) -> [pd.DataFrame, None]:
        """
        获取 Kline 线
        :param code:
        :param frequency:
        :param start_date:
        :param end_date:
        :param args:
        :return:
        """

    @abstractmethod
    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        获取股票列表的 Tick 信息
        :param codes:
        :return:
        """

    @abstractmethod
    def stock_info(self, code: str) -> [Dict, None]:
        """
        获取股票的基本信息
        :param code:
        :return:
        """

    @abstractmethod
    def stock_owner_plate(self, code: str):
        """
        股票所属板块信息
        :param code:
        :return:
        return {
            'HY': [{'code': '行业代码', 'name': '行业名称'}],
            'GN': [{'code': '概念代码', 'name': '概念名称'}],
        }
        """

    @abstractmethod
    def plate_stocks(self, code: str):
        """
        获取板块股票列表信息
        :param code: 板块代码
        :return:
        return [{'code': 'SH.000001', 'name': '上证指数'}]
        """

    @abstractmethod
    def balance(self):
        """
        账户资产信息
        :return:
        """

    @abstractmethod
    def positions(self, code: str = ''):
        """
        当前账户持仓信息
        :param code:
        :return:
        """

    @abstractmethod
    def order(self, code: str, o_type: str, amount: float, args=None):
        """
        下单接口
        :param args:
        :param code:
        :param o_type:
        :param amount:
        :return:
        """


def convert_stock_kline_frequency(klines: pd.DataFrame, to_f: str) -> pd.DataFrame:
    """
    转换股票 k 线到指定的周期
    时间是向后对齐的
    :param klines:
    :param to_f:
    :return:
    """
    new_kline = {}
    freq_second_maps = {
        '5m': 5 * 60, '10m': 10 * 60, '15m': 15 * 60, '30m': 30 * 60, '60m': 60 * 60, '120m': 120 * 60,
        'd': 24 * 60 * 60, 'm': 30 * 24 * 60 * 60
    }
    if to_f not in freq_second_maps.keys():
        raise Exception(f'不支持的转换周期：{to_f}')

    seconds = freq_second_maps[to_f]

    for k in klines.iterrows():
        dt: datetime.datetime = k[1]['date'].to_pydatetime()
        date_time = dt.timestamp()
        if date_time % seconds == 0:
            new_date_time = date_time
        else:
            if to_f in ['d']:
                new_date_time = date_time - (date_time % seconds)
            else:
                new_date_time = date_time - (date_time % seconds) + seconds

        if to_f in ['m']:
            new_date_time = fun.str_to_datetime(f'{dt.year}-{dt.month}-01 00:00:00').timestamp()
        if to_f in ['d']:
            new_date_time -= 8 * 60 * 60
        if to_f == '60m':
            if (dt.hour == 9) or (dt.hour == 10 and dt.minute <= 30):
                new_date_time = datetime.datetime.strptime(dt.strftime('%Y-%m-%d 10:30:00'),
                                                           '%Y-%m-%d %H:%M:%S').timestamp()
            elif (dt.hour == 10 and dt.minute >= 30) or (dt.hour == 11):
                new_date_time = datetime.datetime.strptime(dt.strftime('%Y-%m-%d 11:30:00'),
                                                           '%Y-%m-%d %H:%M:%S').timestamp()
        if to_f == '120m':
            if dt.hour == 9 or dt.hour == 10 or (dt.hour == 11 and dt.minute <= 30):
                new_date_time = datetime.datetime.strptime(dt.strftime('%Y-%m-%d 11:30:00'),
                                                           '%Y-%m-%d %H:%M:%S').timestamp()

        new_date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_date_time))
        if new_date_time in new_kline:
            n_k = new_kline[new_date_time]
            if k[1]['high'] > n_k['high']:
                n_k['high'] = k[1]['high']
            if k[1]['low'] < n_k['low']:
                n_k['low'] = k[1]['low']
            n_k['close'] = k[1]['close']
            n_k['volume'] += float(k[1]['volume']) if k[1]['volume'] is not None else 0
            new_kline[new_date_time] = n_k
        else:
            new_kline[new_date_time] = {
                'code': k[1]['code'],
                'date': new_date_time,
                'open': k[1]['open'],
                'close': k[1]['close'],
                'high': k[1]['high'],
                'low': k[1]['low'],
                'volume': float(k[1]['volume']) if k[1]['volume'] is not None else 0,
            }
    kline_pd = pd.DataFrame(new_kline.values())
    kline_pd['date'] = pd.to_datetime(kline_pd['date'])
    return kline_pd[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]


def convert_currency_kline_frequency(klines: pd.DataFrame, to_f: str) -> pd.DataFrame:
    """
    数字货币k线转换方法
    """
    new_kline = {}
    f_maps = {
        '5m': 5 * 60, '10m': 10 * 60, '15m': 15 * 60, '30m': 30 * 60, '60m': 60 * 60,
        '120m': 120 * 60, '4h': 4 * 60 * 60,
        'd': 24 * 60 * 60, 'w': 7 * 24 * 60 * 60
    }
    seconds = f_maps[to_f]

    for k in klines.iterrows():
        _date = k[1]['date'].to_pydatetime()
        date_time = _date.timestamp()

        new_date_time = date_time - (date_time % seconds)
        new_date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_date_time))
        if new_date_time in new_kline:
            n_k = new_kline[new_date_time]
            if k[1]['high'] > n_k['high']:
                n_k['high'] = k[1]['high']
            if k[1]['low'] < n_k['low']:
                n_k['low'] = k[1]['low']
            n_k['close'] = k[1]['close']
            n_k['volume'] += float(k[1]['volume'])
            new_kline[new_date_time] = n_k
        else:
            new_kline[new_date_time] = {
                'code': k[1]['code'],
                'date': new_date_time,
                'open': k[1]['open'],
                'close': k[1]['close'],
                'high': k[1]['high'],
                'low': k[1]['low'],
                'volume': float(k[1]['volume']),
            }
    kline_pd = pd.DataFrame(new_kline.values())
    kline_pd['date'] = pd.to_datetime(kline_pd['date'])
    return kline_pd[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]


def convert_futures_kline_frequency(klines: pd.DataFrame, to_f: str) -> pd.DataFrame:
    """
    期货数据 转换 k 线到指定的周期
    期货的K线数据日期是向前看其， 10:00 30分钟线表示的是 10:00 - 10:30 分钟数据
    :param klines:
    :param to_f:
    :return:
    """
    new_kline = {}
    freq_second_maps = {
        '1m': 1 * 60,
        '3m': 3 * 60,
        '5m': 5 * 60,
        '10m': 10 * 60,
        '15m': 15 * 60,
        '30m': 30 * 60,
        '60m': 60 * 60,
        '120m': 2 * 60 * 60,
        'd': 24 * 60 * 60
    }
    # TODO 由于 期货上午 10点15 休息 15 分钟，所以需要特殊处理
    freq_special_maps = {
        '10m': [{'h': [10], 'm': [{'min': 10, 'max': 15, 'to': 10}]}],
        '30m': [{'h': [10], 'm': [{'min': 10, 'max': 15, 'to': 10}]}],
    }
    if to_f not in freq_second_maps.keys():
        raise Exception(f'不支持的转换周期：{to_f}')

    seconds = freq_second_maps[to_f]

    for k in klines.iterrows():
        dt: datetime.datetime = k[1]['date'].to_pydatetime()
        date_time = dt.timestamp()
        if date_time % seconds == 0:
            new_date_time = date_time
        else:
            new_date_time = date_time - (date_time % seconds)
        # 30m 10

        new_date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_date_time))
        if new_date_time in new_kline:
            n_k = new_kline[new_date_time]
            if k[1]['high'] > n_k['high']:
                n_k['high'] = k[1]['high']
            if k[1]['low'] < n_k['low']:
                n_k['low'] = k[1]['low']
            n_k['close'] = k[1]['close']
            n_k['volume'] += float(k[1]['volume'])
            new_kline[new_date_time] = n_k
        else:
            new_kline[new_date_time] = {
                'code': k[1]['code'],
                'date': new_date_time,
                'open': k[1]['open'],
                'close': k[1]['close'],
                'high': k[1]['high'],
                'low': k[1]['low'],
                'volume': float(k[1]['volume']),
            }
    kline_pd = pd.DataFrame(new_kline.values())
    kline_pd['date'] = pd.to_datetime(kline_pd['date'])
    return kline_pd[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]
