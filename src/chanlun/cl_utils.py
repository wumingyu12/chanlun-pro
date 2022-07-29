import hashlib
import json

from chanlun import cl
from chanlun.cl_interface import *
from chanlun import rd

# 缓存计算好的缠论数据，第二次则不用重新计算了，减少计算消耗的时间
_global_cache_day = datetime.datetime.now().strftime('%Y%m%d')
_global_caches: Dict[str, ICL] = {}


def batch_cls(code, klines: Dict[str, pd.DataFrame], config: dict = None) -> List[ICL]:
    """
    批量计算并获取 缠论 数据
    :param code: 计算的标的
    :param klines: 计算的 k线 数据，每个周期对应一个 k线DataFrame，例如 ：{'30m': klines_30m, '5m': klines_5m}
    :param config: 缠论配置
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
        key = hashlib.md5(f'{code}_{f}_{config}'.encode('UTF-8')).hexdigest()
        if key in _global_caches.keys():
            # print('使用缓存')
            cls.append(_global_caches[key].process_klines(k))
        else:
            # print('重新计算')
            _global_caches[key] = cl.CL(code, f, config)
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
        'fx_qj': Config.FX_QJ_K.value,
        'fx_bh': Config.FX_BH_YES.value,
        'bi_type': Config.BI_TYPE_NEW.value,
        'bi_bzh': Config.BI_BZH_YES.value,
        'bi_qj': Config.BI_QJ_CK.value,
        'bi_fx_cgd': Config.BI_FX_CHD_NO.value,
        'xd_bzh': Config.XD_BZH_YES.value,
        'xd_qj': Config.XD_QJ_DD.value,
        'zsd_bzh': Config.ZSD_BZH_YES.value,
        'zsd_qj': Config.ZSD_QJ_DD.value,
        'zs_bi_type': [Config.ZS_TYPE_DN.value],
        'zs_xd_type': [Config.ZS_TYPE_DN.value],
        'zs_qj': Config.ZS_QJ_DD.value,
        'zs_wzgx': Config.ZS_WZGX_ZGGDD.value,
        'idx_macd_fast': 12,
        'idx_macd_slow': 26,
        'idx_macd_signal': 9,
        # 画图默认配置
        'chart_show_bi_zs': '1',
        'chart_show_xd_zs': '1',
        'chart_show_bi_mmd': '1',
        'chart_show_xd_mmd': '1',
        'chart_show_bi_bc': '1',
        'chart_show_xd_bc': '1',
        'chart_show_ma': '1',
        'chart_show_boll': '1',
        'chart_show_futu': 'macd',
        'chart_kline_nums': 1000,
        'chart_idx_ma_period': '120,250',
        'chart_idx_vol_ma_period': '5,60',
        'chart_idx_boll_period': 20,
        'chart_idx_rsi_period': 14,
        'chart_idx_atr_period': 14,
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
