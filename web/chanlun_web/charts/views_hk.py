from .apps import login_required
from django.http import HttpResponse
from django.shortcuts import render

from chanlun.exchange import get_exchange, Market
from chanlun import rd, cl, fun, kcharts, zixuan
from . import utils

'''
港股行情
'''


@login_required
def index_show(request):
    """
    港股行情首页显示
    :param request:
    :return:
    """
    zx = zixuan.ZiXuan(market_type='hk')

    return render(request, 'charts/hk/index.html', {
        'nav': 'hk',
        'show_level': ['high', 'low'],
        'zx_list': zx.zixuan_list
    })


@login_required
def jhs_json(request):
    """
    股票机会列表
    :param request:
    :return:
    """
    jhs = rd.jhs_query('hk')
    return utils.JsonResponse(jhs)


@login_required
def plate_json(request):
    """
    查询股票的板块信息
    :param request:
    :return:
    """
    code = request.GET.get('code')
    ex = get_exchange(Market.HK)
    plates = ex.stock_owner_plate(code)
    return utils.JsonResponse(plates)


@login_required
def plate_stocks_json(request):
    """
    查询板块中的股票信息
    :param request:
    :return:
    """
    code = request.GET.get('code')
    ex = get_exchange(Market.HK)
    stocks = ex.plate_stocks(code)
    return utils.JsonResponse(stocks)


@login_required
def kline_chart(request):
    """
    股票 Kline 线获取
    :param request:
    :return:
    """
    code = request.POST.get('code')
    frequency = request.POST.get('frequency')
    kline_dt = request.POST.get('kline_dt')

    # 缠论配置设置
    cl_config_key = ['fx_qj', 'fx_bh', 'bi_type', 'bi_qj', 'bi_bzh', 'bi_fx_cgd', 'xd_bzh', 'xd_qj', 'zslx_bzh',
                     'zslx_qj', 'zs_bi_type',
                     'zs_xd_type', 'zs_qj', 'zs_wzgx', 'idx_macd_fast', 'idx_macd_slow', 'idx_macd_signal',
                     'idx_boll_period', 'idx_ma_period']
    cl_config = {_k: request.POST.get(_k) for _k in cl_config_key}
    # 图表显示设置
    chart_bool_keys = ['show_bi_zs', 'show_xd_zs', 'show_bi_mmd', 'show_xd_mmd', 'show_bi_bc', 'show_xd_bc', 'show_ma',
                       'show_boll']
    chart_config = {_k: bool(int(request.POST.get(_k, '1'))) for _k in chart_bool_keys}

    ex = get_exchange(Market.HK)
    klines = ex.klines(code, frequency=frequency, end_date=None if kline_dt == '' else kline_dt)
    cd = cl.CL(code, frequency, cl_config).process_klines(klines)
    stock_info = ex.stock_info(code)
    orders = rd.stock_order_query(code)
    chart = kcharts.render_charts(
        stock_info['code'] + ':' + stock_info['name'] + ':' + cd.frequency,
        cd, orders=orders, config=chart_config)
    return HttpResponse(chart)
