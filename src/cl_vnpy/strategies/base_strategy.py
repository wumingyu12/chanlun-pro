from vnpy.trader.constant import Interval
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)

from chanlun import cl
from chanlun.backtesting.base import *
from chanlun.strategy.strategy_demo import StrategyDemo


class BaseStrategy(CtaTemplate):
    """
    单标的，多周期回测基类
    """

    author = "WX"
    parameters = []
    variables = []

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 固定交易手数
        self.fixed_amount = 1
        # 缠论计算配置
        self.cl_config = {'xd_bzh': 'xd_bzh_no'}
        # 这里指定缠论对策略，根据策略信号进行交易
        self.STR: Strategy = StrategyDemo()

        # klines 行情数据保存，以上的am没有date字段，还是需要自己做
        self.klines: Dict[str, pd.DataFrame] = {}
        # 记录缠论数据
        self.cl_datas: Dict[str, ICL] = {}
        # 合成的对象
        self.bgs: Dict[str, BarGenerator] = {}
        # 数据序列
        self.ams: Dict[str, ArrayManager] = {}
        # 记录持仓数据 TODO 实盘需要持久化
        self.positions: Dict[str, POSITION] = {}

        # 要运行的周期，以及回调的方法（大周期的在前面）
        self.intervals = [
            {'windows': 5, 'interval': Interval.MINUTE, 'callback': self.on_5m_bar},
            {'windows': 1, 'interval': Interval.MINUTE, 'callback': self.on_1m_bar},
        ]

        # 缠论依赖数据初始化
        self.cl_init()

    def cl_init(self):
        """
        缠论依赖的数据计算初始化
        """
        for interval in self.intervals:
            _key = '%s_%s' % (interval['windows'], interval['interval'].value)
            self.klines[_key] = pd.DataFrame([], columns=['code', 'date', 'open', 'close', 'high', 'low', 'volume'])
            self.cl_datas[_key] = cl.CL(self.vt_symbol, _key, self.cl_config)
            self.bgs[_key] = BarGenerator(
                self.on_bar,
                window=interval['windows'],
                on_window_bar=interval['callback'],
                interval=interval['interval']
            )
            self.ams[_key] = ArrayManager()

    def on_30m_bar(self, bar: BarData):
        """
        30 分钟 bar 回调方法
        """
        key = '30_1m'
        self.update_cl_data(key, bar)
        self.ams[key].update_bar(bar)
        return

    def on_15m_bar(self, bar: BarData):
        """
        15 分钟 bar 回调方法
        """
        key = '15_1m'
        self.update_cl_data(key, bar)
        self.ams[key].update_bar(bar)
        return

    def on_10m_bar(self, bar: BarData):
        """
        10 分钟 bar 回调方法
        """
        key = '10_1m'
        self.update_cl_data(key, bar)
        self.ams[key].update_bar(bar)
        return

    def on_5m_bar(self, bar: BarData):
        """
        5 分钟 bar 回调方法
        """
        key = '5_1m'
        self.update_cl_data(key, bar)
        self.ams[key].update_bar(bar)
        return

    def on_1m_bar(self, bar: BarData):
        """
        1 分钟 bar 回调方法
        """
        key = '1_1m'
        self.update_cl_data(key, bar)
        self.ams[key].update_bar(bar)
        return

    def on_init(self):
        """
        Callback when strategies is inited.
        """
        self.write_log("策略初始化")

        def update_bar(bar: BarData):
            for _, bg in self.bgs.items():
                bg.update_bar(bar)

        # 默认加载几天的历史数据（根据回测开始时间进行算，这几天的数据不参与策略计算）
        self.load_bar(5, callback=update_bar)

    def on_start(self):
        """
        Callback when strategies is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategies is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        实盘的时候才会执行，用于生成 bar
        """
        for _key, _bg in self.bgs.items():
            # 只需要执行一下就好
            _bg.update_tick(tick)
            break

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        for _, bg in self.bgs.items():
            bg.update_bar(bar)

        cds = self.get_cl_datas()

        # 这里是默认加载100个bar后， inited 才为 True
        for _, am in self.ams.items():
            if not am.inited:
                return

        if self.pos == 0:
            opts = self.STR.open(self.vt_symbol, cds)
            for opt in opts:
                if 'buy' in opt.mmd:
                    self.open_buy(bar.close_price * 1.01, self.fixed_amount, opt)
                elif 'sell' in opt.mmd:
                    self.open_sell(bar.close_price * 0.99, self.fixed_amount, opt)
        else:
            poss = self.get_poss()
            for pos in poss:
                opt = self.STR.close(self.vt_symbol, pos.mmd, pos, cds)
                if opt:
                    if 'buy' in pos.mmd:
                        self.close_buy(bar.close_price * 0.99, opt)
                    elif 'sell' in pos.mmd:
                        self.close_sell(bar.close_price * 1.01, opt)

        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass

    def update_cl_data(self, key: str, bar: BarData):
        k = {
            'code': self.vt_symbol,
            'date': bar.datetime,
            'open': bar.open_price,
            'close': bar.close_price,
            'high': bar.high_price,
            'low': bar.low_price,
            'volume': bar.volume
        }
        self.klines[key] = self.klines[key].append(k, ignore_index=True)
        self.cl_datas[key].process_klines(self.klines[key][-100::])

    def get_cl_datas(self) -> List[ICL]:
        """
        获取缠论数据对象
        """
        cds = []
        for _, cd in self.cl_datas.items():
            cds.append(cd)
        return cds

    def open_buy(self, price, amount, opt: Operation):
        """
        买入开仓
        """
        # print('open_buy')
        self.write_log('买入开仓做多，价格 %s 数量 %s 交易信号 %s' % (price, amount, opt.msg))
        res = self.buy(price, amount)

        # 记录持仓
        pos = POSITION(
            code=self.vt_symbol, mmd=opt.mmd, type='long', balance=price * amount, price=price, amount=amount,
            loss_price=opt.loss_price, open_msg=opt.msg, info=opt.info
        )
        pos_key = '%s_%s' % (self.vt_symbol, opt.mmd)
        self.positions[pos_key] = pos
        return res

    def open_sell(self, price, amount, opt: Operation):
        """
        卖出开仓
        """
        # print('open_sell')
        self.write_log('卖出开仓做空，价格 %s 数量 %s 交易信号 %s' % (price, amount, opt.msg))

        res = self.short(price, amount)

        # 记录持仓
        pos = POSITION(
            code=self.vt_symbol, mmd=opt.mmd, type='short', balance=price * amount, price=price, amount=amount,
            loss_price=opt.loss_price, open_msg=opt.msg, info=opt.info
        )
        pos_key = '%s_%s' % (self.vt_symbol, opt.mmd)
        self.positions[pos_key] = pos
        return res

    def close_buy(self, price, opt: Operation):
        """
        平多仓
        """
        # print('close_buy')
        pos_key = '%s_%s' % (self.vt_symbol, opt.mmd)
        if pos_key not in self.positions.keys():
            self.write_log('平仓多单，当前没有持仓记录 %s' % pos_key)
        pos = self.positions[pos_key]

        self.write_log('卖出平仓做多，价格 %s 数量 %s 交易信号 %s' % (price, pos.amount, opt.msg))

        res = self.sell(price, pos.amount)
        del (self.positions[pos_key])
        return res

    def close_sell(self, price, opt: Operation):
        """
        平空仓
        """
        # print('close_sell')
        pos_key = '%s_%s' % (self.vt_symbol, opt.mmd)
        if pos_key not in self.positions.keys():
            self.write_log('平仓空单，当前没有持仓记录 %s' % pos_key)
        pos = self.positions[pos_key]

        self.write_log('买入平仓做空，价格 %s 数量 %s 交易信号 %s' % (price, pos.amount, opt.msg))

        res = self.cover(price, pos.amount)
        del (self.positions[pos_key])
        return res

    def get_poss(self) -> List[POSITION]:
        """
        返回当前的持仓
        """
        poss = []
        for _k in self.positions.keys():
            if self.vt_symbol in _k:
                poss.append(self.positions[_k])
        return poss
