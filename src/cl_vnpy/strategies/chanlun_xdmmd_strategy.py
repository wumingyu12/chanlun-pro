from cl_vnpy.strategies.base_strategy import *

from chanlun.strategy.strategy_xd_mmd import StrategyXDMMD


class ChanlunXdmmdStrategy(BaseStrategy):
    """
    缠论线段买卖点策略

    按照 1M K线执行 线段的买卖点策略
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
        self.STR: Strategy = StrategyXDMMD()

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
            # {'windows': 5, 'interval': Interval.MINUTE, 'callback': self.on_5m_bar},
            {'windows': 1, 'interval': Interval.MINUTE, 'callback': self.on_1m_bar},
        ]

        # 缠论依赖数据初始化
        self.cl_init()
