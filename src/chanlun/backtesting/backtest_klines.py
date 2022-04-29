# 回放行情所需
import time

import pandas as pd

from chanlun import cl
from chanlun.exchange.exchange_db import ExchangeDB
from chanlun.cl_interface import *
from chanlun.backtesting.base import CLDatas


def datetime_minutes(start_dt: datetime, end_dt: datetime):
    """
    获取两个时间的间隔分钟数
    """
    return int((end_dt - start_dt).total_seconds() / 60)


class BackCLDatas(CLDatas):
    """
    回测的缠论数据获取
    """

    def __init__(self, code, frequencys, cl_config):
        super().__init__(code, frequencys, None, cl_config)

        self.total_time = 0

    def __getitem__(self, item) -> ICL:
        __s = time.time()

        frequency = self.frequencys[item]
        if frequency not in self.cl_datas.keys():
            # tqdm.write('cl item %s - %s not exists' % (item, frequency))
            self.cl_datas[frequency] = cl.CL(self.code, frequency=frequency, config=self.cl_config).process_klines(
                self.klines[frequency])

        # 判断是追加更新还是从新计算
        cl_end_time = self.cl_datas[frequency].get_klines()[-1].date
        kline_start_time = self.klines[frequency].iloc[0]['date']
        if cl_end_time > kline_start_time:
            # tqdm.write('cl item %s - %s increment' % (item, frequency))
            self.cl_datas[frequency].process_klines(self.klines[frequency])
        else:
            # tqdm.write('cl item %s - %s cal' % (item, frequency))
            self.cl_datas[frequency] = cl.CL(self.code, frequency=frequency, config=self.cl_config).process_klines(
                self.klines[frequency])

        __r = time.time() - __s
        self.total_time += __r

        return self.cl_datas[frequency]


class BackTestKlines:
    """
    数据库行情回放
    """

    def __init__(self, market, code, start_date, end_date, frequencys=None, cl_config=None):
        """
        配置初始化
        :param market: 市场 支持 a hk currency
        :param code:
        :param frequencys:
        :param start_date:
        :param end_date:
        """
        if frequencys is None:
            frequencys = ['30m', '5m']
        self.market = market
        self.code = code
        self.frequencys = frequencys
        self.cl_config = cl_config
        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        self.start_date = start_date
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        self.end_date = end_date

        self.now_date = start_date

        self.klines: Dict[str, pd.DataFrame] = {}
        self.show_klines: Dict[str, pd.DataFrame] = {}

        # 保存缠论数据对象
        self.cl_datas: BackCLDatas = BackCLDatas(self.code, self.frequencys, self.cl_config)

        self.exchange = ExchangeDB(self.market)

        self.time_fmt = '%Y-%m-%d %H:%M:%S'

        # self.bar = tqdm(desc=self.code, total=datetime_minutes(self.start_date, self.end_date))

    def start(self):
        # 获取行情数据
        for f in self.frequencys:
            real_start_date = self._cal_start_date_by_frequency(self.start_date, f)
            self.klines[f] = self.exchange.klines(self.code,
                                                  f,
                                                  start_date=real_start_date,
                                                  end_date=self.end_date,
                                                  args={'limit': None})
            # print('Code %s F %s len %s' % (self.code, f, len(self.klines[f])))
        self.next(self.frequencys[-1])

    def next(self, f):
        # 设置下一个时间
        while True:
            _up_now_date = self.now_date
            self.now_date = self._next_datetime(self.now_date, f)
            # print('Next date : ', self.now_date)
            if self.now_date is None or self.now_date > self.end_date:
                # self.bar.close()
                return False
            # self.bar.update(datetime_minutes(_up_now_date, self.now_date))
            # self.bar.set_description(self.code + ' ' + self.now_date.strftime('%Y-%m-%d %H:%M:%S'), False)

            try:
                for f in self.frequencys:
                    if self.market in ['currency', 'futures']:
                        self.show_klines[f] = self.klines[f][self.klines[f]['date'] < self.now_date][-2000::]
                    else:
                        self.show_klines[f] = self.klines[f][self.klines[f]['date'] <= self.now_date][-2000::]

                self.convert_klines()
                for f in self.frequencys:
                    self.cl_datas.update_kline(f, self.show_klines[f])
            except Exception as e:
                print(f'ERROR: {self.code} 运行 Next 错误，当前时间 : {self.now_date}，错误信息：{str(e)}')
                return False
            if len(self.show_klines[self.frequencys[-1]]) < 100:
                continue
            return True

    def convert_klines(self):
        """
        转换 kline，去除未来的 kline数据
        :return:
        """
        for i in range(len(self.frequencys), 1, -1):
            min_f = self.frequencys[i - 1]
            max_f = self.frequencys[i - 2]
            new_kline = self.exchange.convert_kline_frequency(self.show_klines[min_f][-120::], max_f)
            if len(self.show_klines[max_f]) > 0 and len(new_kline) > 0:
                self.show_klines[max_f] = self.show_klines[max_f].append(
                    new_kline
                ).drop_duplicates(subset=['date'], keep='last')
                # 删除大周期中，日期大于最小周期的未来数据
                self.show_klines[max_f] = self.show_klines[max_f].drop(
                    self.show_klines[max_f][
                        self.show_klines[max_f]['date'] > self.show_klines[min_f].iloc[-1]['date']
                        ].index
                )
        return True

    def _next_datetime(self, now_date, frequency):
        """
        根据周期，计算下一个时间的起始
        :param now_date:
        :param frequency:
        :return:
        """
        if now_date is None:
            return None

        next_klines = self.klines[frequency][self.klines[frequency]['date'] > now_date]

        if len(next_klines) == 0:
            return None
        # next_date = next_klines.iloc[0]['date']
        # pre_klines = self.klines[frequency][self.klines[frequency]['date'] < next_date]
        # if len(pre_klines) < 500:
        #     if len(next_klines) > 501:
        #         next_date = next_klines.iloc[500]['date']
        #     else:
        #         return None
        # return next_date
        return next_klines.iloc[0]['date']

    def _cal_start_date_by_frequency(self, start_date: datetime, frequency) -> str:
        """
        按照周期，计算行情获取的开始时间
        :param start_date :
        :param frequency:
        :return:
        """
        market_days_freq_maps = {
            'a': {'w': 10000, 'd': 5000, '120m': 500, '4h': 500, '60m': 100, '30m': 100, '15m': 50, '5m': 25, '1m': 5},
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
