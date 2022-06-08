from chanlun.cl_utils import *

"""
根据缠论数据，选择自己所需要的形态方法集合
"""


def xg_single_xd_and_bi_mmd(cl_datas: List[ICL]):
    """
    线段和笔都有出现买卖点 或 笔出现类三买 的条件
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    cd = cl_datas[0]
    if len(cd.get_xds()) == 0 or len(cd.get_bis()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bi = cd.get_bis()[-1]
    if xd.mmd_exists(['1buy', '2buy', '3buy', 'l2buy', 'l3buy']) and bi.mmd_exists(
            ['1buy', '2buy', '3buy', 'l2buy', 'l3buy']):
        return f'线段买点 【{xd.line_mmds()}】 笔买点【{bi.line_mmds()}】'
    return next((f'笔出现线段买点【{bi.line_mmds()}】' for mmd in bi.mmds if mmd.zs.zs_type == 'xd' and 'buy' in mmd.name), None)


def xg_multiple_xd_bi_mmd(cl_datas: List[ICL]):
    """
    选择 高级别线段，低级别笔 都出现买点，或者 高级别线段和高级别笔 都出现 背驰 的条件
    周期：两个周期
    适用市场：沪深A股
    作者：WX
    """
    high_data = cl_datas[0]
    low_data = cl_datas[1]
    if len(high_data.get_xds()) == 0 or len(high_data.get_bis()) == 0:
        return None
    if len(low_data.get_xds()) == 0 or len(low_data.get_bis()) == 0:
        return None

    high_xd = high_data.get_xds()[-1]
    high_bi = high_data.get_bis()[-1]
    low_bi = low_data.get_bis()[-1]
    if high_xd.mmd_exists(['1buy', '2buy', '3buy', 'l2buy', 'l3buy']) and \
            low_bi.mmd_exists(['1buy', '2buy', '3buy', 'l2buy', 'l3buy']):
        return f'{high_data.get_frequency()} 线段买点【{high_xd.line_mmds()}】 {low_data.get_frequency()} 笔买点【{low_bi.line_mmds()}】'

    if high_xd.bc_exists(['pz', 'qs']) and high_bi.bc_exists(['pz', 'qs']):
        return f'{high_data.get_frequency()} 线段背驰【{high_xd.line_bcs()}】 笔背驰【{high_bi.line_bcs()}】'

    return None


def xg_single_xd_bi_zs_zf_5(cl_datas: List[ICL]):
    """
    上涨线段的 第一个 笔中枢， 突破 笔中枢， 大涨 5% 以上的股票
    周期：单周期
    适用市场：沪深A股
    作者：Jiang Haoquan
    """
    cd = cl_datas[0]

    if len(cd.get_xds()) == 0 or len(cd.get_bi_zss()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bi_zs = cd.get_bi_zss()[-1]
    kline = cd.get_klines()[-1]

    if xd.type == 'up' \
            and xd.start.index == bi_zs.lines[0].start.index \
            and kline.h > bi_zs.zg >= kline.l and (kline.c - kline.o) / kline.o > 0.05:
        return '线段向上，当前K线突破中枢高点，并且涨幅大于 5% 涨幅'

    return None


def xg_single_xd_bi_23_overlapped(cl_datas: List[ICL]):
    """
    上涨线段的 第一个 笔中枢， 突破 笔中枢后 23买重叠的股票
    周期：单周期
    适用市场：沪深A股
    作者：Jiang Haoquan
    """
    cd = cl_datas[0]
    if len(cd.get_xds()) == 0 or len(cd.get_bi_zss()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bi_zs = cd.get_bi_zss()[-1]
    bi = cd.get_bis()[-1]
    bi_2 = cd.get_bis()[-2]
    bi_3 = cd.get_bis()[-3]

    overlapped_23_bi = bi.mmd_exists(['2buy']) and bi.mmd_exists(['3buy'])
    overlapped_23_bi_2 = bi_2.mmd_exists(['2buy']) and bi_2.mmd_exists(['3buy']) and bi.td == True
    overlapped_23_bi_3 = bi_3.mmd_exists(['2buy']) and bi_3.mmd_exists(['3buy']) and bi.mmd_exists(['l3buy'])

    if xd.type == 'up' \
            and xd.start.index == bi_zs.lines[0].start.index \
            and overlapped_23_bi or overlapped_23_bi_2 or overlapped_23_bi_3:
        return '线段向上，当前笔突破中枢高点后 2，3 买重叠'

    return None


def xg_single_day_bc_and_up_jincha(cl_datas: List[ICL]):
    """
    日线级别，倒数第二个向下笔背驰（笔背驰、盘整背驰、趋势背驰），后续macd在水上金叉
    """
    cd = cl_datas[0]
    if len(cd.get_bis()) <= 5 or len(cd.get_xds()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bis = cd.get_bis()
    down_bis = [bi for bi in bis if bi.type == 'down']
    if len(down_bis) < 2:
        return None
    if xd.type != 'down':
        return None
    if down_bis[-1].low < down_bis[-2].low:
        return None
    macd_dif = cd.get_idx()['macd']['dif'][-1]
    macd_dea = cd.get_idx()['macd']['dea'][-1]
    if macd_dif < 0 or macd_dea < 0:
        return None
    if down_bis[-2].bc_exists(['bi', 'pz', 'qs']) is False:
        return None
    # last_bi_macd_infos = cal_line_macd_infos(bis[-1], cd)
    # if bis[-1].type == 'up' and last_bi_macd_infos.gold_cross_num > 0:
    return f'前down笔背驰 {down_bis[-2].line_bcs()} macd 在零轴之上，等待接下来向上笔金叉出现。'
    # return None
