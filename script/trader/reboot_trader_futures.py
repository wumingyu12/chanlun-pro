import pickle
import time
import traceback

from chanlun.cl_interface import Config
from chanlun.exchange.exchange_tq import ExchangeTq
from chanlun import rd, fun, zixuan
from chanlun.backtesting.base import CLDatas
from chanlun.strategy import strategy_demo
from chanlun.trader.trader_futures import TraderFutures

logger = fun.get_logger('./logs/trader_futures.log')

logger.info('期货自动化交易程序')

try:
    zx = zixuan.ZiXuan('futures')
    ex = ExchangeTq(use_simulate_account=True)

    p_redis_key = 'trader_futures'

    # 设置使用的策略
    STR = strategy_demo.StrategyDemo()

    # 从 Redis 中恢复交易对象
    p_bytes = rd.get_byte(p_redis_key)
    if p_bytes is not None:
        TR = pickle.loads(p_bytes)
    else:
        TR = TraderFutures(
            'futures', is_stock=False, is_futures=True, log=logger.info, mmds=None
        )

    # 单独设置一些参数，更新之前缓存的参数
    TR.set_strategy(STR)
    # TR.allow_mmds = ['1buy', '2buy', '3buy', '1sell', '2sell', '3sell']
    TR.is_test = False

    # 执行的 标的与周期 设置
    frequencys = ['10s']

    cl_config = {
        # 分型默认配置
        'fx_qj': Config.FX_QJ_K.value,
        'fx_bh': Config.FX_BH_YES.value,
        # 笔默认配置
        'bi_type': Config.BI_TYPE_NEW.value,
        'bi_bzh': Config.BI_BZH_YES.value,
        'bi_fx_cgd': Config.BI_FX_CHD_NO.value,
        'bi_qj': Config.BI_QJ_DD.value,
        # 线段默认配置
        'xd_bzh': Config.XD_BZH_NO.value,
        'xd_qj': Config.XD_QJ_DD.value,
        # 走势类型默认配置
        'zslx_bzh': Config.ZSLX_BZH_NO.value,
        'zslx_qj': Config.ZSLX_QJ_DD.value,
        # 中枢默认配置
        'zs_bi_type': Config.ZS_TYPE_DN.value,  # 笔中枢类型
        'zs_xd_type': Config.ZS_TYPE_DN.value,  # 走势中枢类型
        'zs_qj': Config.ZS_QJ_CK.value,
        'zs_wzgx': Config.ZS_WZGX_ZGD.value,
    }

    while True:
        try:
            seconds = int(time.time())

            # 每 5 分钟执行一次
            if seconds % (10) != 0:
                time.sleep(1)
                continue

            if ex.now_trading() is False:
                continue

            # 增加当前持仓中的交易对儿
            stocks = zx.zx_stocks('我的持仓')
            run_codes = [_s['code'] for _s in stocks]
            run_codes = TR.position_codes() + run_codes
            run_codes = list(set(run_codes))

            # print('Run Codes %s' % run_codes)

            for code in run_codes:
                try:
                    # logger.info('Run %s' % code)
                    # 每次重新创建对象
                    cldatas = CLDatas(code, frequencys, ex, cl_config)

                    TR.run(code, cldatas)
                except Exception as e:
                    logger.error(traceback.format_exc())

            # 保存对象到 Redis 中
            p_obj = pickle.dumps(TR)
            rd.save_byte(p_redis_key, p_obj)

        except Exception as e:
            logger.error(traceback.format_exc())

except Exception as e:
    logger.error(traceback.format_exc())
finally:
    logger.info('Done')
