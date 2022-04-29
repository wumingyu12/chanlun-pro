from chanlun import fun
from chanlun.cl_interface import *
from chanlun.backtesting.base import Strategy, CLDatas, Operation, POSITION


class BackTestTrader(object):
    """
    回测交易（可继承支持实盘）
    """

    def __init__(self, name, is_stock=True, is_futures=False, mmds=None, log=None):
        """
        交易者初始化
        :param name: 交易者名称
        :param is_stock: 是否是股票交易（决定当日是否可以卖出）
        :param is_futures: 是否是期货交易（决定是否可以做空）
        :param mmds: 可交易的买卖点
        :param log: 日志展示方法
        """

        # 当前名称
        self.name = name
        self.is_stock = is_stock
        self.is_futures = is_futures
        self.allow_mmds = mmds

        # 是否打印日志
        self.log = log
        self.log_history = []

        # 盯盘对象
        self.strategy: [Strategy, None] = None

        # 存储当前运行的缠论数据
        self.cl_datas: Dict[str, CLDatas] = {}

        # 当前持仓信息
        self.positions = {}
        self.positions_history = {}
        # 持仓盈亏记录
        self.hold_profit_history = {}

        # 代码订单信息
        self.orders = {}

        # 统计结果数据
        self.results = {
            '1buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            '2buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'l2buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            '3buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'l3buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'down_pz_bc_buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'down_qs_bc_buy': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            '1sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            '2sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'l2sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            '3sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'l3sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'up_pz_bc_sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
            'up_qs_bc_sell': {'win_num': 0, 'loss_num': 0, 'win_balance': 0, 'loss_balance': 0},
        }

    def set_strategy(self, _strategy: Strategy):
        """
        设置策略对象
        :param _strategy:
        :return:
        """
        self.strategy = _strategy

    def __get_price(self, code):
        """
        回测中方法，获取股票代码当前的价格，根据最小周期 k 线收盘价
        """
        if code not in self.cl_datas.keys():
            return None
        frequencys = list(self.cl_datas[code].klines.keys())
        return float(self.cl_datas[code].klines[frequencys[-1]].iloc[-1]['close'])

    def __get_high_low_price(self, code):
        """
        回测中方法，获取当前代码最高最低值，根据最小周期 k 线获取
        """
        if code not in self.cl_datas.keys():
            return None
        frequencys = list(self.cl_datas[code].klines.keys())
        high = self.cl_datas[code].klines[frequencys[-1]].iloc[-1]['high']
        low = self.cl_datas[code].klines[frequencys[-1]].iloc[-1]['low']
        dt = self.cl_datas[code].klines[frequencys[-1]].iloc[-1]['date']
        return dt, float(high), float(low)

    def __get_now_dt(self, code):
        """
        回测中方法，获取代码当前运行到的时间，根据最小周期 k 线的最后一根时间
        """
        if code not in self.cl_datas.keys():
            return None
        frequencys = list(self.cl_datas[code].klines.keys())
        return self.cl_datas[code].klines[frequencys[-1]].iloc[-1]['date']

    # 运行的唯一入口
    def run(self, code, cl_datas: CLDatas):
        self.cl_datas[code] = cl_datas

        # 更新仓位盈亏情况
        self.__position_record(code)

        # 优先检查持仓情况
        if code in self.positions:
            for mmd in self.positions[code]:
                pos = self.positions[code][mmd]
                opt = self.strategy.close(code=code, mmd=mmd, pos=pos, cl_datas=cl_datas)
                if opt:
                    self.execute(code, opt)

        # 再执行检查机会方法
        opts = self.strategy.open(code=code, cl_datas=cl_datas)
        for opt in opts:
            self.execute(code, opt)

        return True

    # 运行结束，统一清仓
    def end(self):
        for code in self.positions:
            for mmd in self.positions[code]:
                pos = self.positions[code][mmd]
                if pos.balance > 0:
                    self.execute(code, Operation(opt='sell', mmd=mmd, msg='退出'))
        self.cl_datas = []  # 清除记录，避免序列化的问题出现
        return True

    def position_codes(self):
        """
        获取当前持仓中的股票代码，根据开仓时间排序，最新开仓的在前面
        """
        poss = []
        for _c in self.positions.keys():
            for mmd in self.positions[_c]:
                _pos = self.positions[_c][mmd]
                if _pos.balance > 0:
                    poss.append(_pos)

        if not poss:
            return []

        poss = pd.DataFrame(poss)
        poss = poss.sort_values('open_datetime', ascending=False)
        codes = list(poss['code'].to_numpy())
        return codes

    # 查询代码买卖点的持仓信息
    def query_code_mmd_pos(self, code: str, mmd: str) -> POSITION:
        if code in self.positions:
            if mmd in self.positions[code]:
                return self.positions[code][mmd]
            else:
                self.positions[code][mmd] = POSITION(code=code, mmd=mmd)
        else:
            self.positions[code] = {mmd: POSITION(code=code, mmd=mmd)}
        return self.positions[code][mmd]

    def reset_pos(self, code: str, mmd: str):
        # 增加进入历史
        self.positions[code][mmd].close_datetime = self.__get_now_dt(code).strftime('%Y-%m-%d %H:%M:%S')
        if code not in self.positions_history:
            self.positions_history[code] = []
        self.positions_history[code].append(self.positions[code][mmd])

        self.positions[code][mmd] = POSITION(code=code, mmd=mmd)
        return

    def __position_record(self, code: str):
        """
        持仓记录更新
        :param code:
        :return:
        """
        now_profit = 0
        k_date, high_price, low_price = self.__get_high_low_price(code)
        now_price = self.__get_price(code)

        if code not in self.hold_profit_history.keys():
            self.hold_profit_history[code] = {}

        if code in self.positions.keys():
            for pos in self.positions[code].values():
                if pos.balance == 0:
                    continue
                if pos.type == '做多':
                    high_profit_rate = round((high_price - pos.price) / pos.price * 100, 4)
                    low_profit_rate = round((low_price - pos.price) / pos.price * 100, 4)
                    pos.max_profit_rate = max(pos.max_profit_rate, high_profit_rate)
                    pos.max_loss_rate = min(pos.max_loss_rate, low_profit_rate)

                    pos.profit_rate = round((now_price - pos.price) / pos.price * 100, 4)
                    now_profit += pos.profit_rate / 100 * pos.balance
                if pos.type == '做空':
                    high_profit_rate = round((pos.price - low_price) / pos.price * 100, 4)
                    low_profit_rate = round((pos.price - high_price) / pos.price * 100, 4)
                    pos.max_profit_rate = max(pos.max_profit_rate, high_profit_rate)
                    pos.max_loss_rate = min(pos.max_loss_rate, low_profit_rate)

                    pos.profit_rate = round((pos.price - now_price) / pos.price * 100, 4)
                    now_profit += pos.profit_rate / 100 * pos.balance
        self.hold_profit_history[code][k_date.strftime('%Y-%m-%d %H:%M:%S')] = now_profit
        return

    # 做多买入
    def open_buy(self, code, opt: Operation):
        use_balance = 100000
        amount = round((use_balance / self.__get_price(code)) * 0.99, 4)
        return {'price': self.__get_price(code), 'amount': amount}

    # 做空卖出
    def open_sell(self, code, opt: Operation):
        use_balance = 100000
        amount = round((use_balance / self.__get_price(code)) * 0.99, 4)
        return {'price': self.__get_price(code), 'amount': amount}

    # 做多平仓
    def close_buy(self, code, pos: POSITION, opt: Operation):
        return {'price': self.__get_price(code), 'amount': pos.amount}

    # 做空平仓
    def close_sell(self, code, pos: POSITION, opt: Operation):
        return {'price': self.__get_price(code), 'amount': pos.amount}

    # 打印日志信息
    def _print_log(self, msg):
        self.log_history.append(msg)
        if self.log:
            self.log(msg)
        return

    # 执行操作
    def execute(self, code, opt: Operation):
        opt_mmd = opt.mmd
        # 检查是否在允许做的买卖点上
        if self.allow_mmds is not None and opt_mmd not in self.allow_mmds:
            return True

        pos = self.query_code_mmd_pos(code, opt_mmd)
        res = None
        # 买点，买入，开仓做多
        if 'buy' in opt_mmd and opt.opt == 'buy':
            if pos.balance > 0:
                return False
            res = self.open_buy(code, opt)
            if res is False:
                return False
            pos.type = '做多'
            pos.price = res['price']
            pos.amount = res['amount']
            pos.balance = res['price'] * res['amount']
            pos.loss_price = opt.loss_price
            pos.open_date = self.__get_now_dt(code).strftime('%Y-%m-%d')
            pos.open_datetime = self.__get_now_dt(code).strftime('%Y-%m-%d %H:%M:%S')
            pos.open_msg = opt.msg
            pos.info = opt.info

            self._print_log(
                f"[{code} - {self.__get_now_dt(code)}] // {opt_mmd} 做多买入（{res['price']} - {res['amount']}），原因： {opt.msg}")

        # 卖点，买入，开仓做空（期货）
        if self.is_futures and 'sell' in opt_mmd and opt.opt == 'buy':
            if pos.balance > 0:
                return False
            res = self.open_sell(code, opt)
            if res is False:
                return False
            pos.type = '做空'
            pos.price = res['price']
            pos.amount = res['amount']
            pos.balance = res['price'] * res['amount']
            pos.loss_price = opt.loss_price
            pos.open_date = self.__get_now_dt(code).strftime('%Y-%m-%d')
            pos.open_datetime = self.__get_now_dt(code).strftime('%Y-%m-%d %H:%M:%S')
            pos.open_msg = opt.msg
            pos.info = opt.info

            self._print_log(
                f"[{code} - {self.__get_now_dt(code)}] // {opt_mmd} 做空卖出（{res['price']} - {res['amount']}），原因： {opt.msg}")

        # 卖点，卖出，平仓做空（期货）
        if self.is_futures and 'sell' in opt_mmd and opt.opt == 'sell':
            if pos.balance == 0:
                return False
            if self.is_stock and pos.open_date == self.__get_now_dt(code).strftime('%Y-%m-%d'):
                # 股票交易，当日不能卖出
                return False
            res = self.close_sell(code, pos, opt)
            if res is False:
                return False
            sell_balance = res['price'] * res['amount']
            hold_balance = pos.balance

            profit = hold_balance - sell_balance
            if profit > 0:
                # 盈利
                self.results[opt_mmd]['win_num'] += 1
                self.results[opt_mmd]['win_balance'] += profit
            else:
                # 亏损
                self.results[opt_mmd]['loss_num'] += 1
                self.results[opt_mmd]['loss_balance'] += abs(profit)

            profit_rate = round((profit / hold_balance) * 100, 2)
            pos.profit_rate = profit_rate
            pos.close_msg = opt.msg

            self._print_log('[%s - %s] // %s 平仓做空（%s - %s） 盈亏：%s (%.2f%%)，原因： %s' % (
                code, self.__get_now_dt(code), opt_mmd, res['price'], res['amount'], profit, profit_rate, opt.msg))

            # 清空持仓
            self.reset_pos(code, opt_mmd)

        # 买点，卖出，平仓做多
        if 'buy' in opt_mmd and opt.opt == 'sell':
            if pos.balance == 0:
                return False
            if self.is_stock and pos.open_date == self.__get_now_dt(code).strftime('%Y-%m-%d'):
                # 股票交易，当日不能卖出
                return False
            res = self.close_buy(code, pos, opt)
            if res is False:
                return False
            sell_balance = res['price'] * res['amount']
            hold_balance = pos.balance
            profit = sell_balance - hold_balance
            if profit > 0:
                # 盈利
                self.results[opt_mmd]['win_num'] += 1
                self.results[opt_mmd]['win_balance'] += profit
            else:
                # 亏损
                self.results[opt_mmd]['loss_num'] += 1
                self.results[opt_mmd]['loss_balance'] += abs(profit)

            profit_rate = round((profit / hold_balance) * 100, 2)
            pos.profit_rate = profit_rate
            pos.close_msg = opt.msg

            self._print_log('[%s - %s] // %s 平仓做多（%s - %s） 盈亏：%s  (%.2f%%)，原因： %s' % (
                code, self.__get_now_dt(code), opt_mmd, res['price'], res['amount'], profit, profit_rate, opt.msg))

            # 清空持仓
            self.reset_pos(code, opt_mmd)

        if res:
            # 记录订单信息
            if code not in self.orders:
                self.orders[code] = []
            self.orders[code].append({
                'datetime': self.__get_now_dt(code),
                'type': opt.opt,
                'price': res['price'],
                'amount': res['amount'],
                'info': opt.msg,
            })
            return True

        return False
