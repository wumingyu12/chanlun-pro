import datetime

from chanlun.exchange.exchange_futu import ExchangeFutu
from chanlun import rd, fun
from chanlun import zixuan
from chanlun.backtesting.base import Operation, POSITION
from chanlun.backtesting.backtest_trader import BackTestTrader

"""
交易所对象放到外面，不然无法进行序列化
使用富途的交易接口
"""
futu_ex = ExchangeFutu()


class TraderHKStock(BackTestTrader):
    """
    港股股票交易对象
    """

    def __init__(self, name, is_stock=False, is_futures=False, mmds=None, log=None):
        super().__init__(name, is_stock, is_futures, mmds, log)
        self.b_space = 3  # 资金分割数量

        self.zx = zixuan.ZiXuan('hk')

    # 做多买入
    def open_buy(self, code, opt: Operation):
        positions = futu_ex.positions()
        if len(positions) >= self.b_space:
            return False
        stock_info = futu_ex.stock_info(code)
        if stock_info is None:
            return False
        can_tv = futu_ex.can_trade_val(code)
        if can_tv is None:
            return False
        max_amount = (can_tv['max_margin_buy'] / (self.b_space - len(positions)))
        max_amount = max_amount - (max_amount % stock_info['lot_size'])

        if max_amount == 0:
            return False
        order = futu_ex.order(code, 'buy', max_amount)
        if order is False:
            fun.send_dd_msg('hk', f'{code} 下单失败 买入数量 {max_amount}')
            return False
        msg = f"股票买入 {code}-{stock_info['name']} 价格 {order['dealt_avg_price']} 数量 {order['dealt_amount']} 原因 {opt.msg}"

        fun.send_dd_msg('hk', msg)

        self.zx.add_stock('我的持仓', stock_info['code'], stock_info['name'])

        # 保存订单记录到 Redis 中
        save_order = {
            'code': code,
            'name': stock_info['name'],
            'datetime': fun.datetime_to_str(datetime.datetime.now()),
            'type': 'buy',
            'price': order['dealt_avg_price'],
            'amount': order['dealt_amount'],
            'info': opt.msg
        }
        rd.stock_order_save(code, save_order)

        return {'price': order['dealt_avg_price'], 'amount': order['dealt_amount']}

    # 做空卖出
    def open_sell(self, code, opt: Operation):
        positions = futu_ex.positions()
        if len(positions) >= self.b_space:
            return False
        stock_info = futu_ex.stock_info(code)
        if stock_info is None:
            return False
        can_tv = futu_ex.can_trade_val(code)
        if can_tv is None:
            return False
        max_amount = (can_tv['max_margin_short'] / (self.b_space - len(positions)))
        max_amount = max_amount - (max_amount % stock_info['lot_size'])
        if max_amount == 0:
            return False
        order = futu_ex.order(code, 'sell', max_amount)
        if order is False:
            fun.send_dd_msg('hk', f'{code} 下单失败 卖出数量 {max_amount}')
            return False
        msg = f"股票卖空 {code}-{stock_info['name']} 价格 {order['dealt_avg_price']} 数量 {order['dealt_amount']} 原因 {opt.msg}"

        fun.send_dd_msg('hk', msg)

        self.zx.add_stock('我的持仓', stock_info['code'], stock_info['name'])

        # 保存订单记录到 Redis 中
        save_order = {
            'code': code,
            'name': stock_info['name'],
            'datetime': fun.datetime_to_str(datetime.datetime.now()),
            'type': 'sell',
            'price': order['dealt_avg_price'],
            'amount': order['dealt_amount'],
            'info': opt.msg
        }
        rd.stock_order_save(code, save_order)

        return {'price': order['dealt_avg_price'], 'amount': order['dealt_amount']}

    # 做多平仓
    def close_buy(self, code, pos: POSITION, opt: Operation):
        positions = futu_ex.positions(code)
        if len(positions) == 0:
            return {'price': pos.price, 'amount': pos.amount}

        stock_info = futu_ex.stock_info(code)
        if stock_info is None:
            return False

        order = futu_ex.order(code, 'sell', pos.amount)
        if order is False:
            fun.send_dd_msg('hk', f'{code} 下单失败 平仓卖出 {pos.amount}')
            return False
        msg = '股票卖出 %s-%s 价格 %s 数量 %s 盈亏 %s (%.2f%%) 原因 %s' % (
            code, stock_info['name'], order['dealt_avg_price'], order['dealt_amount'], positions[0]['profit_val'],
            positions[0]['profit'],
            opt.msg)
        fun.send_dd_msg('hk', msg)

        self.zx.del_stock('我的持仓', stock_info['code'])

        # 保存订单记录到 Redis 中
        save_order = {
            'code': code,
            'name': stock_info['name'],
            'datetime': fun.datetime_to_str(datetime.datetime.now()),
            'type': 'sell',
            'price': order['dealt_avg_price'],
            'amount': order['dealt_amount'],
            'info': opt.msg
        }
        rd.stock_order_save(code, save_order)

        return {'price': order['dealt_avg_price'], 'amount': order['dealt_amount']}

    # 做空平仓
    def close_sell(self, code, pos: POSITION, opt: Operation):
        positions = futu_ex.positions(code)
        if len(positions) == 0:
            return {'price': pos.price, 'amount': pos.amount}

        stock_info = futu_ex.stock_info(code)
        if stock_info is None:
            return False

        order = futu_ex.order(code, 'buy', pos.amount)
        if order is False:
            fun.send_dd_msg('hk', f'{code} 下单失败 平仓买入 {pos.amount}')
            return False
        msg = '股票平空 %s-%s 价格 %s 数量 %s 盈亏 %s (%.2f%%) 原因 %s' % (
            code, stock_info['name'], order['dealt_avg_price'], order['dealt_amount'], positions[0]['profit_val'],
            positions[0]['profit'],
            opt.msg)
        fun.send_dd_msg('hk', msg)

        self.zx.del_stock('我的持仓', stock_info['code'])

        # 保存订单记录到 Redis 中
        save_order = {
            'code': code,
            'name': stock_info['name'],
            'datetime': fun.datetime_to_str(datetime.datetime.now()),
            'type': 'buy',
            'price': order['dealt_avg_price'],
            'amount': order['dealt_amount'],
            'info': opt.msg
        }
        rd.stock_order_save(code, save_order)

        return {'price': order['dealt_avg_price'], 'amount': order['dealt_amount']}
