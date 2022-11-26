from django.http import HttpResponse
from django.shortcuts import render

from chanlun import rd, stock_dl_rank, kcharts, zixuan
from chanlun.cl_utils import batch_cls, query_cl_chart_config, kcharts_frequency_h_l_map
from chanlun.exchange import get_exchange, Market
from . import utils
from .apps import login_required

'''
股票行情
'''


@login_required
def index_show(request):
    """
    股票行情首页显示
    :param request:
    :return:
    """
    zx = zixuan.ZiXuan(market_type='a')

    return render(request, 'charts/stock/index.html', {
        'nav': 'stock',
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
    jhs = rd.jhs_query('stock')
    return utils.JsonResponse(jhs)


@login_required
def plate_json(request):
    """
    查询股票的板块信息
    :param request:
    :return:
    """
    code = request.GET.get('code')
    ex = get_exchange(Market.A)
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
    ex = get_exchange(Market.A)
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

    # 如果开启并设置的该级别的低级别数据，获取低级别数据，并在转换成高级图表展示
    frequency_low, kchart_to_frequency = kcharts_frequency_h_l_map('a', frequency)
    frequency_new = frequency_low if frequency_low else frequency

    cl_chart_config = query_cl_chart_config('a', code)
    ex = get_exchange(Market.A)
    klines = ex.klines(code, frequency=frequency_new)
    cd = batch_cls(code, {frequency_new: klines}, cl_chart_config, )[0]
    stock_info = ex.stock_info(code)
    orders = rd.order_query('a', code)
    title = stock_info['code'] + ':' + stock_info['name'] + ':' + (
        f'{frequency_low}->{frequency}' if frequency_low else frequency)
    chart = kcharts.render_charts(
        title, cd, to_frequency=kchart_to_frequency, orders=orders, config=cl_chart_config)
    return HttpResponse(chart)


@login_required
def dl_ranks_show(request):
    """
    动量排行数据
    :param request:
    :return:
    """
    DRHY = stock_dl_rank.StockDLHYRank()
    hy_ranks = DRHY.query(length=3)
    DRGN = stock_dl_rank.StockDLGNRank()
    gn_ranks = DRGN.query(length=3)

    return render(request, 'charts/stock/dl_ranks.html',
                  {'nav': 'dl_ranks', 'hy_ranks': hy_ranks, 'gn_ranks': gn_ranks})


@login_required
def dl_hy_ranks_save(request):
    """
    行业动量排名增加
    :param request:
    :return:
    """
    ranks = request.body
    ranks = ranks.decode('utf-8')

    DR = stock_dl_rank.StockDLHYRank()
    DR.add_dl_rank(ranks)
    return utils.JsonResponse(True)


@login_required
def dl_gn_ranks_save(request):
    """
    概念动量排名增加
    :param request:
    :return:
    """
    ranks = request.body
    ranks = ranks.decode('utf-8')

    DR = stock_dl_rank.StockDLGNRank()
    DR.add_dl_rank(ranks)
    return utils.JsonResponse(True)
