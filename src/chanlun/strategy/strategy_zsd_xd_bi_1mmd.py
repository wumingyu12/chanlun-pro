from chanlun.backtesting.base import *


class StrategyZsdXdBi1MMD(Strategy):
    """
    市场：任意
    周期：单周期

    通过递归，做走势段信号，根据低级别的一类买卖点进行

    在高级别出现买卖点或背驰，在设置的低级别中有出现过一类买卖点，则进行开仓
    平仓反过来即可
    """

    def __init__(self):
        super().__init__()

        self._max_loss_rate = 10  # 最大亏损比例设置

    def open(self, code, market_data: MarketDatas) -> List[Operation]:
        """
        开仓监控，返回开仓配置
        """
        opts = []

        high_data = market_data.get_cl_data(code, market_data.frequencys[0])
        # 没有笔或中枢，退出
        if len(high_data.get_zsds()) == 0 or len(high_data.get_zsd_zss()) == 0:
            return opts
        high_zsd = high_data.get_zsds()[-1]
        high_xd = high_data.get_xds()[-1]
        high_bi = self.last_done_bi(high_data.get_bis())
        # 如果没有背驰和买卖点，直接返回
        if len(high_zsd.line_bcs()) == 0 and len(high_zsd.line_mmds()) == 0:
            return opts
        # 三个线的方向要一致
        if high_zsd.type != high_xd.type or high_zsd.type != high_bi.type:
            return opts
        if high_xd.mmd_exists(['1buy', '1sell', '2buy', '2sell']) is False and high_bi.mmd_exists(
                ['1buy', '1sell', '2buy', '2sell']) is False:
            return opts
        # 最后笔要停顿
        if self.bi_td(high_bi, high_data) is False:
            return opts

        # 设置止损价格
        price = high_data.get_klines()[-1].c
        if self._max_loss_rate is not None:
            if high_bi.type == 'up':
                loss_price = min(high_bi.high, price * (1 + self._max_loss_rate / 100))
            else:
                loss_price = max(high_bi.low, price * (1 - self._max_loss_rate / 100))
        else:
            loss_price = high_bi.low if high_bi.type == 'down' else high_bi.high

        # 买卖点开仓
        for mmd in high_zsd.line_mmds():
            # 线段 or 笔 出现一类买卖点
            opts.append(Operation(
                'buy', mmd, loss_price, {},
                f'走势段买卖点 {mmd}, 线段买卖点 {high_xd.line_mmds()} 笔买卖点 {high_bi.line_mmds()}'
            ))
        # 背驰开仓
        for bc in high_zsd.line_bcs():
            if bc == 'zsd':
                bc = 'pz'
            bc_mmd = f'{high_bi.type}_{bc}_bc_' + ('buy' if high_bi.type == 'down' else 'sell')
            opts.append(Operation(
                'buy', bc_mmd, loss_price, {},
                f'走势段背驰 {bc}, 线段买卖点 {high_xd.line_mmds()} 笔买卖点 {high_bi.line_mmds()}')
            )
        return opts

    def close(self, code, mmd: str, pos: POSITION, market_data: MarketDatas) -> [Operation, None]:
        """
        持仓监控，返回平仓配置
        """
        if pos.balance == 0:
            return None

        high_data = market_data.get_cl_data(code, market_data.frequencys[0])
        if len(high_data.get_zsds()) == 0 or len(high_data.get_zsd_zss()) == 0:
            return False

        # 止损判断
        loss_opt = self.check_loss(mmd, pos, high_data.get_klines()[-1].c)
        if loss_opt is not None:
            return loss_opt

        high_zsd = high_data.get_zsds()[-1]
        high_xd = high_data.get_xds()[-1]
        high_bi = self.last_done_bi(high_data.get_bis())
        # 如果没有背驰和买卖点，直接返回
        if len(high_zsd.line_bcs()) == 0 and len(high_zsd.line_mmds()) == 0:
            return False
        # 三个线的方向要一致
        if high_zsd.type != high_xd.type or high_zsd.type != high_bi.type:
            return False
        # 如果低级别没有一类买卖点，退出
        if high_xd.mmd_exists(['1buy', '1sell', '2buy', '2sell']) is False and high_bi.mmd_exists(
                ['1buy', '1sell', '2buy', '2sell']) is False:
            return False
        # 如果最后一笔没有停顿，退出
        if self.bi_td(high_bi, high_data) is False:
            return False

        if 'buy' in mmd and high_zsd.type == 'up':
            return Operation(
                'sell', mmd,
                msg=f'走势段买卖点 {high_zsd.line_mmds()} 背驰 {high_zsd.line_bcs()}，线段 {high_xd.line_mmds()} 笔 {high_bi.line_mmds()}'
            )
        if 'sell' in mmd and high_zsd.type == 'down':
            return Operation(
                'sell', mmd,
                msg=f'走势段买卖点 {high_zsd.line_mmds()} 背驰 {high_zsd.line_bcs()}，线段 {high_xd.line_mmds()} 笔 {high_bi.line_mmds()}'
            )

        return None
