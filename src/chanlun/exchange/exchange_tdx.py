import copy
import json
import time
import traceback
from typing import Union

from pytdx.hq import TdxHq_API
from pytdx.util import best_ip
from tenacity import retry, stop_after_attempt, wait_random, retry_if_result

from chanlun import fun
from chanlun import rd
from chanlun.exchange.exchange import *
from chanlun.exchange.exchange_futu import ExchangeFutu
from chanlun.exchange.stocks_bkgn import StocksBKGN
from chanlun.file_db import FileCacheDB

g_all_stocks = []
g_trade_days = None


class ExchangeTDX(Exchange):
    """
    通达信行情接口
    """

    def __init__(self):
        # super().__init__()

        # 选择最优的服务器，并保存到 redis 中
        connect_ip = rd.Robj().get('tdx_connect_ip')
        # connect_ip = None # 手动重新选择最优服务器
        if connect_ip is None:
            connect_ip = best_ip.select_best_ip('stock')
            connect_ip = connect_ip['ip'] + ':' + str(connect_ip['port'])
            rd.Robj().set('tdx_connect_ip', connect_ip)
        print('TDX 最优服务器：' + connect_ip)
        self.connect_ip = {'ip': connect_ip.split(':')[0], 'port': int(connect_ip.split(':')[1])}

        self.futu_ex = ExchangeFutu()

        # 板块概念信息
        self.stock_bkgn = StocksBKGN()

        # 文件缓存
        self.fdb = FileCacheDB()

        # 设置时区
        self.tz = pytz.timezone('Asia/Shanghai')

    def default_code(self):
        return 'SH.000001'

    def support_frequencys(self):
        return {
            'y': 'Y', 'q': 'Q', 'm': 'M', 'w': 'W', 'd': 'D',
            '120m': '120m', '60m': '60m', '30m': '30m', '15m': '15m', '5m': '5m', '1m': '1m'
        }

    def all_stocks(self):
        """
        使用 通达信的方式获取所有股票代码
        """
        global g_all_stocks
        if len(g_all_stocks) > 0:
            return g_all_stocks
        g_all_stocks = rd.get_ex('stocks_all')
        if g_all_stocks is not None:
            return g_all_stocks
        g_all_stocks = []
        for market in range(2):

            client = TdxHq_API(raise_exception=True, auto_retry=True)
            with client.connect(self.connect_ip['ip'], self.connect_ip['port']):
                count = client.get_security_count(market)
                data = pd.concat([
                    client.to_df(client.get_security_list(market, i * 1000)) for i in
                    range(int(count / 1000) + 1)
                ], axis=0, sort=False)
                for _d in data.iterrows():
                    code = _d[1]['code']
                    name = _d[1]['name']
                    sse = 'SZ' if market == 0 else 'SH'
                    _type = self.for_sz(code) if market == 0 else self.for_sh(code)
                    if _type in ['bond_cn', 'undefined', 'stockB_cn']:
                        continue
                    g_all_stocks.append({'code': f'{sse}.{str(code)}', 'name': name, 'type': _type})

        print(f'股票列表从 TDX 进行获取，共获取数量：{len(g_all_stocks)}')

        if g_all_stocks:
            rd.save_ex('stocks_all', 24 * 60 * 60, g_all_stocks)

        return g_all_stocks

    def to_tdx_code(self, code):
        """
        转换为 tdx 对应的代码
        """
        # 富途代码对 tdx 代码的对照修正表
        tdx_code_maps = {
            'SH.000001': 'SH.999999'
        }
        if code in tdx_code_maps:
            code = tdx_code_maps[code]

        market = code[:3]
        if market == 'SH.':
            market = 1
        elif market == 'SZ.':
            market = 0
        else:
            market = None
        all_stocks = self.all_stocks()
        stock = [_s for _s in all_stocks if _s['code'] == code]
        _type = stock[0]['type'] if stock else None
        return market, code[-6:], _type

    @retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=5), retry=retry_if_result(lambda _r: _r is None))
    def klines(self, code: str, frequency: str,
               start_date: str = None, end_date: str = None,
               args=None) -> Union[pd.DataFrame, None]:

        """
        通达信，不支持按照时间查找
        """
        _s_time = time.time()

        if args is None:
            args = {}
        if 'fq' not in args.keys():
            args['fq'] = 'qfq'
        if 'use_cache' not in args.keys():
            args['use_cache'] = True
        if 'pages' not in args.keys():
            args['pages'] = 8
        else:
            args['pages'] = int(args['pages'])

        frequency_map = {
            'y': 11, 'q': 10, 'm': 6, 'w': 5, 'd': 9, '120m': 3, '60m': 3, '30m': 2, '15m': 1, '5m': 0, '1m': 8
        }
        market, tdx_code, _type = self.to_tdx_code(code)
        if market is None or _type is None or start_date is not None or end_date is not None:
            print('通达信不支持的调用参数')
            return None

        # _time_s = time.time()
        try:
            client = TdxHq_API(raise_exception=True, auto_retry=True)
            with client.connect(self.connect_ip['ip'], self.connect_ip['port']):
                if 'index' in _type:
                    get_bars = client.get_index_bars
                else:
                    get_bars = client.get_security_bars

                klines: pd.DataFrame = self.fdb.get_tdx_klines(code, frequency)
                if klines is None:
                    # 获取 8*800 = 6400 条数据
                    klines = pd.concat([
                        client.to_df(get_bars(frequency_map[frequency], market, tdx_code, (i - 1) * 800, 800))
                        for i in range(1, args['pages'] + 1)
                    ], axis=0, sort=False)
                    klines.loc[:, 'date'] = pd.to_datetime(klines['datetime'])
                    klines.sort_values('date', inplace=True)
                else:
                    for i in range(1, args['pages'] + 1):
                        # print(f'{code} 使用缓存，更新获取第 {i} 页')
                        _ks = client.to_df(get_bars(frequency_map[frequency], market, tdx_code, (i - 1) * 800, 800))
                        _ks.loc[:, 'date'] = pd.to_datetime(_ks['datetime'])
                        _ks.sort_values('date', inplace=True)
                        new_start_dt = _ks.iloc[0]['date']
                        old_end_dt = klines.iloc[-1]['date']
                        klines = pd.concat([klines, _ks], ignore_index=True)
                        # 如果请求的第一个时间大于缓存的最后一个时间，退出
                        if old_end_dt >= new_start_dt:
                            break

            # 删除重复数据
            klines = klines.drop_duplicates(['date'], keep='last').sort_values('date')
            self.fdb.save_tdx_klines(code, frequency, klines)

            klines.loc[:, 'code'] = code
            klines.loc[:, 'volume'] = klines['vol']

            # 转换时区
            klines['date'] = klines['date'].dt.tz_localize(self.tz)

            if frequency in {'y', 'q', 'm', 'w', 'd'}:
                klines['date'] = klines['date'].apply(self.__convert_date)

            klines = klines[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]

            if frequency == '120m':
                klines = convert_stock_kline_frequency(klines, frequency)

            if args['fq'] in ['qfq', 'hfq']:
                klines = self.klines_fq(klines, self.xdxr(market, code, tdx_code), args['fq'])

            return klines
        except Exception as e:
            print(f'tdx 获取行情异常 {code} Exception ：{str(e)}')
            print(traceback.format_exc())
        finally:
            pass
            # print(f'tdx 请求行情用时：{time.time() - _s_time}')
        return None

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        获取股票名称
        """
        all_stock = self.all_stocks()
        stock = [_s for _s in all_stock if _s['code'] == code]
        if not stock:
            return None
        return {
            'code': stock[0]['code'],
            'name': stock[0]['name']
        }

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        如果可以使用 富途 的接口，就用 富途的，否则就用 日线的 K线计算
        使用 富途 的接口会很快，日线则很慢
        获取日线的k线，并返回最后一根k线的数据
        """
        ticks = {}
        if len(codes) == 0:
            return ticks
        query_stocks = []
        for _c in codes:
            _m, _c, _t = self.to_tdx_code(_c)
            if _m is not None:
                query_stocks.append((_m, _c))
        client = TdxHq_API(raise_exception=True, auto_retry=True)
        with client.connect(self.connect_ip['ip'], self.connect_ip['port']):
            # 获取总数据量
            total_quotes = len(query_stocks)
            # 分批次获取数据
            batch_size = 80
            quotes = []
            for i in range(0, total_quotes, batch_size):
                batch_stocks = query_stocks[i:i + batch_size]
                batch_quotes = client.get_security_quotes(batch_stocks)
                quotes += batch_quotes
            # ('market', 0), ('code', '000001'), ('active1', 4390), ('price', 14.29), ('last_close', 14.24), ('open', 14.35),
            # ('high', 14.37), ('low', 14.14), ('servertime', '14:59:55.939'), ('reversed_bytes0', 14998872),
            # ('reversed_bytes1', -1429), ('vol', 690954), ('cur_vol', 11982), ('amount', 985552128.0), ('s_vol', 339925),
            # ('b_vol', 351029), ('reversed_bytes2', -1), ('reversed_bytes3', 45188), ('bid1', 14.28), ('ask1', 14.29),
            # ('bid_vol1', 2617), ('ask_vol1', 2391), ('bid2', 14.27), ('ask2', 14.3), ('bid_vol2', 1853),
            # ('ask_vol2', 4075), ('bid3', 14.26), ('ask3', 14.31), ('bid_vol3', 2164), ('ask_vol3', 3421), ('bid4', 14.25),
            # ('ask4', 14.32), ('bid_vol4', 2512), ('ask_vol4', 8679), ('bid5', 14.24), ('ask5', 14.33), ('bid_vol5', 889),
            # ('ask_vol5', 5191), ('reversed_bytes4', (2518,)), ('reversed_bytes5', 0), ('reversed_bytes6', 0),
            # ('reversed_bytes7', 0), ('reversed_bytes8', 0), ('reversed_bytes9', 0.0), ('active2', 4390)])
            for _q in quotes:
                if _q['code'] == '999999':
                    _code = 'SH.000001'
                else:
                    _code = [_c for _c in codes if _c[-6:] == _q['code']]
                    if len(_code) == 0:
                        continue
                    _code = _code[0]
                ticks[_code] = Tick(
                    code=_code, last=_q['price'],
                    buy1=_q['bid1'], sell1=_q['ask1'],
                    low=_q['low'], high=_q['high'],
                    volume=_q['vol'], open=_q['open'],
                    rate=round(
                        (_q['price'] - _q['last_close']) / _q['last_close'] * 100, 2
                    ) if _q['price'] != 0 else 0
                )

        return ticks

    def now_trading(self):
        """
        返回当前是否是交易时间
        周一至周五，09:30-11:30 13:00-15:00
        """
        now_dt = datetime.datetime.now()
        if now_dt.weekday() in [5, 6]:  # 周六日不交易
            return False
        hour = now_dt.hour
        minute = now_dt.minute
        if hour == 9 and minute >= 30:
            return True
        if hour in [10, 13, 14]:
            return True
        if hour == 11 and minute < 30:
            return True
        return False

    @staticmethod
    def __convert_date(dt):
        dt = fun.datetime_to_str(dt, '%Y-%m-%d')
        return fun.str_to_datetime(dt, '%Y-%m-%d')

    @staticmethod
    def for_sz(code):
        """深市代码分类
        Arguments:
            code {[type]} -- [description]
        Returns:
            [type] -- [description]
        """

        if str(code)[:2] in ['00', '30', '02']:
            return 'stock_cn'
        elif str(code)[:2] in ['39']:
            return 'index_cn'
        elif str(code)[:2] in ['15', '16']:
            return 'etf_cn'
        elif str(code)[:3] in ['101', '104', '105', '106', '107', '108', '109',
                               '111', '112', '114', '115', '116', '117', '118', '119',
                               '123', '127', '128',
                               '131', '139', ]:
            # 10xxxx 国债现货
            # 11xxxx 债券
            # 12xxxx 可转换债券

            # 123
            # 127
            # 12xxxx 国债回购
            return 'bond_cn'

        elif str(code)[:2] in ['20']:
            return 'stockB_cn'
        else:
            return 'undefined'

    @staticmethod
    def for_sh(code):
        if str(code)[0] == '6':
            return 'stock_cn'
        elif str(code)[:3] in ['000', '880', '999']:
            return 'index_cn'
        elif str(code)[:2] in ['51', '58']:
            return 'etf_cn'
        # 110×××120×××企业债券；
        # 129×××100×××可转换债券；
        # 113A股对应可转债 132
        elif str(code)[:3] in ['102', '110', '113', '120', '122', '124',
                               '130', '132', '133', '134', '135', '136',
                               '140', '141', '143', '144', '147', '148']:
            return 'bond_cn'
        else:
            return 'undefined'

    def stock_owner_plate(self, code: str):
        """
        使用已经保存好的板块概念信息
        """
        code_type = ''
        if 'SH.' in code:
            code_type = self.for_sh(code.split('.')[1])
        elif 'SZ.' in code:
            code_type = self.for_sz(code.split('.')[1])
        if code_type != 'stock_cn':
            return {'HY': [], 'GN': []}
        bkgn = self.stock_bkgn.get_code_bkgn(code.split('.')[1])
        hys = [{'code': n, 'name': n} for n in bkgn['HY']]
        gns = [{'code': n, 'name': n} for n in bkgn['GN']]
        return {'HY': hys, 'GN': gns}

    def plate_stocks(self, code: str):
        """
        使用已经保存好的板块概念信息
        """
        stock_codes = self.stock_bkgn.get_codes_by_gn(code)
        stock_codes += self.stock_bkgn.get_codes_by_hy(code)

        def code_to_tdx(_code: str):
            if _code[0] == '6':
                return 'SH.' + _code
            else:
                return 'SZ.' + _code

        return [self.stock_info(code_to_tdx(c)) for c in stock_codes if self.stock_info(code_to_tdx(c)) is not None]

    def balance(self):
        raise Exception('交易所不支持')

    def positions(self, code: str = ''):
        raise Exception('交易所不支持')

    def order(self, code: str, o_type: str, amount: float, args=None):
        raise Exception('交易所不支持')

    def xdxr(self, market: int, project_code: str, code: str):
        """
        读取除权除息信息
        """
        key = f'new_xdxr_{market}_{code}'
        now_day = fun.datetime_to_str(datetime.datetime.now(), '%Y-%m-%d')
        redis_data = rd.Robj().hget('tdx_xdxr', key)
        if redis_data is None or json.loads(redis_data)['date'] != now_day:
            client = TdxHq_API(raise_exception=True, auto_retry=True)
            with client.connect(self.connect_ip['ip'], self.connect_ip['port']):
                data = client.to_df(client.get_xdxr_info(market, code))
            if len(data) > 0:
                data.loc[:, 'date'] = data['year'].map(str) + '-' + data['month'].map(str) + '-' + data['day'].map(str)
                data['date'] = pd.to_datetime(data['date'])
            redis_new_data = {
                'date': now_day,
                'data': data.to_json(date_format='epoch', orient='split')
            }
            # 如果之前的不为none，对比复权信息是否有变更，有变更需要清除对应的缓存信息
            if redis_data is not None:
                old_data = pd.read_json(json.loads(redis_data)['data'], orient='split')
                if len(old_data) > 0 and old_data.index[-1] != data.index[-1]:
                    # 清理缓存
                    print(f'{code}复权信息变动，清理缠论数据缓存')
                    self.fdb.clear_web_cl_data('a', project_code)
            rd.Robj().hset('tdx_xdxr', key, json.dumps(redis_new_data))
        else:
            # print('直接读取缓存')
            data = pd.read_json(json.loads(redis_data)['data'], orient='split')

        return data

    def klines_fq(self, fq_klines: pd.DataFrame, xdxr_data, fq_type: str):
        """
        对行情进行复权处理
        """
        if len(xdxr_data) == 0:
            return fq_klines
        info = copy.deepcopy(xdxr_data.query('category==1'))
        if len(info) == 0:
            return fq_klines
        info.loc[:, 'idx_date'] = info['date'].dt.tz_localize(self.tz).dt.tz_convert('UTC')
        info.set_index('idx_date', inplace=True)

        fq_klines = fq_klines.assign(if_trade=1)
        fq_klines.loc[:, 'idx_date'] = fq_klines['date'].dt.tz_convert('UTC')
        fq_klines.set_index('idx_date', inplace=True)

        if len(info) > 0:
            # 有除权数据
            data = pd.concat([fq_klines, info.loc[fq_klines.index[0]:fq_klines.index[-1], ['category']]], axis=1)
            data['if_trade'].fillna(value=0, inplace=True)
            data = data.fillna(method='ffill')
            data = pd.concat(
                [data,
                 info.loc[fq_klines.index[0]:fq_klines.index[-1], ['fenhong', 'peigu', 'peigujia', 'songzhuangu']]],
                axis=1)
        else:
            data = pd.concat([fq_klines, info.loc[:, ['category', 'fenhong', 'peigu', 'peigujia', 'songzhuangu']]],
                             axis=1)

        # 数据补全
        data = data.fillna(0)

        # 计算前日收盘
        data['preclose'] = (data['close'].shift(1) * 10 - data['fenhong'] + data['peigu'] * data['peigujia']) / (
                10 + data['peigu'] + data['songzhuangu'])

        # 前复权
        if fq_type == 'qfq':
            data['adj'] = (data['preclose'].shift(-1) / data['close']).fillna(1)[::-1].cumprod()

        # 后复权
        if fq_type == 'hfq':
            data['adj'] = (data['close'] / data['preclose'].shift(-1)).cumprod().shift(1).fillna(1)

        # ohlc 数据进行复权计算
        for col in ['open', 'high', 'low', 'close']:
            data[col] = round(data[col] * data['adj'], 2)

        # data['volume'] = data['volume'] / data['adj'] if 'volume' in data.columns else data['vol'] / data['adj']

        data = data.query('if_trade==1 and open != 0')

        return data[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]


if __name__ == '__main__':
    ex = ExchangeTDX()
    # xdxr = ex.xdxr(0, '000014')
    # print(xdxr)

    # klines = ex.klines('SH.600498', '30m')
    # print(klines[['date', 'close']].tail())
    #
    # klines = ex.klines('SH.600498', '5m')
    # print(klines[['date', 'close']].tail())

    ticks = ex.ticks(['SZ.300474'])
    print(ticks)
