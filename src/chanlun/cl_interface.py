# -*- coding: utf-8 -*-
import datetime
import math
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import List, Dict

import pandas as pd


class Config(Enum):
    """
    缠论配置项
    """
    ### 分型配置项
    FX_QJ_CK = 'fx_qj_ck'  # 用顶底的缠论K线，获取分型区间
    FX_QJ_K = 'fx_qj_k'  # 用顶底的原始k线，获取分型区间
    FX_BH_YES = 'fx_bh_yes'  # 不判断顶底关系，即接受所有关系
    FX_BH_DINGDI = 'fx_bh_dingdi'  # 顶不可以在底中，但底可以在顶中
    FX_BH_DIDING = 'fx_bh_diding'  # 底不可以在顶中，但顶可以在底中
    FX_BH_NO = 'fx_bh_no'  # 顶不可以在底中，底不可以在顶中

    ### 笔配置项
    BI_TYPE_OLD = 'bi_type_old'  # 笔类型，使用老笔规则
    BI_TYPE_NEW = 'bi_type_new'  # 笔类型，使用新笔规则
    BI_TYPE_JDB = 'bi_type_jdb'  # 笔类型，简单笔
    BI_TYPE_DD = 'bi_type_dd'  # 笔类型，使用顶底成笔规则
    BI_BZH_NO = 'bi_bzh_no'  # 笔标准化，不进行标准化
    BI_BZH_YES = 'bi_bzh_yes'  # 笔标准化，进行标准化，画在最高最低上
    BI_QJ_DD = 'bi_qj_dd'  # 笔区间，使用起止的顶底点作为区间
    BI_QJ_CK = 'bi_qj_ck'  # 笔区间，使用缠论K线的最高最低价作为区间
    BI_QJ_K = 'bi_qj_k'  # 笔区间，使用原始K线的最高最低价作为区间
    BI_FX_CHD_YES = 'bi_fx_cgd_yes'  # 笔内分型，次高低可以成笔
    BI_FX_CHD_NO = 'bi_fx_cgd_no'  # 笔内分型，次高低不可以成笔

    ### 线段配置项
    XD_BZH_NO = 'xd_bzh_no'  # 线段不进行标准化
    XD_BZH_YES = 'xd_bzh_yes'  # 线段进行标准化，则线段的起止点落在线段的最高最低点
    XD_QJ_DD = 'xd_qj_dd'  # 线段区间，使用线段的顶底点作为区间
    XD_QJ_CK = 'xd_qj_ck'  # 线段区间，使用线段中缠论K线的最高最低作为区间
    XD_QJ_K = 'xd_qj_k'  # 线段区间，使用线段中原始K线的最高最低作为区间

    ### 走势类型配置项
    ZSLX_BZH_NO = 'zslx_bzh_no'  # 走势类型不进行标准化
    ZSLX_BZH_YES = 'zslx_bzh_yes'  # 走势类型进行标准化
    ZSLX_QJ_DD = 'zslx_qj_dd'  # 走势类型区间，使用线段的顶底点作为区间
    ZSLX_QJ_CK = 'zslx_qj_ck'  # 走势类型区间，使用线段中缠论K线的最高最低作为区间
    ZSLX_QJ_K = 'zslx_qj_k'  # 走势类型区间，使用线段中原始K线的最高最低作为区间

    ### 中枢配置项
    ZS_TYPE_BZ = 'zs_type_bz'  # 计算的中枢类型，标准中枢，中枢维持的方法
    ZS_TYPE_DN = 'zs_type_dn'  # 计算中枢的类型，段内中枢，形成线段内的中枢
    ZS_QJ_DD = 'zs_qj_dd'  # 中枢区间，使用线段的顶底点作为区间
    ZS_QJ_CK = 'zs_qj_ck'  # 中枢区间，使用线段中缠论K线的最高最低作为区间
    ZS_QJ_K = 'zs_qj_k'  # 中枢区间，使用线段中原始K线的最高最低作为区间
    ZS_WZGX_ZGD = 'zs_wzgx_zgd'  # 判断两个中枢的位置关系，比较方式，zg与zd 宽松比较
    ZS_WZGX_ZGGDD = 'zs_wzgx_zggdd'  # 判断两个中枢的位置关系，比较方式，zg与dd zd与gg 较为宽松比较
    ZS_WZGX_GD = 'zs_wzgx_gd'  # 判断两个中枢的位置关系，比较方式，gg与dd 严格比较


class Kline:
    """
    原始K线对象
    """

    def __init__(self, index: int, date: datetime, h: float, l: float, o: float, c: float, a: float):
        self.index: int = index
        self.date: datetime = date
        self.h: float = h
        self.l: float = l
        self.o: float = o
        self.c: float = c
        self.a: float = a

    def __str__(self):
        return f"index: {self.index} date: {self.date} h: {self.h} l: {self.l} o: {self.o} c:{self.c} a:{self.a}"


class CLKline:
    """
    缠论K线对象
    """

    def __init__(self, k_index: int, date: datetime, h: float, l: float, o: float, c: float, a: float,
                 klines: List[Kline] = None, index: int = 0, _n: int = 0, _q: bool = False):
        if klines is None:
            klines = []
        self.k_index: int = k_index
        self.date: datetime = date
        self.h: float = h
        self.l: float = l
        self.o: float = o
        self.c: float = c
        self.a: float = a
        self.klines: List[Kline] = klines  # 其中包含K线对象
        self.index: int = index
        self.n: int = _n  # 记录包含的K线数量
        self.q: bool = _q  # 是否有缺口
        self.up_qs = None  # 合并时之前的趋势

    def __str__(self):
        return f"index: {self.index} k_index:{self.k_index} date: {self.date} h: {self.h} l: {self.l} _n:{self.n} _q:{self.q}"


class FX:
    """
    分型对象
    """

    def __init__(self, _type: str, k: CLKline, klines: List[CLKline], val: float,
                 index: int = 0, done: bool = True):
        self.type: str = _type  # 分型类型 （ding 顶分型 di 底分型）
        self.k: CLKline = k
        self.klines: List[CLKline] = klines
        self.val: float = val
        self.index: int = index
        self.done: bool = done  # 分型是否完成

    def ld(self) -> int:
        """
        分型力度值，数值越大表示分型力度越大
        根据第三根K线与前两根K线的位置关系决定
        """
        ld = 0
        one_k = self.klines[0]
        two_k = self.klines[1]
        three_k = self.klines[2]
        if three_k is None:
            return ld
        if self.type == 'ding':
            # 第三个缠论K线要一根单阳线
            if len(three_k.klines) > 1 or three_k.klines[0].o > three_k.klines[0].c:
                return ld
            if three_k.h < (two_k.h - (two_k.h - two_k.l) / 2):
                # 第三个K线的高点，低于第二根的50%以下
                ld += 1
            if three_k.l < one_k.l and three_k.l < two_k.l:
                # 第三个最低点是三根中最低的
                ld += 1
        elif self.type == 'di':
            # 第三个缠论K线要一根单阴线
            if len(three_k.klines) > 1 or three_k.klines[0].o < three_k.klines[0].c:
                return ld
            if three_k.l > (two_k.l + (two_k.h - two_k.l) / 2):
                # 第三个K线的低点，低于第二根的50%之上
                ld += 1
            if three_k.h > one_k.h and three_k.h > two_k.h:
                # 第三个最低点是三根中最低的
                ld += 1
        return ld

    def high(self, qj_type: [str, Config]) -> float:
        """
        获取分型最高点
        """
        if qj_type == Config.FX_QJ_CK.value:
            # （获取缠论K线的最高点）
            high = self.klines[0].h
            for k in self.klines:
                if k is not None:
                    high = max(high, k.h)
        elif qj_type == Config.FX_QJ_K.value:
            # （获取原始K线的最高点）
            high = self.klines[0].klines[0].h
            for ck in self.klines:
                if ck is not None:
                    for k in ck.klines:
                        high = max(high, k.h)
        else:
            raise Exception(f'获取分型高点的区间类型错误 {qj_type}')

        return high

    def low(self, qj_type: [str, Config]) -> float:
        """
        获取分型的最低点（取原始K线的最低点）
        """
        if qj_type == Config.FX_QJ_CK.value:
            low = self.klines[0].l
            for k in self.klines:
                if k is not None:
                    low = min(low, k.l)
        elif qj_type == Config.FX_QJ_K.value:
            low = self.klines[0].klines[0].l
            for ck in self.klines:
                if ck is not None:
                    for k in ck.klines:
                        low = min(low, k.l)
        else:
            raise Exception(f'获取分型低点的区间类型错误 {qj_type}')
        return low

    def __str__(self):
        return f'index: {self.index} type: {self.type} date : {self.k.date} val: {self.val} done: {self.done}'


class LINE:
    """
    线的基本定义，笔和线段继承此对象
    """

    def __init__(self, start: FX, end: FX, _type: str, index: int):
        self.start: FX = start  # 线的起始位置，以分型来记录
        self.end: FX = end  # 线的结束位置，以分型来记录
        self.high: float = 0  # 根据缠论配置，得来的高低点（顶底高低 或 缠论K线高低 或 原始K线高低）
        self.low: float = 0  # 根据缠论配置，得来的高低点（顶底高低 或 缠论K线高低 或 原始K线高低）
        self.type: str = _type  # 线的方向类型 （up 上涨  down 下跌）
        self.ld: dict = {}  # 记录线的力度信息
        self.index: int = index  # 线的索引，后续查找方便

    def ding_high(self) -> float:
        return self.end.val if self.type == 'up' else self.start.val

    def di_low(self) -> float:
        return self.end.val if self.type == 'down' else self.start.val

    def jiaodu(self) -> float:
        """
        计算线段与坐标轴呈现的角度（正为上，负为下）
        """
        # 计算斜率
        k = (self.start.val - self.end.val) / (self.start.k.k_index - self.end.k.k_index)
        # 斜率转弧度
        k = math.atan(k)
        # 弧度转角度
        j = math.degrees(k)
        return j


class ZS:
    """
    中枢对象（笔中枢，线段中枢）
    """

    def __init__(self, zs_type: str, start: FX, end: FX = None, zg: float = None, zd: float = None,
                 gg: float = None, dd: float = None, _type: str = None, index: int = 0, line_num: int = 0,
                 level: int = 0, max_ld: dict = None):
        self.zs_type: str = zs_type  # 标记中枢类型 bi 笔中枢 xd 线段中枢
        self.start: FX = start
        self.lines: List[LINE, BI, XD] = []  # 中枢，记录中枢的线（笔 or 线段）对象
        self.end: FX = end
        self.zg: float = zg
        self.zd: float = zd
        self.gg: float = gg
        self.dd: float = dd
        self.type: str = _type  # 中枢类型（up 上涨中枢  down 下跌中枢  zd 震荡中枢）
        self.index: int = index
        self.line_num: int = line_num  # 中枢包含的 笔或线段 个数
        self.level: int = level  # 中枢级别 0 本级别 1 上一级别 ...
        self.max_ld: dict = max_ld  # 记录中枢中最大笔力度

        # 记录中枢内，macd 的变化情况
        self.dif_up_cross_num = 0  # dif 线上穿零轴的次数
        self.dea_up_cross_num = 0  # dea 线上穿令咒的次数
        self.dif_down_cross_num = 0  # dif 线下穿零轴的次数
        self.dea_down_cross_num = 0  # dea 线下穿零轴的次数
        self.gold_cross_num = 0  # 金叉次数
        self.die_cross_num = 0  # 死叉次数

        self.done = False  # 记录中枢是否完成
        self.real = True  # 记录是否是有效中枢

    def add_line(self, line: LINE) -> bool:
        """
        添加 笔 or 线段
        """
        self.lines.append(line)
        return True

    def zf(self) -> float:
        """
        中枢振幅
        中枢重叠区间占整个中枢区间的百分比，越大说明中枢重叠区域外的波动越小
        """
        zgzd = self.zg - self.zd
        if zgzd == 0:
            zgzd = 1
        return (zgzd / (self.gg - self.dd)) * 100

    def __str__(self):
        return f'index: {self.index} zs_type: {self.zs_type} level: {self.level} FX: ({self.start.k.date}-{self.end.k.date}) type: {self.type} zg: {self.zg} zd: {self.zd} gg: {self.gg} dd: {self.dd} done: {self.done} real: {self.real}'


class MMD:
    """
    买卖点对象
    """

    def __init__(self, name: str, zs: ZS):
        self.name: str = name  # 买卖点名称
        self.zs: ZS = zs  # 买卖点对应的中枢对象

    def __str__(self):
        return f'MMD: {self.name} ZS: {self.zs}'


class BC:
    """
    背驰对象
    """

    def __init__(self, _type: str, zs: ZS, compare_line: LINE, compare_lines: List[LINE], bc: bool):
        self.type: str = _type  # 背驰类型 （bi 笔背驰 xd 线段背驰 pz 盘整背驰 qs 趋势背驰）
        self.zs: ZS = zs  # 背驰对应的中枢
        self.compare_line: LINE = compare_line  # 比较的笔 or 线段， 在 笔背驰、线段背驰、盘整背驰有用
        self.compare_lines: List[LINE] = compare_lines  # 在趋势背驰的时候使用
        self.bc = bc  # 是否背驰

    def __str__(self):
        return f'BC type: {self.type} bc: {self.bc} zs: {self.zs}'


class BI(LINE):
    """
    笔对象
    """

    def __init__(self, start: FX, end: FX = None, _type: str = None, index: int = 0):
        super().__init__(start, end, _type, index)
        self.mmds: List[MMD] = []  # 买卖点
        self.bcs: List[BC] = []  # 背驰信息
        self.td: bool = False  # 笔是否停顿

    def __str__(self):
        return f'index: {self.index} type: {self.type} FX: ({self.start.k.date} - {self.end.k.date}) high: {self.high} low: {self.low} done: {self.is_done()}'

    def is_done(self) -> bool:
        """
        返回笔是否完成
        """
        return self.end.done

    def fx_num(self) -> int:
        """
        包含的分型数量
        """
        return self.end.index - self.start.index

    def add_mmd(self, name: str, zs: ZS) -> bool:
        """
        添加买卖点
        """
        self.mmds.append(MMD(name, zs))
        return True

    def line_mmds(self) -> list:
        """
        返回当前线所有买卖点名称
        """
        return list({m.name for m in self.mmds})

    def line_bcs(self) -> list:
        """
        返回当前线所有的背驰类型
        """
        return [_bc.type for _bc in self.bcs if _bc.bc]

    def mmd_exists(self, check_mmds: list) -> bool:
        """
        检查当前笔是否包含指定的买卖点的一个
        """
        mmds = self.line_mmds()
        return len(set(check_mmds) & set(mmds)) > 0

    def bc_exists(self, bc_type: list) -> bool:
        """
        检查是否有背驰的情况
        """
        return any(_bc.type in bc_type and _bc.bc for _bc in self.bcs)

    def add_bc(self, _type: str, zs: [ZS, None], compare_line: [LINE, None], compare_lines: List[LINE],
               bc: bool) -> bool:
        """
        添加背驰点
        """
        self.bcs.append(BC(_type, zs, compare_line, compare_lines, bc))
        return True


class TZXL:
    """
    特征序列
    """

    def __init__(self, line: [LINE, None], pre_line: LINE, _max: float, _min: float, line_bad: bool, done: bool):
        self.line: [LINE, None] = line
        self.max: float = _max
        self.min: float = _min
        self.pre_line: LINE = pre_line
        self.line_bad: bool = line_bad
        self.lines: List[LINE] = [line]
        self.done: bool = done

    def __str__(self):
        return f'done {self.done} max {self.max} min {self.min} line_bad {self.line_bad} line {self.line} pre_line {self.pre_line} num {len(self.lines)}'


class XLFX:
    """
    序列分型
    """

    def __init__(self, _type: str, xl: TZXL, xls: List[TZXL], done: bool = True):
        self.type: str = _type
        self.high: float = xl.max
        self.low: float = xl.min
        self.xl: TZXL = xl
        self.xls: List[TZXL] = xls

        if self.type == 'ding' and self.xls[0].max < self.xls[1].min:
            self.qk = True  # 分型是否有缺口
        elif self.type == 'di' and self.xls[0].min > self.xls[1].max:
            self.qk = True
        else:
            self.qk = False
        self.line_bad = xl.line_bad  # 标记是否线破坏
        self.fx_high = max(_xl.max for _xl in self.xls)
        self.fx_low = min(_xl.min for _xl in self.xls)

        self.done = done  # 序列分型是否完成

    def __str__(self):
        return f"XLFX type : {self.type} done : {self.done} qk : {self.qk} line_bad : {self.line_bad} high : {self.high} low : {self.low} xl : {self.xl}"


class XD(LINE):
    """
    线段对象
    """

    def __init__(self, start: FX, end: FX, start_line: LINE, end_line: LINE = None, _type: str = None,
                 ding_fx: XLFX = None, di_fx: XLFX = None,
                 index: int = 0):
        super().__init__(start, end, _type, index)

        self.start_line: LINE = start_line  # 线段起始笔
        self.end_line: LINE = end_line  # 线段结束笔
        self.mmds: List[MMD] = []  # 买卖点
        self.bcs: List[BC] = []  # 背驰信息
        self.ding_fx: XLFX = ding_fx
        self.di_fx: XLFX = di_fx

    def is_qk(self) -> bool:
        """
        成线段的分型是否有缺口
        """
        return self.ding_fx.qk if self.type == 'up' else self.di_fx.qk

    def is_line_bad(self) -> bool:
        """
        成线段的分数，是否背笔破坏（被笔破坏不等于线段结束，但是有大概率是结束了）
        """
        return self.ding_fx.line_bad if self.type == 'up' else self.di_fx.line_bad

    def add_mmd(self, name: str, zs: ZS) -> bool:
        """
        添加买卖点
        """
        self.mmds.append(MMD(name, zs))
        return True

    def line_mmds(self) -> list:
        """
        返回当前线段所有买卖点名称
        """
        return list({m.name for m in self.mmds})

    def line_bcs(self) -> list:
        return [_bc.type for _bc in self.bcs if _bc.bc]

    def mmd_exists(self, check_mmds: list) -> bool:
        """
        检查当前笔是否包含指定的买卖点的一个
        """
        mmds = self.line_mmds()
        return len(set(check_mmds) & set(mmds)) > 0

    def bc_exists(self, bc_type: list) -> bool:
        """
        检查是否有背驰的情况
        """
        return any(_bc.type in bc_type and _bc.bc for _bc in self.bcs)

    def add_bc(self, _type: str, zs: [ZS, None], compare_line: LINE, compare_lines: List[LINE], bc: bool) -> bool:
        """
        添加背驰点
        """
        self.bcs.append(BC(_type, zs, compare_line, compare_lines, bc))
        return True

    def is_done(self) -> bool:
        """
        线段是否完成
        """
        return self.ding_fx.done if self.type == 'up' else self.di_fx.done

    def __str__(self):
        return f'XD index: {self.index} type: {self.type} start: {self.start_line.start.k.date} end: {self.end_line.end.k.date} high: {self.high} low: {self.low} done: {self.is_done()}'


class LOW_LEVEL_QS:

    def __init__(self):
        self.zss: List[ZS] = []  # 低级别线构成的中枢列表
        self.zs_num: int = 0
        self.lines: List[LINE] = []  # 包含的低级别线
        self.line_num: int = 0
        self.bc_line: [LINE, None] = None  # 背驰的线
        self.last_line: [LINE, None] = None  # 最后一个线
        self.qs: bool = False  # 是否形成趋势
        self.pz: bool = False  # 是否形成盘整
        self.qs_bc: bool = False  # 是否趋势背驰
        self.pz_bc: bool = False  # 是否盘整背驰


class ICL(metaclass=ABCMeta):
    """
    缠论数据分析接口定义
    """

    @abstractmethod
    def __init__(self, code: str, frequency: str, config: [dict, None] = None):
        """
        缠论计算
        :param code: 代码
        :param frequency: 周期
        :param config: 计算缠论依赖的配置项
        """
        pass

    @abstractmethod
    def process_klines(self, klines: pd.DataFrame):
        """
        计算k线缠论数据
        传递 pandas 数据，需要包括以下列：
            date  时间日期  datetime 格式，对于在 DataFrame 中 date 不是日期格式的，需要执行 pd.to_datetime 方法转换下
            high  最高价
            low   最低价
            open  开盘价
            close  收盘价
            volume  成交量

        可增量多次调用，重复已计算的会自动跳过，最后一个 bar 会进行更新
        """
        pass

    @abstractmethod
    def get_code(self) -> str:
        """
        返回计算的标的代码
        """
        pass

    @abstractmethod
    def get_frequency(self) -> str:
        """
        返回计算的周期参数
        """
        pass

    def get_config(self) -> dict:
        """
        返回计算时使用的缠论配置项
        """
        pass

    @abstractmethod
    def get_klines(self) -> List[Kline]:
        """
        返回原始K线列表
        """
        pass

    @abstractmethod
    def get_cl_klines(self) -> List[CLKline]:
        """
        返回合并后的缠论K线列表
        """
        pass

    @abstractmethod
    def get_idx(self) -> dict:
        """
        返回计算的指标数据
        """
        pass

    @abstractmethod
    def get_fxs(self) -> List[FX]:
        """
        返回缠论分型列表
        """
        pass

    @abstractmethod
    def get_bis(self) -> List[BI]:
        """
        返回计算缠论笔列表
        """
        pass

    @abstractmethod
    def get_xds(self) -> List[XD]:
        """
        返回计算缠论线段列表
        """
        pass

    @abstractmethod
    def get_zslxs(self) -> List[XD]:
        """
        返回计算缠论走势类型列表
        """
        pass

    @abstractmethod
    def get_bi_zss(self) -> List[ZS]:
        """
        返回计算缠论笔中枢列表
        """
        pass

    @abstractmethod
    def get_xd_zss(self) -> List[ZS]:
        """
        返回计算缠论线段中枢（走势中枢）
        """
        pass


@abstractmethod
def batch_cls(code, klines: Dict[str, pd.DataFrame], config: dict = None) -> List[ICL]:
    """
    批量计算并获取 缠论 数据
    :param code: 计算的标的
    :param klines: 计算的 k线 数据，每个周期对应一个 k线DataFrame，例如 ：{'30m': klines_30m, '5m': klines_5m}
    :param config: 缠论配置
    :return: 返回计算好的缠论数据对象，List 列表格式，按照传入的 klines.keys 顺序返回 如上调用：[0] 返回 30m 周期数据 [1] 返回 5m 数据
    """
    pass


class IMultiLevelAnalyse(metaclass=ABCMeta):
    """
    多级别分析工具类
    """

    @abstractmethod
    def low_level_qs(self, up_line: LINE, low_line_type='bi') -> LOW_LEVEL_QS:
        """
        根据高级别线，查询低级别的趋势
        """

    @abstractmethod
    def up_bi_low_level_qs(self) -> LOW_LEVEL_QS:
        """
        高级别笔，最后一笔的低级别趋势信息(低级别查找的是笔)
        """

    @abstractmethod
    def up_xd_low_level_qs(self) -> LOW_LEVEL_QS:
        """
        高级别线段，最后一线段的低级别趋势信息(低级别查找的是笔)
        """
