import itertools
import multiprocessing
import pickle
import random
import time
import traceback
import copy
import os

import prettytable as pt
from pyecharts import options as opts
from pyecharts.charts import Kline as cKline, Line, Bar, Grid, Scatter

from chanlun import cl, kcharts, fun, rd
from chanlun.backtesting.backtest_klines import BackTestKlines
from chanlun.backtesting.backtest_trader import BackTestTrader
from chanlun.backtesting.base import POSITION
from chanlun.cl_interface import *

from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor


class BackTest:
    """
    回测类
    """

    def __init__(self, config: dict = None):
        # 日志记录
        self.log = fun.get_logger()

        if config is None:
            return
        check_keys = ['market', 'codes', 'frequencys', 'start_datetime', 'end_datetime',
                      'cl_config', 'is_stock', 'is_futures', 'strategy']
        for _k in check_keys:
            if _k not in config.keys():
                raise Exception(f'回测配置缺少必要参数:{_k}')

        self.market = config['market']
        self.codes = config['codes']
        self.frequencys = config['frequencys']
        self.start_datetime = config['start_datetime']
        self.end_datetime = config['end_datetime']

        self.cl_config = config['cl_config']
        self.is_stock = config['is_stock']
        self.is_futures = config['is_futures']

        # 执行策略
        self.strategy = config['strategy']

        self.save_file = config.get('save_file')

        # 记录每个 code 的交易对象
        self.traders = {}

        # 回测循环加载下次周期，默认None 为回测最小周期
        self.next_frequency = None

        # 随机一个 ID，用于区别其他的回测对象
        self.__id = 16

    def save(self):
        """
        保存回测结果到配置的文件中
        """
        if self.save_file is None:
            return
        save_dict = {
            'save_file': self.save_file,
            'market': self.market,
            'codes': self.codes,
            'frequencys': self.frequencys,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'cl_config': self.cl_config,
            'is_stock': self.is_stock,
            'is_futures': self.is_futures,
            'strategy': self.strategy,
            'traders': self.traders
        }
        # 保存策略结果到 file 中，进行页面查看
        self.log.info(f'save to : {self.save_file}')
        with open(file=self.save_file, mode='wb') as file:
            pickle.dump(save_dict, file)

    def load(self, _file: str):
        """
        从指定的文件中恢复回测结果
        """
        file = open(file=_file, mode='rb')
        config_dict = pickle.load(file)
        self.save_file = config_dict['save_file']
        self.market = config_dict['market']
        self.codes = config_dict['codes']
        self.frequencys = config_dict['frequencys']
        self.start_datetime = config_dict['start_datetime']
        self.end_datetime = config_dict['end_datetime']
        self.cl_config = config_dict['cl_config']
        self.is_stock = config_dict['is_stock']
        self.is_futures = config_dict['is_futures']
        self.strategy = config_dict['strategy']
        self.traders = config_dict['traders']
        self.log.info('Load OK')
        return

    def info(self):
        """
        输出回测信息
        """
        self.log.info(fun.now_dt())
        self.log.info(f'Save File : {self.save_file}')
        self.log.info(f'STR Class : {self.strategy}')
        self.log.info(f'Run Codes : {self.codes}')
        self.log.info(f'Frequencys : {self.frequencys}')
        self.log.info(f'Start time : {self.start_datetime} End time : {self.end_datetime}')
        self.log.info(f'CL Config : {self.cl_config}')
        return True

    def run(self, next_frequency: str = None):
        """
        执行回测
        """

        self.next_frequency = next_frequency

        _st = time.time()

        # 多进程执行设置的回测对象
        # run_codes = self.codes
        # while True:
        #     with ProcessPoolExecutor(max_workers=max(1, multiprocessing.cpu_count() - 2)) as executor:
        #         executor.map(self.run_code, run_codes[0:100])
        #
        #     run_codes = []
        #     for code in self.codes:
        #         if code in self.traders.keys():
        #             continue
        #         # 从 Redis 获取执行结果，之后在进行删除
        #         key = 'backtesting_%s_%s' % (self.__id, code)
        #         p_bytes = rd.get_byte(key)
        #         if p_bytes is not None:
        #             self.traders[code] = pickle.loads(p_bytes)
        #         else:
        #             run_codes.append(code)
        #
        #     # 有时候多进程执行会不返回结果，这里多执行几遍，直到返回所有代码的结果
        #     if len(self.traders) == len(self.codes):
        #         break
        #     else:
        #         self.log.info('当前运行完成数量：%s 剩余待执行数量：%s' % (len(self.traders), len(run_codes)))
        #
        # # 执行完毕，删除缓存的回测数据
        # for code in self.codes:
        #     key = 'backtesting_%s_%s' % (self.__id, code)
        #     rd.Robj().delete(key)

        # 多线程版本
        # with ThreadPoolExecutor() as executor:
        #     for code, td in zip(self.codes, executor.map(self.run_code, self.codes)):
        #         self.traders[code] = td

        for code in self.codes:
            self.traders[code] = self.run_code(code)

        _et = time.time()

        self.log.info(f'运行完成，执行时间：{_et - _st}')
        return True

    def run_code(self, code):
        """
        执行单个的回测任务
        """

        # 如果已经执行过，就退出
        # save_key = 'backtesting_%s_%s' % (self.__id, code)
        # if rd.get_byte(save_key) is not None:
        #     return True

        _start = time.time()
        bk = BackTestKlines(
            self.market, code, self.start_datetime, self.end_datetime, self.frequencys, cl_config=self.cl_config
        )
        bk.start()
        td = BackTestTrader(code, is_stock=self.is_stock, is_futures=self.is_futures, log=self.log.info)
        td.set_strategy(self.strategy)

        while True:
            try:
                ok = bk.next(self.frequencys[-1] if self.next_frequency is None else self.next_frequency)
                if ok is False:
                    break

                # 检查所有周期收盘价是否一致，不一致说明获取行情错误
                # f_close_price = {}
                # for f in bk.cl_datas.klines.keys():
                #     f_close_price[f] = bk.cl_datas.klines[f].iloc[-1]['close']
                # if min(f_close_price.values()) != max(f_close_price.values()):
                #     raise Exception('K线数据错误，多个周期的收盘价个不一致，检查合并K线方法是否正确')

                td.run(bk.code, bk.cl_datas)
            except Exception as e:
                self.log.error(f'运行 {code} 发生错误：{e}')
                self.log.error(traceback.format_exc())
                break
        td.end()
        _end = time.time()
        self.log.info('%s Total Run: %.4f s' % (code, _end - _start))

        # 将结果序列表保存到 Redis 中，执行完成后在统一取出并删除
        # p_obj = pickle.dumps(td)
        # rd.save_byte(save_key, p_obj)

        return td

    def show_charts(self, code, frequency, change_cl_config={}):
        """
        显示指定代码指定周期的图表
        """
        show_cl_config = copy.deepcopy(self.cl_config)
        for _i, _v in change_cl_config.items():
            show_cl_config[_i] = _v
        bk = BackTestKlines(
            self.market, code, self.start_datetime, self.end_datetime, [frequency], cl_config=show_cl_config
        )
        bk.start()

        klines = bk.klines[frequency]
        cd: ICL = cl.CL(code, frequency, show_cl_config).process_klines(klines)
        td = self.traders[code]
        if self.market == 'currency':
            orders = fun.convert_currency_order_by_frequency(td.orders[code], frequency) if code in td.orders else []
        else:
            orders = fun.convert_stock_order_by_frequency(td.orders[code], frequency) if code in td.orders else []
        render = kcharts.render_charts('%s - %s' % (code, frequency), cd, orders=orders)
        return render

    def result(self, index: [str, int] = None):
        """
        输出回测结果
        如果 index 为 none 返回所有回测结果的数据
        如果 index 为 int 返回 codes 顺序下标的数据
        如果 index 为 str 返回 特定 code 的数据
        """
        if len(self.traders) == 0:
            return None
        if index is None:
            return self.__traders_result(list(self.traders.values()))
        elif isinstance(index, int):
            return self.__traders_result([list(self.traders.values())[index]])
        elif isinstance(index, str):
            return self.__traders_result([self.traders[index]])

    def backtest_charts(self, index: [str, int] = None):
        """
        输出盈利图表
        如果 index 为 none 返回所有回测结果的数据
        如果 index 为 int 返回 codes 顺序下标的数据
        如果 index 为 str 返回 特定 code 的数据
        """
        if len(self.traders) == 0:
            return None
        if index is None:
            return self.__backtest_data_show_chart(list(self.traders.values()))
        elif isinstance(index, int):
            return self.__backtest_data_show_chart([list(self.traders.values())[index]])
        elif isinstance(index, str):
            return self.__backtest_data_show_chart([self.traders[index]])

    def positions(self, index: [str, int] = None, add_columns=None):
        """
        输出历史持仓信息
        如果 index 为 none 返回所有回测结果的数据
        如果 index 为 int 返回 codes 顺序下标的数据
        如果 index 为 str 返回 特定 code 的数据
        """
        if len(self.traders) == 0:
            return None
        if index is None:
            return self.__positions_pd(list(self.traders.values()), add_columns)
        elif isinstance(index, int):
            return self.__positions_pd([list(self.traders.values())[index]], add_columns)
        elif isinstance(index, str):
            return self.__positions_pd([self.traders[index]], add_columns)

    def orders(self, index: [str, int] = None):
        """
        输出订单列表
        如果 index 为 none 返回所有订单数据
        如果 index 为 int 返回 codes 顺序下标的数据
        如果 index 为 str 返回 特定 code 的数据
        """
        if len(self.traders) == 0:
            return None
        if index is None:
            return self.__orders_pd(list(self.traders.values()))
        elif isinstance(index, int):
            return self.__orders_pd([list(self.traders.values())[index]])
        elif isinstance(index, str):
            return self.__orders_pd([self.traders[index]])

    @staticmethod
    def __traders_result(traders: List[BackTestTrader]) -> pt.PrettyTable:
        """
        所有交易者中的结果进行汇总并统计，之后格式化输出
        """

        tb = pt.PrettyTable()
        tb.field_names = ["买卖点", "成功", "失败", '胜率', "盈利", '亏损', '净利润', '回吐比例', '平均盈利', '平均亏损', '盈亏比']

        results = {
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
        for t, (mmd, value) in itertools.product(traders, results.items()):
            value['win_num'] += t.results[mmd]['win_num']
            results[mmd]['loss_num'] += t.results[mmd]['loss_num']
            results[mmd]['win_balance'] += t.results[mmd]['win_balance']
            results[mmd]['loss_balance'] += t.results[mmd]['loss_balance']

        mmds = {
            '1buy': '一类买点', '2buy': '二类买点', 'l2buy': '类二类买点', '3buy': '三类买点', 'l3buy': '类三类买点',
            'down_pz_bc_buy': '下跌盘整背驰', 'down_qs_bc_buy': '下跌趋势背驰',
            '1sell': '一类卖点', '2sell': '二类卖点', 'l2sell': '类二类卖点', '3sell': '三类卖点', 'l3sell': '类三类卖点',
            'up_pz_bc_sell': '上涨盘整背驰', 'up_qs_bc_sell': '上涨趋势背驰',
        }
        for k in results:
            mmd = mmds[k]
            win_num = results[k]['win_num']
            loss_num = results[k]['loss_num']
            shenglv = 0 if win_num == 0 and loss_num == 0 else win_num / (win_num + loss_num) * 100
            win_balance = results[k]['win_balance']
            loss_balance = results[k]['loss_balance']
            net_balance = win_balance - loss_balance
            back_rate = 0 if win_balance == 0 else loss_balance / win_balance * 100
            win_mean_balance = 0 if win_num == 0 else win_balance / win_num
            loss_mean_balance = 0 if loss_num == 0 else loss_balance / loss_num
            ykb = 0 if loss_mean_balance == 0 or win_mean_balance == 0 else win_mean_balance / loss_mean_balance

            tb.add_row(
                [mmd, win_num, loss_num, f'{str(round(shenglv, 2))}%', round(win_balance, 2), round(loss_balance, 2),
                 round(net_balance, 2), round(back_rate, 2), round(win_mean_balance, 2), round(loss_mean_balance, 2),
                 round(ykb, 4)])

        return tb

    def __backtest_data_show_chart(self, traders: List[BackTestTrader]):
        """
        回测数据图表展示
        """
        net_profit_history = {'datetime': [], 'val': []}
        hold_profit_history = {'datetime': [], 'val': []}
        hold_num_history = {'datetime': [], 'val': []}

        # 获取所有的交易日期节点，多标的测试可能会有个别的时间不齐（数据缺失），获取所有的在去重并排序
        dts = []
        for t in traders:
            for _code, _hps in t.hold_profit_history.items():
                for _dt, _hp in _hps.items():
                    if _dt not in dts:
                        dts.append(_dt)
        dts = sorted(dts, reverse=False)

        # 获取所有的持仓历史，并按照平仓时间排序
        positions: List[POSITION] = []
        for t in traders:
            for _code in t.positions_history:
                positions.extend(iter(t.positions_history[_code]))
        positions = sorted(positions, key=lambda p: p.close_datetime, reverse=False)

        # 按照平仓时间统计其中的收益总和
        dts_total_nps = {}
        for _p in positions:
            net_profit = (_p.profit_rate / 100) * _p.balance
            if _p.close_datetime not in dts_total_nps.keys():
                dts_total_nps[_p.close_datetime] = net_profit
            else:
                dts_total_nps[_p.close_datetime] += net_profit

        # 按照时间统计当前时间持仓累计盈亏
        _hold_profit_sums = {}
        _hold_num_sums = {}
        for t in traders:
            for _code, _hp in t.hold_profit_history.items():
                for _dt, _p in _hp.items():
                    if _dt not in _hold_profit_sums.keys():
                        _hold_profit_sums[_dt] = _p
                        _hold_num_sums[_dt] = 1 if _p != 0 else 0
                    else:
                        _hold_profit_sums[_dt] += _p
                        _hold_num_sums[_dt] += 1 if _p != 0 else 0

        # 按照时间累加总的收益
        total_np = 0
        for _dt in dts:
            # 累计净收益数据
            if _dt in dts_total_nps.keys():
                total_np += dts_total_nps[_dt]
            net_profit_history['datetime'].append(_dt)
            net_profit_history['val'].append(total_np)

            # 当前时间持仓累计
            hold_profit_history['datetime'].append(_dt)
            if _dt in _hold_profit_sums.keys():
                hold_profit_history['val'].append(_hold_profit_sums[_dt])
            else:
                hold_profit_history['val'].append(0)

            # 当前时间持仓数量
            hold_num_history['datetime'].append(_dt)
            if _dt in _hold_num_sums.keys():
                hold_num_history['val'].append(_hold_num_sums[_dt])
            else:
                hold_profit_history['val'] = 0

        return self.__create_backtest_charts(net_profit_history, hold_profit_history, hold_num_history)

    @staticmethod
    def __positions_pd(trades: List[BackTestTrader], add_columns: List[str]):
        """
        持仓历史转换成 pandas 数据，便于做分析
        """
        pos_objs = []
        for td in trades:
            for code in td.positions_history.keys():
                for p in td.positions_history[code]:
                    p_obj = {
                        'code': code,
                        'mmd': p.mmd,
                        'open_datetime': p.open_datetime,
                        'close_datetime': p.close_datetime,
                        'type': p.type,
                        'price': p.price,
                        'amount': p.amount,
                        'loss_price': p.loss_price,
                        'profit_rate': p.profit_rate,
                        'max_profit_rate': p.max_profit_rate,
                        'max_loss_rate': p.max_loss_rate,
                        'open_msg': p.open_msg,
                        'close_msg': p.close_msg,
                    }
                    if add_columns is not None:
                        for _col in add_columns:
                            p_obj[_col] = p.info[_col]
                    pos_objs.append(p_obj)

        return pd.DataFrame(pos_objs)

    @staticmethod
    def __orders_pd(trades: List[BackTestTrader]):
        """
        持仓历史转换成 pandas 数据，便于做分析
        """
        order_objs = []
        for td in trades:
            for code, orders in td.orders.items():
                order_objs.extend(iter(orders))
        return pd.DataFrame(order_objs)

    @staticmethod
    def __create_backtest_charts(net_profit_history: dict, hold_profit_history: dict, hold_num_history: dict):
        """
        回测结果图表展示
        :return:
        """

        net_profit_chart = (Line().add_xaxis(
            xaxis_data=net_profit_history['datetime']
        ).add_yaxis(
            series_name='净收益累计', y_axis=net_profit_history['val'], label_opts=opts.LabelOpts(is_show=False),
        ).set_global_opts(
            title_opts=opts.TitleOpts(title='回测结果图表展示'),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            yaxis_opts=opts.AxisOpts(position="right"),
            legend_opts=opts.LegendOpts(is_show=False),
            datazoom_opts=[
                opts.DataZoomOpts(is_show=False, type_="inside", xaxis_index=[0, 0], range_start=0, range_end=100),
                opts.DataZoomOpts(is_show=True, xaxis_index=[0, 1], pos_top="97%", range_start=0, range_end=100),
                opts.DataZoomOpts(is_show=False, xaxis_index=[0, 2], range_start=0, range_end=100),
            ]))

        hold_profit_chart = (Bar().add_xaxis(
            xaxis_data=hold_profit_history['datetime']
        ).add_yaxis(
            series_name='持仓盈亏变动', y_axis=hold_profit_history['val'], label_opts=opts.LabelOpts(is_show=False),
        ).set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            yaxis_opts=opts.AxisOpts(position="right"),
            legend_opts=opts.LegendOpts(is_show=False),
        ))

        hold_num_chart = (Bar().add_xaxis(
            xaxis_data=hold_num_history['datetime']
        ).add_yaxis(
            series_name='持仓数', y_axis=hold_num_history['val'], label_opts=opts.LabelOpts(is_show=False),
        ).set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            yaxis_opts=opts.AxisOpts(position="right"),
            legend_opts=opts.LegendOpts(is_show=False),
        ))

        chart = Grid(init_opts=opts.InitOpts(width="90%", height="600px", theme='white'))
        chart.add(
            net_profit_chart,
            grid_opts=opts.GridOpts(width="96%", height="60%", pos_left='1%', pos_right='3%'),
        )
        chart.add(
            hold_profit_chart,
            grid_opts=opts.GridOpts(
                pos_bottom="15%", height="25%", width="96%", pos_left='1%', pos_right='3%'
            ),
        )
        chart.add(
            hold_num_chart,
            grid_opts=opts.GridOpts(
                pos_bottom="0", height="15%", width="96%", pos_left='1%', pos_right='3%'
            ),
        )
        if "JPY_PARENT_PID" in os.environ:
            return chart.render_notebook()
        else:
            return chart.dump_options()
