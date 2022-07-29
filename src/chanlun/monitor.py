"""
监控相关代码
"""
from chanlun import rd
from chanlun.cl_utils import batch_cls
from chanlun.exchange import get_exchange, Market
from chanlun.fun import *


def monitoring_code(market: str, code: str, name: str, frequencys: list,
                    check_types: dict = None, is_send_msg: bool = False, cl_config=None):
    """
    监控指定股票是否出现指定的信号
    :param market: 市场
    :param code: 代码
    :param name: 名称
    :param frequencys: 检查周期
    :param check_types: 监控项目
    :param is_send_msg: 是否发送消息
    :param cl_config: 缠论配置
    :return:
    """
    if check_types is None:
        check_types = {'beichi': [], 'mmd': [], 'beichi_xd': [], 'mmd_xd': []}

    if len(check_types['beichi']) == 0 and len(check_types['mmd']) == 0 and \
            len(check_types['beichi_xd']) == 0 and len(check_types['mmd_xd']) == 0:
        return ''

    ex = get_exchange(Market(market))

    klines = {f: ex.klines(code, f) for f in frequencys}
    cl_datas: List[ICL] = batch_cls(code, klines, cl_config)

    jh_msgs = []
    bc_maps = {
        'xd': '线段背驰',
        'bi': '笔背驰',
        'pz': '盘整背驰',
        'qs': '趋势背驰'
    }
    mmd_maps = {
        '1buy': '一买点',
        '2buy': '二买点',
        'l2buy': '类二买点',
        '3buy': '三买点',
        'l3buy': '类三买点',
        '1sell': '一卖点',
        '2sell': '二卖点',
        'l2sell': '类二卖点',
        '3sell': '三卖点',
        'l3sell': '类三卖点',
    }
    for cd in cl_datas:
        bis = cd.get_bis()
        frequency = cd.get_frequency()
        if len(bis) == 0:
            continue
        end_bi = bis[-1]
        end_xd = cd.get_xds()[-1] if len(cd.get_xds()) > 0 else None
        # 检查背驰和买卖点
        jh_msgs.extend(
            {'type': f'笔 {end_bi.type} {bc_maps[bc_type]}', 'frequency': frequency, 'bi': end_bi} for bc_type in
            check_types['beichi'] if end_bi.bc_exists([bc_type], '|'))

        jh_msgs.extend(
            {'type': f'笔 {mmd_maps[mmd]}', 'frequency': frequency, 'bi': end_bi} for mmd in check_types['mmd'] if
            end_bi.mmd_exists([mmd], '|'))

        if end_xd:
            # 检查背驰和买卖点
            jh_msgs.extend(
                {'type': f'线段 {end_xd.type} {bc_maps[bc_type]}', 'frequency': frequency, 'xd': end_xd} for bc_type in
                check_types['beichi_xd'] if end_xd.bc_exists([bc_type], '|'))

            jh_msgs.extend(
                {'type': f'线段 {mmd_maps[mmd]}', 'frequency': frequency, 'xd': end_xd} for mmd in check_types['mmd_xd']
                if end_xd.mmd_exists([mmd], '|'))

    send_msgs = ""
    for jh in jh_msgs:
        if 'bi' in jh.keys():
            is_done = '笔完成' if jh['bi'].is_done() else '笔未完成'
            is_td = '停顿:' + ('Yes' if jh['bi'].td else 'No')
        else:
            is_done = '线段完成' if jh['xd'].is_done() else '线段未完成'
            is_td = ''

        if market in {'a', 'hk'}:
            is_exists = rd.jhs_save('stock', code, name, jh)
        elif market == 'futures':
            is_exists = rd.jhs_save('futures', code, name, jh)
        else:
            is_exists = rd.jhs_save('currency', code, name, jh)

        if is_exists is False and is_send_msg:
            send_msgs += '【%s - %s】触发 %s (%s - %s) \n' % (name, jh['frequency'], jh['type'], is_done, is_td)

    # print('Send_msgs: ', send_msgs)

    if len(send_msgs) > 0:
        send_dd_msg(market, send_msgs)

    return jh_msgs
