# 回放行情所需
import hashlib
import json

from chanlun import fun
from chanlun.backtesting.base import MarketDatas
from chanlun.cl_interface import *
from chanlun.exchange.exchange_db import ExchangeDB
from tqdm.auto import tqdm
from chanlun import cl

from typing import Dict


class BackTestKlines(MarketDatas):
    """
    数据库行情回放
    """

    def __init__(self, market: str, start_date: str, end_date: str, frequencys: List[str], cl_config=None):
        """
        配置初始化
        :param market: 市场 支持 a hk currency
        :param frequencys:
        :param start_date:
        :param end_date:
        """
        super().__init__(market, frequencys, cl_config)

        self.market = market
        self.base_code = None
        self.frequencys = frequencys
        self.cl_config = cl_config
        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        self.start_date = start_date
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        self.end_date = end_date

        self.now_date = start_date

        # 保存k线数据
        self.all_klines: Dict[str, Dict[str, pd.DataFrame]] = {}

        # 每个周期缓存的k线数据，避免多次请求重复计算
        self.cache_klines: Dict[str, Dict[str, pd.DataFrame]] = {}

        # 保存每个标的的缠论配置唯一key，如果后续在运行中进行变更，则需要重新计算
        self.cache_cl_config_keys: Dict[str, str] = {}

        self.ex = ExchangeDB(self.market)

        # 用于循环的日期列表
        self.loop_datetime_list: list = []

        # 进度条
        self.bar: Union[tqdm, None] = None

        self.time_fmt = '%Y-%m-%d %H:%M:%S'

    def init(self, base_code: str, frequency: str):
        # 初始化，获取循环的日期列表
        self.base_code = base_code
        if frequency is None:
            frequency = self.frequencys[-1]
        klines = self.ex.klines(
            base_code, frequency,
            start_date=fun.datetime_to_str(self.start_date), end_date=fun.datetime_to_str(self.end_date),
            args={'limit': None}
        )
        self.loop_datetime_list = list(klines['date'].to_list())

        self.bar = tqdm(total=len(self.loop_datetime_list))

    def next(self):
        if len(self.loop_datetime_list) == 0:
            return False
        self.now_date = self.loop_datetime_list.pop(0)
        # 清除之前的 cl_datas 、klines 缓存，重新计算
        self.cache_cl_datas = {}
        self.cache_klines = {}
        self.bar.update(1)
        return True

    def last_k_info(self, code) -> dict:
        kline = self.klines(code, self.frequencys[-1])
        return {
            'date': kline.iloc[-1]['date'],
            'open': float(kline.iloc[-1]['open']),
            'close': float(kline.iloc[-1]['close']),
            'high': float(kline.iloc[-1]['high']),
            'low': float(kline.iloc[-1]['low']),
        }

    def get_cl_data(self, code, frequency) -> ICL:
        key = '%s_%s' % (code, frequency)
        if key in self.cache_cl_datas.keys():
            return self.cache_cl_datas[key]

        # 根据回测配置，可自定义不同周期所使用的缠论配置项
        if code in self.cl_config.keys():
            cl_config = self.cl_config[code]
        elif frequency in self.cl_config.keys():
            cl_config = self.cl_config[frequency]
        elif 'default' in self.cl_config.keys():
            cl_config = self.cl_config['default']
        else:
            cl_config = self.cl_config

        # 将配置项md5哈希，并对比与之前的计算是否一致，不一致则重新计算
        cl_config_key = json.dumps(cl_config)
        cl_config_key = hashlib.md5(cl_config_key.encode(encoding='UTF-8')).hexdigest()
        if key not in self.cache_cl_config_keys.keys():
            self.cache_cl_config_keys[key] = cl_config_key
        elif self.cache_cl_config_keys[key] != cl_config_key:
            # print(f'{key} 配置项变更为：{cl_config}')
            self.cache_cl_config_keys[key] = cl_config_key
            del (self.cl_datas[key])

        if key not in self.cl_datas.keys():
            # 第一次进行计算
            klines = self.klines(code, frequency)
            self.cl_datas[key] = cl.CL(code, frequency, cl_config).process_klines(klines)
        else:
            # 更新计算
            cd = self.cl_datas[key]
            klines = self.klines(code, frequency)
            if len(klines) > 0:
                if len(cd.get_klines()) == 0:
                    self.cl_datas[key].process_klines(klines)
                else:
                    # 判断是追加更新还是从新计算
                    cl_end_time = cd.get_klines()[-1].date
                    kline_start_time = klines.iloc[0]['date']
                    if cl_end_time > kline_start_time:
                        self.cl_datas[key].process_klines(klines)
                    else:
                        self.cl_datas[key] = cl.CL(code, frequency, cl_config).process_klines(klines)

        # 单次循环内，计算过后进行缓存，避免多次计算
        self.cache_cl_datas[key] = self.cl_datas[key]

        return self.cache_cl_datas[key]

    def klines(self, code, frequency) -> pd.DataFrame:
        if code in self.cache_klines.keys():
            # 直接从缓存中读取
            return self.cache_klines[code][frequency]

        for f in self.frequencys:
            key = '%s-%s' % (code, f)
            if key not in self.all_klines.keys():
                # 从数据库获取日期区间的所有行情
                self.all_klines[key] = self.ex.klines(
                    code, f,
                    start_date=self._cal_start_date_by_frequency(self.start_date, f),
                    end_date=fun.datetime_to_str(self.end_date),
                    args={'limit': None}
                )
        klines = {}
        for f in self.frequencys:
            key = '%s-%s' % (code, f)
            if self.market in ['currency', 'futures']:
                kline = self.all_klines[key][self.all_klines[key]['date'] < self.now_date][-2000::]
            else:
                kline = self.all_klines[key][self.all_klines[key]['date'] <= self.now_date][-2000::]
            klines[f] = kline
        # 转换周期k线，去除未来数据
        klines = self.convert_klines(klines)
        # print(frequency, len(klines[frequency]))
        # 将结果保存到 缓存中，避免重复读取
        self.cache_klines[code] = klines
        return klines[frequency]

    def convert_klines(self, klines: Dict[str, pd.DataFrame]):
        """
        转换 kline，去除未来的 kline数据
        :return:
        """
        for i in range(len(self.frequencys), 1, -1):
            min_f = self.frequencys[i - 1]
            max_f = self.frequencys[i - 2]
            if len(klines[min_f]) == 0:
                continue
            new_kline = self.ex.convert_kline_frequency(klines[min_f][-120::], max_f)
            if len(klines[max_f]) > 0 and len(new_kline) > 0:
                klines[max_f] = klines[max_f].append(new_kline).drop_duplicates(subset=['date'], keep='last')
                # 删除大周期中，日期大于最小周期的未来数据
                klines[max_f] = klines[max_f].drop(
                    klines[max_f][klines[max_f]['date'] > klines[min_f].iloc[-1]['date']].index
                )

        return klines

    def _cal_start_date_by_frequency(self, start_date: datetime, frequency) -> str:
        """
        按照周期，计算行情获取的开始时间
        :param start_date :
        :param frequency:
        :return:
        """
        market_days_freq_maps = {
            'a': {'w': 10000, 'd': 5000, '120m': 500, '4h': 500, '60m': 100, '30m': 100, '15m': 50, '5m': 25,
                  '1m': 5},
            'hk': {'d': 5000, '120m': 500, '4h': 500, '60m': 100, '30m': 100, '15m': 50, '5m': 25, '1m': 5},
            'us': {'d': 5000, '120m': 500, '4h': 500, '60m': 100, '30m': 100, '15m': 50, '5m': 25, '1m': 5},
            'currency': {'d': 300, '120m': 200, '4h': 100, '60m': 50, '30m': 50, '15m': 25, '5m': 5, '1m': 1},
            'futures': {'d': 5000, '120m': 500, '4h': 500, '60m': 100, '30m': 100, '15m': 50, '5m': 25, '1m': 5},
        }
        for _freq in ['w', 'd', '120m', '4h', '60m', '30m', '15m', '5m', '1m']:
            if _freq == frequency:
                return (start_date - datetime.timedelta(days=market_days_freq_maps[self.market][_freq])).strftime(
                    self.time_fmt)
        raise Exception(f'不支持的周期 {frequency}')
