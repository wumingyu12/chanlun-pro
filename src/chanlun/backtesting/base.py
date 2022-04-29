from abc import ABC
from dataclasses import dataclass

import pandas as pd

from chanlun import cl
from chanlun.exchange.exchange import Exchange
from chanlun.cl_interface import *


@dataclass
class POSITION:
    """
    持仓对象
    """
    code: str
    mmd: str
    type: str = None
    balance: float = 0
    price: float = 0
    amount: float = 0
    loss_price: float = None
    open_date: str = None
    open_datetime: str = None
    close_datetime: str = None
    profit_rate: float = 0
    max_profit_rate: float = 0  # 仅供参考，不太精确
    max_loss_rate: float = 0  # 仅供参考，不太精确
    open_msg: str = ''
    close_msg: str = ''
    info: Dict = None


@dataclass
class Operation:
    """
    策略返回的操作指示对象
    """
    opt: str  # 操作指示  buy  买入  sell  卖出
    mmd: str  # 触发指示的 买卖点 例如：1buy  2buy  1sell 2sell
    loss_price: float = None  # 止损价格
    info: Dict[str, object] = None  # 自定义保存的一些信息
    msg: str = ''

    def __str__(self):
        return f'mmd {self.mmd} opt {self.opt} loss_price {self.loss_price} msg: {self.msg}'


class CLDatas(object):
    """
    缠论数据类，用于回测与正式交易获取缠论数据的类
    """

    def __init__(self, code, frequencys, ex: Exchange, cl_config=None):
        self.code = code
        self.frequencys = frequencys
        self.ex = ex
        self.cl_config = cl_config

        # 用于保存原始的 k 线数据
        self.klines: Dict[str, pd.DataFrame] = {}
        # 存储周期对应的缠论数据
        self.cl_datas: Dict[str, ICL] = {}

        # 初始化就调用交易所结果获取数据
        if self.ex is not None:
            for _f in self.frequencys:
                self.klines[_f] = self.ex.klines(code, _f)

    def update_kline(self, frequency, klines: pd.DataFrame):
        # 检查k线的更新时间，不能小于之前的
        if frequency in self.klines.keys():
            if self.klines[frequency].iloc[-1]['date'] > klines.iloc[-1]['date']:
                raise Exception('CLDatas 更新K线数据错误，新的日期不能小于原有的')
        self.klines[frequency] = klines

    def __getitem__(self, item) -> ICL:
        """
        按需重写这个方法，在需要使用缠论数据的时候，进行计算并返回
        """
        _f = self.frequencys[item]
        if _f in self.cl_datas.keys():
            return self.cl_datas[_f]

        cd: ICL = cl.CL(self.code, _f, self.cl_config).process_klines(self.klines[_f])
        self.cl_datas[_f] = cd

        return cd

    def all_datas(self) -> Dict[str, ICL]:
        """
        返回所有周期的缠论数据
        """
        cds = {}
        for i in range(len(self.frequencys)):
            f = self.frequencys[i]
            cd = self.__getitem__(i)
            cds[f] = cd
        return cds


class Strategy(ABC):
    """
    交易策略基类
    """

    def __init__(self):
        pass

    @abstractmethod
    def open(self, code, cl_datas: [CLDatas, List[ICL]]) -> List[Operation]:
        """
        观察行情数据，给出开仓操作建议
        :param code:
        :param cl_datas:
        :return:
        """

    @abstractmethod
    def close(self, code, mmd: str, pos: POSITION, cl_datas: [CLDatas, List[ICL]]) -> [Operation, None]:
        """
        盯当前持仓，给出平仓当下建议
        :param code:
        :param mmd:
        :param pos:
        :param cl_datas:
        :return:
        """

    @staticmethod
    def check_loss(mmd: str, pos: POSITION, price: float):
        """
        检查是否触发止损，止损返回操作对象，不出发返回 None
        """
        # 止盈止损检查
        if pos.loss_price is None:
            return None

        if 'buy' in mmd:
            if price < pos.loss_price:
                return Operation('sell', mmd, msg='%s 止损' % mmd)
        elif 'sell' in mmd:
            if price > pos.loss_price:
                return Operation('sell', mmd, msg='%s 止损' % mmd)
        return None

    @staticmethod
    def check_back_return(mmd: str, pos: POSITION, price: float, max_back_rate: float):
        """
        检查是否触发最大回撤
        """
        if max_back_rate is not None:
            profit_rate = (pos.price - price) / pos.price * 100 \
                if 'sell' in mmd else \
                (price - pos.price) / pos.price * 100
            if profit_rate > 0 and pos.max_profit_rate - profit_rate >= max_back_rate:
                return Operation('sell', mmd, msg='%s 回调止损' % mmd)
        return None

    @staticmethod
    def last_done_bi(bis: List[BI]):
        """
        获取最后一个 完成笔
        """
        for bi in bis[::-1]:
            if bi.is_done():
                return bi
        return None

    @staticmethod
    def bi_qiang_td(bi: BI, cd: ICL):
        """
        笔的强停顿判断
        判断方法：收盘价要突破分型的高低点，并且K线要是阳或阴
        距离分型太远就直接返回 False
        """
        if bi.end.done is False:
            return False
        last_k = cd.get_klines()[-1]
        # 当前bar与分型第三个bar相隔大于2个bar，直接返回 False
        if last_k.index - bi.end.klines[-1].klines[-1].index > 2:
            return False
        if bi.end.klines[-1].index == last_k.index:
            return False
        if bi.end.type == 'ding' and last_k.o > last_k.c and last_k.c < bi.end.low(cd.get_config()['fx_qj']):
            return True
        elif bi.end.type == 'di' and last_k.o < last_k.c and last_k.c > bi.end.high(cd.get_config()['fx_qj']):
            return True
        return False

    @staticmethod
    def bi_yanzhen_fx(bi: BI, cd: ICL):
        """
        检查是否符合笔验证分型条件
        查找与笔结束分型一致的后续分型，并且该分型不能高于或低于笔结束分型
        """
        last_k = cd.get_klines()[-1]
        price = last_k.c
        fxs = cd.get_fxs()
        next_fxs = [_fx for _fx in fxs if (_fx.index > bi.end.index and _fx.type == bi.end.type)]
        if len(next_fxs) == 0:
            return False
        next_fx = next_fxs[0]
        # # 当前bar与验证分型第三个bar相隔大于2个bar，直接返回 False
        # if last_k.index - next_fx.klines[-1].klines[-1].index > 2:
        #     return False

        # 两个分型不能相隔太远，两个分型中间最多两根缠论K线
        if next_fx.k.k_index - bi.end.k.k_index > 3:
            return False
        if bi.type == 'up':
            # 笔向上，验证下一个顶分型不高于笔的结束顶分型，并且当前价格要低于顶分型的最低价格
            if next_fx.done and next_fx.val < bi.end.val and price < bi.end.low(cd.get_config()['fx_qj']):
                return True
        elif bi.type == 'down':
            # 笔向下，验证下一个底分型不低于笔的结束底分型，并且两个分型不能离得太远
            if next_fx.done and next_fx.val > bi.end.val and price > bi.end.high(cd.get_config()['fx_qj']):
                return True
        return False

    def dynamic_change_loss_by_bi(self, pos: POSITION, bis: List[BI]):
        """
        动态按照笔进行止损价格的移动
        """
        if pos.loss_price is None:
            return
        last_done_bi = self.last_done_bi(bis)
        if 'buy' in pos.mmd and last_done_bi.type == 'up':
            pos.loss_price = max(pos.loss_price, last_done_bi.low)
        elif 'sell' in pos.mmd and last_done_bi.type == 'down':
            pos.loss_price = min(pos.loss_price, last_done_bi.high)

        return
