from chanlun.cl_utils import batch_cls
from .apps import login_required
from django.http import HttpResponse
from django.shortcuts import render

from chanlun.exchange import get_exchange, Market
from chanlun import rd, cl, fun, kcharts, zixuan
from . import utils

'''
期货行情
'''


@login_required
def index_show(request):
    """
    期货行情首页显示
    :param request:
    :return:
    """
    ex = get_exchange(Market.FUTURES)
    codes = ex.all_stocks()
    zx = zixuan.ZiXuan(market_type='futures')
    return render(request, 'charts/futures/index.html',
                  {'codes': codes,
                   'nav': 'futures',
                   'show_level': ['high', 'low'],
                   'zx_list': zx.zixuan_list})


@login_required
def kline_show(request):
    """
    期货 Kline 线获取
    :param request:
    :return:
    """
    code = request.POST.get('code')
    frequency = request.POST.get('frequency')

    # 缠论配置设置
    cl_config_key = ['fx_qj', 'fx_bh', 'bi_type', 'bi_qj', 'bi_bzh', 'bi_fx_cgd', 'xd_bzh', 'xd_qj', 'zsd_bzh',
                     'zsd_qj', 'zs_bi_type',
                     'zs_xd_type', 'zs_qj', 'zs_wzgx', 'idx_macd_fast', 'idx_macd_slow', 'idx_macd_signal',
                     ]
    cl_config = {_k: request.POST.get(_k) for _k in cl_config_key}
    # 图表显示设置
    chart_bool_keys = ['show_bi_zs', 'show_xd_zs', 'show_bi_mmd', 'show_xd_mmd', 'show_bi_bc', 'show_xd_bc', 'show_ma',
                       'show_boll', 'idx_boll_period', 'idx_ma_period']
    chart_config = {_k: request.POST.get(_k, '1') for _k in chart_bool_keys}

    ex = get_exchange(Market.FUTURES)
    klines = ex.klines(code, frequency=frequency)
    cd = batch_cls(code, {frequency: klines}, cl_config, )[0]
    stock_info = ex.stock_info(code)
    orders = rd.order_query('futures', code)
    chart = kcharts.render_charts(
        stock_info['code'] + ':' + stock_info['name'] + ':' + cd.get_frequency(),
        cd, orders=orders, config=chart_config)
    return HttpResponse(chart)


@login_required
def jhs_json(request):
    """
    期货机会列表
    :param request:
    :return:
    """
    jhs = rd.jhs_query('futures')
    return utils.JsonResponse(jhs)
