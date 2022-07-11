import pickle

from chanlun import rd
from chanlun.backtesting.base import Strategy, Operation, POSITION, MarketDatas
from chanlun.cl_interface import *


class BackTestTrader(object):
    """
    回测交易（可继承支持实盘）
    """

    def __init__(self, name, mode='signal',
                 is_stock=True, is_futures=False,
                 init_balance=100000, fee_rate=0.0005, max_pos=10,
                 log=None):
        """
        交易者初始化
        :param name: 交易者名称
        :param mode: 执行模式 signal 测试信号模式，固定金额开仓；trade 实际买卖模式；real 线上实盘交易
        :param is_stock: 是否是股票交易（决定当日是否可以卖出）
        :param is_futures: 是否是期货交易（决定是否可以做空）
        :param init_balance: 初始资金
        :param fee_rate: 手续费比例
        """

        # 策略基本信息
        self.name = name
        self.mode = mode
        self.is_stock = is_stock
        self.is_futures = is_futures
        self.allow_mmds = None

        # 资金情况
        self.balance = init_balance if mode == 'trade' else 0
        self.fee_rate = fee_rate
        self.fee_total = 0
        self.max_pos = max_pos

        # 是否打印日志
        self.log = log
        self.log_history = []

        # 策略对象
        self.strategy: Strategy = None

        # 回测数据对象
        self.datas: MarketDatas = None

        # 当前持仓信息
        self.positions: Dict[str, Dict[str, POSITION]] = {}
        self.positions_history = {}
        # 持仓盈亏记录
        self.hold_profit_history = {}
        # 资产历史
        self.balance_history: Dict[str, float] = {}

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

    def set_data(self, _data: MarketDatas):
        """
        设置数据对象
        """
        self.datas = _data

    def save_to_redis(self, key: str):
        """
        将对象数据保存到 Redis 中
        """
        save_infos = {
            'positions': self.positions,
            'positions_history': self.positions_history,
            'hold_profit_history': self.hold_profit_history,
            'balance_history': self.balance_history
        }
        p_obj = pickle.dumps(save_infos)
        rd.save_byte(key, p_obj)
        return True

    def load_from_redis(self, key: str):
        """
        从 Redis 中恢复之前的数据
        """
        p_bytes = rd.get_byte(key)
        if p_bytes is None:
            return False
        save_infos = pickle.loads(p_bytes)
        self.positions = save_infos['positions']
        self.positions_history = save_infos['positions_history']
        self.hold_profit_history = save_infos['hold_profit_history']
        self.balance_history = save_infos['balance_history']
        return True

    def get_price(self, code):
        """
        回测中方法，获取股票代码当前的价格，根据最小周期 k 线收盘价
        """
        price_info = self.datas.last_k_info(code)
        return price_info

    def get_now_datetime(self):
        """
        获取当前时间
        """
        if self.mode == 'real':
            return datetime.datetime.now()
        # 回测时用回测的当前时间
        return self.datas.now_date

    # 运行的唯一入口
    def run(self, code):
        # 优先检查持仓情况
        if code in self.positions:
            for mmd in self.positions[code]:
                pos = self.positions[code][mmd]
                opt = self.strategy.close(code=code, mmd=mmd, pos=pos, market_data=self.datas)
                if opt:
                    self.execute(code, opt)

        # 再执行检查机会方法
        opts = self.strategy.open(code=code, market_data=self.datas)
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
        return True

    def update_position_record(self):
        """
        更新所有持仓的盈亏情况
        """
        total_hold_profit = 0
        for code in self.positions.keys():
            now_profit, hold_balance = self.position_record(code)
            if self.mode == 'trade':
                total_hold_profit += (now_profit + hold_balance)
            else:
                total_hold_profit += now_profit
        now_datetime = self.get_now_datetime().strftime('%Y-%m-%d %H:%M:%S')
        self.balance_history[now_datetime] = total_hold_profit + self.balance

    def position_record(self, code: str) -> Tuple[float, float]:
        """
        持仓记录更新
        :param code:
        :return: 返回持仓的总金额（包括持仓盈亏）
        """
        hold_balance = 0
        now_profit = 0
        price_info = self.get_price(code)

        if code not in self.hold_profit_history.keys():
            self.hold_profit_history[code] = {}

        if code in self.positions.keys():
            for pos in self.positions[code].values():
                if pos.balance == 0:
                    continue
                if pos.type == '做多':
                    high_profit_rate = round((price_info['high'] - pos.price) / pos.price * 100, 4)
                    low_profit_rate = round((price_info['low'] - pos.price) / pos.price * 100, 4)
                    pos.max_profit_rate = max(pos.max_profit_rate, high_profit_rate)
                    pos.max_loss_rate = min(pos.max_loss_rate, low_profit_rate)

                    pos.profit_rate = round((price_info['close'] - pos.price) / pos.price * 100, 4)
                    now_profit += pos.profit_rate / 100 * pos.balance
                if pos.type == '做空':
                    high_profit_rate = round((pos.price - price_info['low']) / pos.price * 100, 4)
                    low_profit_rate = round((pos.price - price_info['high']) / pos.price * 100, 4)
                    pos.max_profit_rate = max(pos.max_profit_rate, high_profit_rate)
                    pos.max_loss_rate = min(pos.max_loss_rate, low_profit_rate)

                    pos.profit_rate = round((pos.price - price_info['close']) / pos.price * 100, 4)
                    now_profit += pos.profit_rate / 100 * pos.balance
                hold_balance += pos.balance
        self.hold_profit_history[code][price_info['date'].strftime('%Y-%m-%d %H:%M:%S')] = now_profit
        return now_profit, hold_balance

    def position_codes(self):
        """
        获取当前持仓中的股票代码，根据开仓时间排序，最新开仓的在前面
        """
        poss = []
        for _c in self.positions.keys():
            for mmd in self.positions[_c]:
                _pos = self.positions[_c][mmd]
                if _pos.balance > 0:
                    poss.append({
                        'code': _pos.code,
                        'mmd': _pos.mmd,
                        'open_datetime': _pos.open_datetime,
                        'close_datetime': _pos.close_datetime,
                        'type': _pos.type,
                        'price': _pos.price,
                        'amount': _pos.amount,
                        'loss_price': _pos.loss_price,
                        'profit_rate': _pos.profit_rate,
                        'max_profit_rate': _pos.max_profit_rate,
                        'max_loss_rate': _pos.max_loss_rate,
                        'open_msg': _pos.open_msg,
                        'close_msg': _pos.close_msg,
                    })

        if not poss:
            return []

        poss = pd.DataFrame(poss)
        poss = poss.sort_values('open_datetime', ascending=False)
        codes = list(poss['code'].to_numpy())
        return codes

    def hold_positions(self):
        """
        返回所有持仓记录
        """
        poss: List[POSITION] = []
        for code in self.positions.keys():
            for mmd, pos in self.positions[code].items():
                if pos.balance != 0:
                    poss.append(pos)
        return poss

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
        self.positions[code][mmd].close_datetime = self.get_now_datetime().strftime('%Y-%m-%d %H:%M:%S')
        if code not in self.positions_history:
            self.positions_history[code] = []
        self.positions_history[code].append(self.positions[code][mmd])

        self.positions[code][mmd] = POSITION(code=code, mmd=mmd)
        return

    # 做多买入
    def open_buy(self, code, opt: Operation):
        if self.mode == 'signal':
            use_balance = 100000
            price = self.get_price(code)['close']
            amount = round((use_balance / price) * 0.99, 4)
            return {'price': price, 'amount': amount}
        else:
            if len(self.hold_positions()) >= self.max_pos:
                return False
            price = self.get_price(code)['close']

            use_balance = (self.balance / (self.max_pos - len(self.hold_positions()))) * 0.99
            amount = use_balance / price
            if amount < 0:
                return False
            if use_balance > self.balance:
                self._print_log('%s - %s 做多开仓 资金余额不足' % (code, opt.mmd))
                return False

            fee = use_balance * self.fee_rate
            self.balance -= (use_balance + fee)
            self.fee_total += fee

            return {'price': price, 'amount': amount}

    # 做空卖出
    def open_sell(self, code, opt: Operation):
        if self.mode == 'signal':
            use_balance = 100000
            price = self.get_price(code)['close']
            amount = round((use_balance / price) * 0.99, 4)
            return {'price': price, 'amount': amount}
        else:
            if len(self.hold_positions()) >= self.max_pos:
                return False
            price = self.get_price(code)['close']

            use_balance = (self.balance / (self.max_pos - len(self.hold_positions()))) * 0.99
            amount = use_balance / price
            if amount < 0:
                return False

            if use_balance > self.balance:
                self._print_log('%s - %s 做空开仓 资金余额不足' % (code, opt.mmd))
                return False

            fee = use_balance * self.fee_rate
            self.balance -= (use_balance + fee)
            self.fee_total += fee

            return {'price': price, 'amount': amount}

    # 做多平仓
    def close_buy(self, code, pos: POSITION, opt: Operation):
        if self.mode == 'signal':
            price = self.get_price(code)['close']
            net_profit = (price * pos.amount) - (pos.price * pos.amount)
            self.balance += net_profit
            return {'price': price, 'amount': pos.amount}
        else:
            price = self.get_price(code)['close']

            hold_balance = price * pos.amount

            fee = hold_balance * self.fee_rate
            self.balance += (hold_balance - fee)
            self.fee_total += fee
            return {'price': price, 'amount': pos.amount}

    # 做空平仓
    def close_sell(self, code, pos: POSITION, opt: Operation):
        if self.mode == 'signal':
            price = self.get_price(code)['close']
            net_profit = (pos.price * pos.amount) - (price * pos.amount)
            self.balance += net_profit
            return {'price': price, 'amount': pos.amount}
        else:
            price = self.get_price(code)['close']

            hold_balance = price * pos.amount
            pos_balance = pos.price * pos.amount

            profit = pos_balance - hold_balance

            fee = hold_balance * self.fee_rate
            self.balance += (pos_balance + profit - fee)
            self.fee_total += fee

            return {'price': price, 'amount': pos.amount}

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
        order_type = None
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
            pos.open_date = self.get_now_datetime().strftime('%Y-%m-%d')
            pos.open_datetime = self.get_now_datetime().strftime('%Y-%m-%d %H:%M:%S')
            pos.open_msg = opt.msg
            pos.info = opt.info

            order_type = 'open_long'

            self._print_log(
                f"[{code} - {self.get_now_datetime()}] // {opt_mmd} 做多买入（{res['price']} - {res['amount']}），原因： {opt.msg}"
            )

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
            pos.open_date = self.get_now_datetime().strftime('%Y-%m-%d')
            pos.open_datetime = self.get_now_datetime().strftime('%Y-%m-%d %H:%M:%S')
            pos.open_msg = opt.msg
            pos.info = opt.info

            order_type = 'open_short'

            self._print_log(
                f"[{code} - {self.get_now_datetime()}] // {opt_mmd} 做空卖出（{res['price']} - {res['amount']}），原因： {opt.msg}"
            )

        # 卖点，卖出，平仓做空（期货）
        if self.is_futures and 'sell' in opt_mmd and opt.opt == 'sell':
            if pos.balance == 0:
                return False
            if self.is_stock and pos.open_date == self.get_now_datetime().strftime('%Y-%m-%d'):
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

            order_type = 'close_short'

            self._print_log('[%s - %s] // %s 平仓做空（%s - %s） 盈亏：%s (%.2f%%)，原因： %s' % (
                code, self.get_now_datetime(), opt_mmd, res['price'], res['amount'], profit, profit_rate, opt.msg))

            # 清空持仓
            self.reset_pos(code, opt_mmd)

        # 买点，卖出，平仓做多
        if 'buy' in opt_mmd and opt.opt == 'sell':
            if pos.balance == 0:
                return False
            if self.is_stock and pos.open_date == self.get_now_datetime().strftime('%Y-%m-%d'):
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

            order_type = 'close_long'

            self._print_log('[%s - %s] // %s 平仓做多（%s - %s） 盈亏：%s  (%.2f%%)，原因： %s' % (
                code, self.get_now_datetime(), opt_mmd, res['price'], res['amount'], profit, profit_rate, opt.msg))

            # 清空持仓
            self.reset_pos(code, opt_mmd)

        if res:
            # 记录订单信息
            if code not in self.orders:
                self.orders[code] = []
            self.orders[code].append({
                'datetime': self.get_now_datetime(),
                'type': order_type,
                'price': res['price'],
                'amount': res['amount'],
                'info': opt.msg,
            })
            return True

        return False
