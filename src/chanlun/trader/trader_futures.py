import datetime

from chanlun.exchange.exchange_tq import ExchangeTq
from chanlun import fun
from chanlun import rd, zixuan
from chanlun.backtesting.base import Operation, POSITION
from chanlun.backtesting.backtest_trader import BackTestTrader

"""
交易所对象放到外面，不然无法进行序列化
期货使用天勤自带的模拟账号测试
"""
ex = ExchangeTq(use_simulate_account=True)


class TraderFutures(BackTestTrader):
    """
    期货交易 Demo
    """

    def __init__(self, name, is_stock=True, is_futures=False, mmds=None, log=None):
        super().__init__(name, is_stock, is_futures, mmds, log)

        self.zx = zixuan.ZiXuan('futures')

        # 每单交易手数
        self.unit_volume = 2

    # 做多买入
    def open_buy(self, code, opt: Operation):
        try:
            positions = ex.positions(code)
            if len(positions) > 0 and positions[code].pos_long > 0:
                return False

            res = ex.order(code, 'open_long', self.unit_volume)
            if res is False or res['price'] is None:
                fun.send_dd_msg('futures', f'{code} open long 下单失败')
                return False

            stock_info = ex.stock_info(code)

            msg = f"开多仓 {code} 价格 {res['price']} 数量 {self.unit_volume} 原因 {opt.msg}"
            fun.send_dd_msg('futures', msg)

            self.zx.add_stock('我的持仓', stock_info['code'], stock_info['name'])

            # 保存订单记录到 Redis 中
            save_order = {
                'code': code,
                'name': code,
                'datetime': fun.datetime_to_str(datetime.datetime.now()),
                'type': 'buy',
                'price': res['price'],
                'amount': res['amount'],
                'info': opt.msg
            }
            rd.futures_order_save(code, save_order)

            return {'price': res['price'], 'amount': res['amount']}
        except Exception as e:
            fun.send_dd_msg('futures', f'{code} open long 异常: {str(e)}')
            return False

    # 做空卖出
    def open_sell(self, code, opt: Operation):
        try:
            positions = ex.positions(code)
            if len(positions) > 0 and positions[code].pos_short > 0:
                return False

            res = ex.order(code, 'open_short', self.unit_volume)
            if res is False or res['price'] is None:
                fun.send_dd_msg('futures', f'{code} open short 下单失败')
                return False

            stock_info = ex.stock_info(code)

            msg = f"开空仓 {code} 价格 {res['price']} 数量 {self.unit_volume} 原因 {opt.msg}"
            fun.send_dd_msg('futures', msg)

            self.zx.add_stock('我的持仓', stock_info['code'], stock_info['name'])

            # 保存订单记录到 Redis 中
            save_order = {
                'code': code,
                'name': code,
                'datetime': fun.datetime_to_str(datetime.datetime.now()),
                'type': 'sell',
                'price': res['price'],
                'amount': res['amount'],
                'info': opt.msg
            }
            rd.futures_order_save(code, save_order)

            return {'price': res['price'], 'amount': res['amount']}
        except Exception as e:
            fun.send_dd_msg('futures', f'{code} open short 异常: {str(e)}')
            return False

    # 做多平仓
    def close_buy(self, code, pos: POSITION, opt: Operation):
        try:
            hold_position = ex.positions(code)
            if len(hold_position) == 0 or hold_position[code].pos_long == 0:
                # 当前无持仓，不进行操作
                return {'price': pos.price, 'amount': pos.amount}
            hold_position = hold_position[code]

            res = ex.order(code, 'close_long', pos.amount)
            if res is False or res['price'] is None:
                fun.send_dd_msg('futures', f'{code} 下单失败')
                return False
            msg = f"平多仓 {code} 价格 {res['price']} 数量 {res['amount']} 盈亏 {hold_position.float_profit}  原因 {opt.msg}"

            fun.send_dd_msg('futures', msg)

            self.zx.del_stock('我的持仓', code)

            # 保存订单记录到 Redis 中
            save_order = {
                'code': code,
                'name': code,
                'datetime': fun.datetime_to_str(datetime.datetime.now()),
                'type': 'sell',
                'price': res['price'],
                'amount': res['amount'],
                'info': opt.msg
            }
            rd.futures_order_save(code, save_order)

            return {'price': res['price'], 'amount': res['amount']}
        except Exception as e:
            fun.send_dd_msg('futures', f'{code} close buy 异常: {str(e)}')
            return False

    # 做空平仓
    def close_sell(self, code, pos: POSITION, opt: Operation):
        try:
            hold_position = ex.positions(code)
            if len(hold_position) == 0 or hold_position[code].pos_short == 0:
                # 当前无持仓，不进行操作
                return {'price': pos.price, 'amount': pos.amount}
            hold_position = hold_position[code]

            res = ex.order(code, 'close_short', pos.amount)
            if res is False or res['price'] is None:
                fun.send_dd_msg('futures', f'{code} 下单失败')
                return False
            msg = f"平空仓 {code} 价格 {res['price']} 数量 {res['amount']} 盈亏 {hold_position.float_profit}  原因 {opt.msg}"

            fun.send_dd_msg('futures', msg)

            self.zx.del_stock('我的持仓', code)

            # 保存订单记录到 Redis 中
            save_order = {
                'code': code,
                'name': code,
                'datetime': fun.datetime_to_str(datetime.datetime.now()),
                'type': 'buy',
                'price': res['price'],
                'amount': res['amount'],
                'info': opt.msg
            }
            rd.futures_order_save(code, save_order)

            return {'price': res['price'], 'amount': res['amount']}
        except Exception as e:
            fun.send_dd_msg('futures', f'{code} close sell 异常: {str(e)}')
            return False
