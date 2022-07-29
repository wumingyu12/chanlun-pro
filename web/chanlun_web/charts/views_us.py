from django.http import HttpResponse
from django.shortcuts import render

from chanlun import rd, kcharts, zixuan
from chanlun.cl_utils import batch_cls, query_cl_chart_config
from chanlun.exchange import get_exchange, Market
from . import utils
from .apps import login_required

'''
美股行情
'''


@login_required
def index_show(request):
    """
    港股行情首页显示
    :param request:
    :return:
    """
    zx = zixuan.ZiXuan(market_type='us')

    return render(request, 'charts/us/index.html', {
        'nav': 'us',
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
    jhs = rd.jhs_query('us')
    return utils.JsonResponse(jhs)


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

    cl_chart_config = query_cl_chart_config('us', code)

    ex = get_exchange(Market.US)
    klines = ex.klines(code, frequency=frequency, end_date=None if kline_dt == '' else kline_dt)
    cd = batch_cls(code, {frequency: klines}, cl_chart_config, )[0]
    stock_info = ex.stock_info(code)
    orders = rd.order_query('us', code)
    chart = kcharts.render_charts(
        stock_info['code'] + ':' + stock_info['name'] + ':' + cd.get_frequency(),
        cd, orders=orders, config=cl_chart_config)
    return HttpResponse(chart)
