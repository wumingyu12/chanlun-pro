from django.http import HttpResponse
from django.shortcuts import render

from chanlun import rd, kcharts, zixuan
from chanlun.cl_utils import batch_cls, kcharts_frequency_h_l_map
from chanlun.cl_utils import query_cl_chart_config
from chanlun.exchange import get_exchange, Market
from . import utils
from .apps import login_required

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

    cl_chart_config = query_cl_chart_config('futures', code)
    # 如果开启并设置的该级别的低级别数据，获取低级别数据，并在转换成高级图表展示
    frequency_low, kchart_to_frequency = kcharts_frequency_h_l_map('futures', frequency)
    frequency_new = frequency_low if frequency_low else frequency

    ex = get_exchange(Market.FUTURES)
    klines = ex.klines(code, frequency=frequency_new)
    cd = batch_cls(code, {frequency_new: klines}, cl_chart_config, )[0]
    stock_info = ex.stock_info(code)
    orders = rd.order_query('futures', code)
    title = stock_info['code'] + ':' + stock_info['name'] + ':' + (
        f'{frequency_low}->{frequency}' if frequency_low else frequency)
    chart = kcharts.render_charts(
        title, cd, to_frequency=kchart_to_frequency, orders=orders, config=cl_chart_config)
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
