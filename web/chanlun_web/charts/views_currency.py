from django.http import HttpResponse
from django.shortcuts import render

from chanlun import kcharts
from chanlun import rd, zixuan
from chanlun.cl_utils import batch_cls
from chanlun.exchange import get_exchange, Market
from . import utils
from .apps import login_required

'''
数字货币行情
'''


@login_required
def index_show(request):
    """
    数字货币行情首页
    :param request:
    :return:
    """
    ex = get_exchange(Market.CURRENCY)
    stocks = ex.all_stocks()
    zx = zixuan.ZiXuan(market_type='currency')
    return render(request, 'charts/currency/index.html',
                  {
                      'stocks': stocks,
                      'nav': 'currency',
                      'show_level': ['high', 'low'],
                      'zx_list': zx.zixuan_list
                  })


@login_required
def kline_show(request):
    """
    数字货币 Kline 获取
    :param request:
    :return:
    """
    code = request.POST.get('code')
    frequency = request.POST.get('frequency')
    kline_dt = request.POST.get('kline_dt')

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

    ex = get_exchange(Market.CURRENCY)
    klines = ex.klines(code, frequency=frequency, end_date=None if kline_dt == '' else kline_dt)
    cd = batch_cls(code, {frequency: klines}, cl_config, )[0]

    orders = rd.currency_order_query(code)

    chart = kcharts.render_charts(f'{code}:{cd.get_frequency()}', cd, orders=orders, config=chart_config)

    return HttpResponse(chart)


@login_required
def currency_balances(request):
    """
    查询数字货币资产
    """
    ex = get_exchange(Market.CURRENCY)
    balance = ex.balance()
    return utils.JsonResponse(balance)


@login_required
def currency_positions(request):
    """
    查询数字货币持仓
    :param request:
    :return:
    """
    ex = get_exchange(Market.CURRENCY)
    positions = ex.positions()
    return utils.JsonResponse(positions)


@login_required
def opt_records(request):
    """
    数字货币操盘列表
    :param request:
    :return:
    """
    records = rd.currency_opt_record_query(100)
    return utils.JsonResponse(records)


@login_required
def jhs_json(request):
    """
    数字货币机会列表
    :param request:
    :return:
    """
    jhs = rd.jhs_query('currency')
    return utils.JsonResponse(jhs)
