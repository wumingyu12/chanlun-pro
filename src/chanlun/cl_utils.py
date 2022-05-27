import hashlib

from chanlun import cl
from chanlun.cl_interface import *

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
    for f, k in klines.items():
        key = hashlib.md5(f'{code}_{f}_{config}'.encode('UTF-8')).hexdigest()
        if key in _global_caches.keys():
            # print('使用缓存')
            cls.append(_global_caches[key].process_klines(k))
        else:
            # print('重新计算')
            _global_caches[key] = cl.CL(code, f, config)
            cls.append(_global_caches[key].process_klines(k))
    return cls
