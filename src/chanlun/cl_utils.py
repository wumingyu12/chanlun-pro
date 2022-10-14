import hashlib
import json

from chanlun import rd, fun
from chanlun.cl_interface import *
from chanlun import cl

# 缓存计算好的缠论数据，第二次则不用重新计算了，减少计算消耗的时间
_global_cache_day = datetime.datetime.now().strftime('%Y%m%d')
_global_caches: Dict[str, ICL] = {}


def batch_cls(
        code, klines: Dict[str, pd.DataFrame],
        config: dict = None, start_datetime: datetime.datetime = None) -> List[ICL]:
    """
    批量计算并获取 缠论 数据
    :param code: 计算的标的
    :param klines: 计算的 k线 数据，每个周期对应一个 k线DataFrame，例如 ：{'30m': klines_30m, '5m': klines_5m}
    :param config: 缠论配置
    :param start_datetime: 开始分析的时间
    :return: 返回计算好的缠论数据对象，List 列表格式，按照传入的 klines.keys 顺序返回 如上调用：[0] 返回 30m 周期数据 [1] 返回 5m 数据
    """
    global _global_cache_day, _global_caches
    # 只记录当天的缓存，第二天缓存清空
    if _global_cache_day != datetime.datetime.now().strftime('%Y%m%d'):
        _global_cache_day = datetime.datetime.now().strftime('%Y%m%d')
        _global_caches = {}

    cls = []
    # _time_s = time.time()
    for f, k in klines.items():
        key = hashlib.md5(f'{code}_{f}_{config}_{start_datetime}'.encode('UTF-8')).hexdigest()
        if key in _global_caches.keys():
            # print('使用缓存')
            cls.append(_global_caches[key].process_klines(k))
        else:
            # print('重新计算')
            _global_caches[key] = cl.CL(code, f, config, start_datetime)
            cls.append(_global_caches[key].process_klines(k))
    # print('计算缠论数据用时:' + str(time.time() - _time_s))
    return cls


def cal_klines_macd_infos(start_k: Kline, end_k: Kline, cd: ICL) -> MACD_INFOS:
    """
    计算线中macd信息
    """
    infos = MACD_INFOS()

    idx = cd.get_idx()
    dea = np.array(idx['macd']['dea'][start_k.index:end_k.index + 1])
    dif = np.array(idx['macd']['dif'][start_k.index:end_k.index + 1])
    if len(dea) < 2 or len(dif) < 2:
        return infos
    zero = np.zeros(len(dea))

    infos.dif_up_cross_num = len(up_cross(dif, zero))
    infos.dif_down_cross_num = len(down_cross(dif, zero))
    infos.dea_up_cross_num = len(up_cross(dea, zero))
    infos.dea_down_cross_num = len(down_cross(dea, zero))
    infos.gold_cross_num = len(up_cross(dif, dea))
    infos.die_cross_num = len(down_cross(dif, dea))
    infos.last_dif = dif[-1]
    infos.last_dea = dea[-1]
    return infos


def cal_line_macd_infos(line: LINE, cd: ICL) -> MACD_INFOS:
    """
    计算线中macd信息
    """
    infos = MACD_INFOS()

    idx = cd.get_idx()
    dea = np.array(idx['macd']['dea'][line.start.k.k_index:line.end.k.k_index + 1])
    dif = np.array(idx['macd']['dif'][line.start.k.k_index:line.end.k.k_index + 1])
    if len(dea) < 2 or len(dif) < 2:
        return infos
    zero = np.zeros(len(dea))

    infos.dif_up_cross_num = len(up_cross(dif, zero))
    infos.dif_down_cross_num = len(down_cross(dif, zero))
    infos.dea_up_cross_num = len(up_cross(dea, zero))
    infos.dea_down_cross_num = len(down_cross(dea, zero))
    infos.gold_cross_num = len(up_cross(dif, dea))
    infos.die_cross_num = len(down_cross(dif, dea))
    infos.last_dif = dif[-1]
    infos.last_dea = dea[-1]
    return infos


def cal_zs_macd_infos(zs: ZS, cd: ICL) -> MACD_INFOS:
    """
    计算中枢的macd信息
    """
    infos = MACD_INFOS()
    dea = np.array(cd.get_idx()['macd']['dea'][zs.start.k.k_index:zs.end.k.k_index + 1])
    dif = np.array(cd.get_idx()['macd']['dif'][zs.start.k.k_index:zs.end.k.k_index + 1])
    if len(dea) < 2 or len(dif) < 2:
        return infos
    zero = np.zeros(len(dea))

    infos.dif_up_cross_num = len(up_cross(dif, zero))
    infos.dif_down_cross_num = len(down_cross(dif, zero))
    infos.dea_up_cross_num = len(up_cross(dea, zero))
    infos.dea_down_cross_num = len(down_cross(dea, zero))
    infos.gold_cross_num = len(up_cross(dif, dea))
    infos.die_cross_num = len(down_cross(dif, dea))
    infos.last_dif = dif[-1]
    infos.last_dea = dea[-1]
    return infos


def up_cross(one_list: np.array, two_list: np.array):
    """
    获取上穿信号列表
    """
    assert len(one_list) == len(two_list), '信号输入维度不相等'
    if len(one_list) < 2:
        return []
    cross = []
    for i in range(1, len(two_list)):
        if one_list[i - 1] < two_list[i - 1] and one_list[i] > two_list[i]:
            cross.append(i)
    return cross


def down_cross(one_list: np.array, two_list: np.array):
    """
    获取下穿信号列表
    """
    assert len(one_list) == len(two_list), '信号输入维度不相等'
    if len(one_list) < 2:
        return []
    cross = []
    for i in range(1, len(two_list)):
        if one_list[i - 1] > two_list[i - 1] and one_list[i] < two_list[i]:
            cross.append(i)
    return cross


def last_done_bi(cd: ICL):
    """
    获取最后一个 完成笔
    """
    bis = cd.get_bis()
    if len(bis) == 0:
        return None
    for bi in bis[::-1]:
        if bi.is_done():
            return bi
    return None


def bi_qk_num(cd: ICL, bi: BI) -> Tuple[int, int]:
    """
    获取笔的缺口数量（分别是向上跳空，向下跳空数量）
    """
    up_qk_num = 0
    down_qk_num = 0
    klines = cd.get_klines()[bi.start.k.k_index:bi.end.k.k_index + 1]
    for i in range(1, len(klines)):
        pre_k = klines[i - 1]
        now_k = klines[i]
        if now_k.l > pre_k.h:
            up_qk_num += 1
        elif now_k.h < pre_k.l:
            down_qk_num += 1
    return up_qk_num, down_qk_num


def query_cl_chart_config(market: str, code: str) -> Dict[str, object]:
    """
    查询指定市场和标的下的缠论和画图配置
    """
    # 如果是期货，代码进行特殊处理，只保留核心的交易所和品种信息，其他的去掉
    if market == 'futures':
        code = code.upper().replace('KQ.M@', '')
        code = ''.join([i for i in code if not i.isdigit()])

    config: str = rd.Robj().hget(f'config_{market}', code)
    if config is None:
        config: str = rd.Robj().hget(f'config_{market}', 'common')
    # 默认配置设置，用于在前台展示设置值
    default_config = {
        'config_use_type': 'common',
        # 缠论默认配置项
        'kline_type': Config.KLINE_TYPE_DEFAULT.value,
        'fx_qj': Config.FX_QJ_K.value,
        'fx_bh': Config.FX_BH_YES.value,
        'bi_type': Config.BI_TYPE_OLD.value,
        'bi_bzh': Config.BI_BZH_YES.value,
        'bi_qj': Config.BI_QJ_DD.value,
        'bi_fx_cgd': Config.BI_FX_CHD_YES.value,
        # 'xd_bzh': Config.XD_BZH_NO.value, # TODO 移除配置
        'xd_qj': Config.XD_QJ_DD.value,
        # 'zsd_bzh': Config.ZSD_BZH_NO.value, # TODO 移除配置
        'zsd_qj': Config.ZSD_QJ_DD.value,
        'zs_bi_type': [Config.ZS_TYPE_BZ.value],
        'zs_xd_type': [Config.ZS_TYPE_BZ.value],
        'zs_qj': Config.ZS_QJ_DD.value,
        'zs_wzgx': Config.ZS_WZGX_ZGGDD.value,
        'idx_macd_fast': 12,
        'idx_macd_slow': 26,
        'idx_macd_signal': 9,
        # 画图默认配置
        'chart_show_infos': '1',
        'chart_show_fx': '1',
        'chart_show_bi_zs': '1',
        'chart_show_xd_zs': '1',
        'chart_show_bi_mmd': '1',
        'chart_show_xd_mmd': '1',
        'chart_show_bi_bc': '1',
        'chart_show_xd_bc': '1',
        'chart_show_ma': '1',
        'chart_show_boll': '1',
        'chart_show_futu': 'macd',
        'chart_show_atr_stop_loss': False,
        'chart_show_ld': 'xd',
        'chart_kline_nums': 1000,
        'chart_idx_ma_period': '120,250',
        'chart_idx_vol_ma_period': '5,60',
        'chart_idx_boll_period': 20,
        'chart_idx_rsi_period': 14,
        'chart_idx_atr_period': 14,
        'chart_idx_atr_multiplier': 1.5,
        'chart_idx_cci_period': 14,
        'chart_idx_kdj_period': '9,3,3',
        'chart_qstd': 'xd,0',
    }

    if config is None:
        return default_config
    config: Dict[str, object] = json.loads(config)
    for _key, _val in default_config.items():
        if _key not in config.keys():
            config[_key] = _val

    return config


def set_cl_chart_config(market: str, code: str, config: Dict[str, object]) -> bool:
    """
    设置指定市场和标的下的缠论和画图配置
    """
    # 如果是期货，代码进行特殊处理，只保留核心的交易所和品种信息，其他的去掉
    if market == 'futures':
        code = code.upper().replace('KQ.M@', '')
        code = ''.join([i for i in code if not i.isdigit()])

    # 读取原来的配置，使用新的配置项进行覆盖，并保存
    old_config = query_cl_chart_config(market, code)
    if config['config_use_type'] == 'custom' and code is None:
        return False
    elif config['config_use_type'] == 'common':
        rd.Robj().hdel(f'config_{market}', code)

    for new_key, new_val in config.items():
        if new_key in old_config.keys():
            old_config[new_key] = new_val
        else:
            old_config[new_key] = new_val

    rd.Robj().hset(
        f'config_{market}', code if config['config_use_type'] == 'custom' else 'common', json.dumps(old_config)
    )
    return True


def del_cl_chart_config(market: str, code: str) -> bool:
    """
    删除指定市场标的的独立配置项
    """
    # 如果是期货，代码进行特殊处理，只保留核心的交易所和品种信息，其他的去掉
    if market == 'futures':
        code = code.upper().replace('KQ.M@', '')
        code = ''.join([i for i in code if not i.isdigit()])

    rd.Robj().hdel(f'config_{market}', code)
    return True


def cl_qstd(cd: ICL, line_type='xd', line_num: int = 5):
    """
    缠论线段的趋势通道
    基于已完成的最后 n 条线段，线段最高两个点，线段最低两个点连线，作为趋势通道线指导交易（不一定精确）
    """
    lines = cd.get_xds() if line_type == 'xd' else cd.get_bis()
    qs_lines = []
    for i in range(1, len(lines)):
        xd = lines[-i]
        if xd.is_done():
            qs_lines.append(xd)
        if len(qs_lines) == line_num:
            break

    if len(qs_lines) != line_num:
        return None

    # 获取线段的高低点并排序
    line_highs = [{'val': l.high, 'index': l.end.k.k_index, 'date': l.end.k.date} for l in qs_lines if l.type == 'up']
    line_lows = [{'val': l.low, 'index': l.end.k.k_index, 'date': l.end.k.date} for l in qs_lines if l.type == 'down']
    if len(line_highs) < 2 or len(line_lows) < 2:
        return None
    line_highs = sorted(line_highs, key=lambda v: v['val'], reverse=True)
    line_lows = sorted(line_lows, key=lambda v: v['val'], reverse=False)

    def xl(one, two):
        # 计算斜率
        k = (one['val'] - two['val']) / (one['index'] - two['index'])
        return k

    qstd = {
        'up': {'one': line_highs[0], 'two': line_highs[1], 'xl': xl(line_highs[0], line_highs[1])},
        'down': {'one': line_lows[0], 'two': line_lows[1], 'xl': xl(line_lows[0], line_lows[1])},
    }
    # 图标上展示的坐标设置
    chart_up_start = {
        'val': line_highs[0]['val'] - qstd['up']['xl'] * (line_highs[0]['index'] - qs_lines[-1].start.k.k_index),
        'index': qs_lines[-1].start.k.k_index,
        'date': qs_lines[-1].start.k.date
    }
    chart_up_end = {
        'val': line_highs[0]['val'] - qstd['up']['xl'] * (line_highs[0]['index'] - cd.get_klines()[-1].index),
        'index': cd.get_klines()[-1].index,
        'date': cd.get_klines()[-1].date
    }
    chart_down_start = {
        'val': line_lows[0]['val'] - qstd['down']['xl'] * (line_lows[0]['index'] - qs_lines[-1].start.k.k_index),
        'index': qs_lines[-1].start.k.k_index,
        'date': qs_lines[-1].start.k.date
    }
    chart_down_end = {
        'val': line_lows[0]['val'] - qstd['down']['xl'] * (line_lows[0]['index'] - cd.get_klines()[-1].index),
        'index': cd.get_klines()[-1].index,
        'date': cd.get_klines()[-1].date
    }
    qstd['up']['chart'] = {
        'x': [chart_up_start['date'], chart_up_end['date']],
        'y': [chart_up_start['val'], chart_up_end['val']],
    }
    qstd['down']['chart'] = {
        'x': [chart_down_start['date'], chart_down_end['date']],
        'y': [chart_down_start['val'], chart_down_end['val']],
    }

    # 计算当前价格和趋势线的位置关系
    now_point = {'val': cd.get_klines()[-1].c, 'index': cd.get_klines()[-1].index, 'date': cd.get_klines()[-1].date}
    qstd['up']['now'] = 'up' if xl(chart_up_start, now_point) > qstd['up']['xl'] else 'down'
    qstd['down']['now'] = 'up' if xl(chart_down_start, now_point) > qstd['down']['xl'] else 'down'

    return qstd


def prices_jiaodu(prices):
    """
    技术价格序列中，起始与终点的角度（正为上，负为下）

    弧度 = dy / dx
        dy = 终点与起点的差值
        dx = 固定位 100000
        dy 如果不足六位数，进行补位
    不同品种的标的价格有差异，这时计算的角度会有很大的不同，不利于量化，将 dy 固定，变相的将所有标的放在一个尺度进行对比
    """
    if prices[-1] == prices[0]:
        return 0
    dy = max(prices[-1], prices[0]) - min(prices[-1], prices[0])
    dx = 100000
    while True:
        dy_len = len(str(int(dy)))
        if dy_len < 6:
            dy = dy * (10 ** (6 - dy_len))
        elif dy_len > 6:
            dy = dy / (10 ** (dy_len - 6))
        else:
            break
    # 弧度
    k = math.atan2(dy, dx)
    # 弧度转角度
    j = math.degrees(k)
    return j if prices[-1] > prices[0] else -j


def cl_date_to_tv_chart(cd: ICL, config):
    """
    将缠论数据，转换成 tv 画图的坐标数据
    """
    bi_chart_data = []
    for bi in cd.get_bis():
        bi_chart_data.append({
            'points': [
                {'time': fun.datetime_to_int(bi.start.k.date), 'price': bi.start.val},
                {'time': fun.datetime_to_int(bi.end.k.date), 'price': bi.end.val},
            ],
            'linestyle': '0' if bi.is_done() else '1',
        })

    xd_chart_data = []
    for xd in cd.get_xds():
        xd_chart_data.append({
            'points': [
                {'time': fun.datetime_to_int(xd.start.k.date), 'price': xd.start.val},
                {'time': fun.datetime_to_int(xd.end.k.date), 'price': xd.end.val},
            ],
            'linestyle': '0' if xd.is_done() else '1',
        })
    zsd_chart_data = []
    for zsd in cd.get_zsds():
        zsd_chart_data.append({
            'points': [
                {'time': fun.datetime_to_int(zsd.start.k.date), 'price': zsd.start.val},
                {'time': fun.datetime_to_int(zsd.end.k.date), 'price': zsd.end.val},
            ],
            'linestyle': '0' if zsd.is_done() else '1',
        })
    bi_zs_chart_data = []
    for zs_type in config['zs_bi_type']:
        for zs in cd.get_bi_zss(zs_type):
            bi_zs_chart_data.append({
                'points': [
                    {'time': fun.datetime_to_int(zs.start.k.date), 'price': zs.start.val},
                    {'time': fun.datetime_to_int(zs.end.k.date), 'price': zs.end.val},
                ],
                'linestyle': '0' if zs.done else '1',
            })
    xd_zs_chart_data = []
    for zs_type in config['zs_xd_type']:
        for zs in cd.get_xd_zss(zs_type):
            xd_zs_chart_data.append({
                'points': [
                    {'time': fun.datetime_to_int(zs.start.k.date), 'price': zs.start.val},
                    {'time': fun.datetime_to_int(zs.end.k.date), 'price': zs.end.val},
                ],
                'linestyle': '0' if zs.done else '1',
            })
    zsd_zs_chart_data = []
    for zs in cd.get_zsd_zss():
        zsd_zs_chart_data.append({
            'points': [
                {'time': fun.datetime_to_int(zs.start.k.date), 'price': zs.start.val},
                {'time': fun.datetime_to_int(zs.end.k.date), 'price': zs.end.val},
            ],
            'linestyle': '0' if zs.done else '1',
        })

    # 背驰信息
    bc_infos = {}
    # 买卖点信息
    mmd_infos = {}

    lines = {
        'bi': cd.get_bis(),
        'xd': cd.get_xds(),
        'zsd': cd.get_zsds(),
    }
    line_type_map = {'bi': '笔', 'xd': '线段', 'zsd': '走势段'}
    bc_type_map = {'bi': '笔背驰', 'xd': '线段背驰', 'pz': '盘整背驰', 'qs': '趋势背驰'}
    mmd_type_map = {
        '1buy': '一买', '2buy': '二买', 'l2buy': '类二买', '3buy': '三买', 'l3buy': '类三买',
        '1sell': '一卖', '2sell': '二卖', 'l2sell': '类二卖', '3sell': '三卖', 'l3sell': '类三卖'
    }
    for line_type, ls in lines.items():
        for l in ls:
            bcs = l.line_bcs('|')
            if len(bcs) != 0 and l.end.k.date not in bc_infos.keys():
                bc_infos[l.end.k.date] = {
                    'price': l.end.val,
                    'bc_types': [],
                    'bc_texts': []
                }
            for bc in bcs:
                if bc not in bc_infos[l.end.k.date]['bc_types']:
                    bc_infos[l.end.k.date]['bc_types'].append(bc)
                    bc_infos[l.end.k.date]['bc_texts'].append(f"{line_type_map[line_type]} {bc_type_map[bc]}")

            pass
            mmds = l.line_mmds('|')
            if len(mmds) != 0 and l.end.k.date not in mmd_infos.keys():
                mmd_infos[l.end.k.date] = {
                    'price': l.end.val,
                    'mmd_types': [],
                    'mmd_texts': []
                }
            for mmd in mmds:
                if f'{line_type}_{mmd}' not in mmd_infos[l.end.k.date]['mmd_types']:
                    mmd_infos[l.end.k.date]['mmd_types'].append(f'{line_type}_{mmd}')
                    mmd_infos[l.end.k.date]['mmd_texts'].append(f"{line_type_map[line_type]} {mmd_type_map[mmd]}")

    bc_chart_data = []
    for dt, bc in bc_infos.items():
        bc_chart_data.append({
            'points': {'time': fun.datetime_to_int(dt), 'price': bc['price']},
            'text': ('/'.join(bc['bc_texts'])).strip('/')
        })
    mmd_chart_data = []
    for dt, mmd in mmd_infos.items():
        mmd_chart_data.append({
            'points': {'time': fun.datetime_to_int(dt), 'price': mmd['price']},
            'text': ('/'.join(mmd['mmd_texts'])).strip('/')
        })

    return {
        'bis': bi_chart_data,
        'xds': xd_chart_data,
        'zsds': zsd_chart_data,
        'bi_zss': bi_zs_chart_data,
        'xd_zss': xd_zs_chart_data,
        'zsd_zss': zsd_zs_chart_data,
        'bcs': bc_chart_data,
        'mmds': mmd_chart_data,
    }


def bi_td(bi: BI, cd: ICL):
    """
    判断是否笔停顿
    """
    if bi.is_done() is False:
        return False
    last_k = cd.get_klines()[-1]
    if bi.type == 'up' and last_k.c < last_k.o and last_k.c < bi.end.klines[-1].l:
        return True
    elif bi.type == 'down' and last_k.c > last_k.o and last_k.c > bi.end.klines[-1].h:
        return True

    return False
