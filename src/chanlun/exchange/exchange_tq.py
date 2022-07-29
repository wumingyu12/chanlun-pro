import threading

import tqsdk
from tenacity import retry, stop_after_attempt, wait_random, retry_if_result
from tqsdk.objs import Account, Position

from chanlun import config, fun
from chanlun.exchange.exchange import *

# 整全局的变量
g_api: tqsdk.TqApi = None
g_account: tqsdk.TqAccount = None
g_account_enable: bool = False
g_look = threading.Lock()
g_all_stocks = []
g_klines = {}


class ExchangeTq(Exchange):
    """
    天勤期货行情
    """

    def __init__(self, use_simulate_account=True):
        # 是否使用模拟账号，进行交易测试（这种模式无需设置实盘账号）
        self.use_simulate_account = use_simulate_account

    def get_api(self, use_account=False):
        """
        获取 天勤API 对象
        use_account : 标记是否使用账户对象，在特殊时间，账户是无法登录的，这时候只能使用行情服务，使用账户则会报错
        """
        global g_api, g_account_enable
        # 这时候使用账户模式，但是账户并不可用，尝试关闭 API，并重新创建 账户 API 连接
        if use_account is True and g_account_enable is False and g_api is not None:
            g_api.close()
            g_api = None

        if g_api is None:
            account = self.get_account()
            if use_account and account is None:
                raise Exception('使用实盘账户操作，但是并没有配置实盘账户，请检查实盘配置')
            try:
                g_api = tqsdk.TqApi(account=account, auth=tqsdk.TqAuth(config.TQ_USER, config.TQ_PWD))
                g_account_enable = True
            except Exception as e:
                print('初始化默认的天勤 API 报错，重新尝试初始化无账户的 API：', {str(e)})
                g_api = tqsdk.TqApi(auth=tqsdk.TqAuth(config.TQ_USER, config.TQ_PWD))
                g_account_enable = False

        return g_api

    @staticmethod
    def close_api():
        global g_api, g_klines
        if g_api is not None:
            g_api.close()
            g_api = None
            g_klines = {}
        return True

    def get_account(self):
        global g_account
        # 使用快期的模拟账号
        if self.use_simulate_account:
            if g_account is None:
                g_account = tqsdk.TqKq()
            return g_account

        # 天勤的实盘账号，如果有设置则使用
        if config.TQ_SP_ACCOUNT == '':
            return None
        if g_account is None:
            g_account = tqsdk.TqAccount(config.TQ_SP_NAME, config.TQ_SP_ACCOUNT, config.TQ_SP_PWD)
        return g_account

    def all_stocks(self):
        """
        获取支持的所有股票列表
        :return:
        """
        global g_all_stocks
        if len(g_all_stocks) > 0:
            return g_all_stocks

        codes = []
        for c in ['FUTURE', 'CONT']:
            codes += self.get_api().query_quotes(ins_class=c)
        infos = self.get_api().query_symbol_info(codes)

        for code in codes:
            g_all_stocks.append(
                {'code': code, 'name': infos[infos['instrument_id'] == code].iloc[0]['instrument_name']}
            )
        return g_all_stocks

    @retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=5), retry=retry_if_result(lambda _r: _r is None))
    def klines(self, code: str, frequency: str,
               start_date: str = None, end_date: str = None,
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
        if args is None:
            args = {}
        if 'limit' not in args.keys():
            args['limit'] = 2000
        global g_look, g_klines
        try:
            return self._extracted_from_klines_9(start_date, end_date, code, frequency, args['limit'])
        except Exception as e:
            print(f'TQ 获取 {code} - {frequency} 行情异常： {e}')
            return None
        finally:
            g_look.release()

    def _extracted_from_klines_9(self, start_date, end_date, code, frequency, limit=2000):
        g_look.acquire()
        frequency_maps = {'w': 7 * 24 * 60 * 60, 'd': 24 * 60 * 60, '60m': 60 * 60, '30m': 30 * 60, '15m': 15 * 60,
                          '6m': 6 * 60, '5m': 5 * 60, '1m': 1 * 60, '30s': 30, '10s': 10}

        if start_date is not None and end_date is not None:
            # 有专业版权限才可以调用此方法
            klines = self.get_api().get_kline_data_series(
                symbol=code,
                duration_seconds=frequency_maps[frequency],
                start_dt=fun.str_to_datetime(start_date),
                end_dt=fun.str_to_datetime(end_date)
            )
            # raise Exception('期货行情不支持历史数据查询，因为账号不是专业版，没权限')
        else:
            key = f'{code}_{frequency}'
            if key not in g_klines.keys():
                try:
                    g_klines[key] = self.get_api().get_kline_serial(symbol=code,
                                                                    duration_seconds=frequency_maps[frequency],
                                                                    data_length=limit)
                except Exception:
                    # 异常重新关闭后进行重试
                    self.close_api()
                    g_klines[key] = self.get_api().get_kline_serial(symbol=code,
                                                                    duration_seconds=frequency_maps[frequency],
                                                                    data_length=limit)
            # 等数据更新
            self.get_api().wait_update(time.time() + 1)
            klines = g_klines[key].dropna()

        klines.loc[:, 'date'] = klines['datetime'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1e9))
        klines.loc[:, 'code'] = code

        return klines[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        获取代码列表的 Tick 信息
        :param codes:
        :return:
        """
        res_ticks = {}
        for _code in codes:
            tick = self.get_api().get_tick_serial(_code, data_length=1)
            self.get_api().wait_update(time.time() + 1)
            res_ticks[_code] = Tick(
                code=_code,
                last=tick.iloc[-1]['last_price'],
                buy1=tick.iloc[-1]['bid_price1'],
                sell1=tick.iloc[-1]['ask_price1'],
                high=tick.iloc[-1]['highest'],
                low=tick.iloc[-1]['lowest'],
                open=0,
                volume=tick.iloc[-1]['volume']
            )
        return res_ticks

    def stock_info(self, code: str) -> [Dict, None]:
        """
        获取股票的基本信息
        :param code:
        :return:
        """
        all_stocks = self.all_stocks()
        return next((stock for stock in all_stocks if stock['code'] == code), {'code': code, 'name': code})

    def now_trading(self):
        """
        返回当前是否是交易时间
        TODO 简单判断 ：9-12 , 13:30-15:00 21:00-02:30
        """
        hour = int(time.strftime('%H'))
        minute = int(time.strftime('%M'))
        if hour in {9, 10, 11, 14, 21, 22, 23, 0, 1} or (hour == 13 and minute >= 30) or (hour == 2 and minute <= 30):
            return True
        return False

    def balance(self) -> Account:
        """
        获取账户资产
        """
        global g_account_enable
        api = self.get_api(use_account=True)
        if g_account_enable is False:
            raise Exception('账户链接失败，暂时不可用，请稍后尝试')

        account = api.get_account()
        api.wait_update(time.time() + 2)
        return account

    def positions(self, code: str = None) -> Dict[str, Position]:
        """
        获取持仓
        """
        global g_account_enable
        api = self.get_api(use_account=True)
        if g_account_enable is False:
            raise Exception('账户链接失败，暂时不可用，请稍后尝试')

        positions = api.get_position(symbol=code)
        api.wait_update(time.time() + 2)
        if isinstance(positions, Position):
            return {code: positions}
        else:
            return {_code: positions[_code] for _code in positions.keys()}

    def order(self, code: str, o_type: str, amount: float, args=None):
        """
        下单接口，默认使用盘口的买一卖一价格成交，知道所有手数成交后返回
        """
        if args is None:
            args = {}

        if o_type == 'open_long':
            direction = 'BUY'
            offset = 'OPEN'
        elif o_type == 'open_short':
            direction = 'SELL'
            offset = 'OPEN'
        elif o_type == 'close_long':
            direction = 'SELL'
            offset = 'CLOSE'
        elif o_type == 'close_short':
            direction = 'BUY'
            offset = 'CLOSE'
        else:
            raise Exception('期货下单类型错误')

        global g_account_enable
        api = self.get_api(use_account=True)
        if g_account_enable is False:
            raise Exception('账户链接失败，暂时不可用，请稍后尝试')

        # 查询持仓
        if offset == 'CLOSE':
            pos = self.positions(code)[code]
            if direction == 'BUY':  # 平空，检查空仓
                if pos.pos_short < amount:
                    # 持仓手数少于要平仓的，修正为持仓数量
                    amount = pos.pos_short

                if 'SHFE' in code or 'INE.sc' in code:
                    if pos.pos_short_his >= amount:
                        offset = 'CLOSE'
                    elif pos.pos_short_today >= amount:
                        offset = 'CLOSETODAY'
                    else:
                        # 持仓不够，返回错误
                        return False
            else:
                if pos.pos_long < amount:
                    # 持仓手数少于要平仓的，修正为持仓数量
                    amount = pos.pos_long

                if 'SHFE' in code or 'INE.sc' in code:
                    if pos.pos_long_his >= amount:
                        offset = 'CLOSE'
                    elif pos.pos_long_today >= amount:
                        offset = 'CLOSETODAY'
                    else:
                        # 持仓不够，返回错误
                        return False

        order = None

        amount_left = amount
        while amount_left > 0:

            quote = api.get_quote(code)
            api.wait_update(time.time() + 2)
            price = quote.ask_price1 if direction == 'BUY' else quote.bid_price1
            if price is None:
                continue
            order = api.insert_order(code,
                                     direction=direction,
                                     offset=offset,
                                     volume=int(amount_left),
                                     limit_price=price,
                                     )
            api.wait_update(time.time() + 5)

            if order.status == 'FINISHED':
                if order.is_error:
                    print(f'下单失败，原因：{order.last_msg}')
                    return False
                break
            else:
                # 取消订单，未成交的部分继续挂单
                self.cancel_order(order)
                if order.is_error:
                    print(f'下单失败，原因：{order.last_msg}')
                    return False
                amount_left = order.volume_left

        if order is None:
            return False

        return {'id': order.order_id, 'price': order.trade_price, 'amount': amount}

    def all_orders(self):
        """
        获取所有订单 (有效订单)
        """
        global g_account_enable
        api = self.get_api(use_account=True)
        if g_account_enable is False:
            raise Exception('账户链接失败，暂时不可用，请稍后尝试')

        orders = api.get_order()
        api.wait_update(time.time() + 5)

        res_orders = []
        for _id in orders:
            _o = orders[_id]
            if _o.status == 'ALIVE':
                res_orders.append(_o)

        return res_orders

    def cancel_all_orders(self):
        """
        撤销所有订单
        """
        global g_account_enable
        api = self.get_api(use_account=True)
        if g_account_enable is False:
            raise Exception('账户链接失败，暂时不可用，请稍后尝试')

        orders = api.get_order()
        api.wait_update(time.time() + 2)
        for _id in orders:
            _o = orders[_id]
            if _o.status == 'ALIVE':
                # 有效的订单，进行撤单处理
                self.cancel_order(_o)

        return True

    def cancel_order(self, order):
        """
        取消订单，直到订单取消成功
        """
        global g_account_enable
        api = self.get_api(use_account=True)
        if g_account_enable is False:
            raise Exception('账户链接失败，暂时不可用，请稍后尝试')

        while True:
            api.cancel_order(order)
            api.wait_update(time.time() + 2)
            if order.status == 'FINISHED':
                break

        return None

    def stock_owner_plate(self, code: str):
        raise Exception('交易所不支持')

    def plate_stocks(self, code: str):
        raise Exception('交易所不支持')
