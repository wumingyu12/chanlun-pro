from chanlun.cl_utils import batch_cls
from .apps import login_required
from django.http import HttpResponse
from django.shortcuts import render

from . import utils
from chanlun import rd, cl, fun, stock_dl_rank, kcharts, zixuan
from chanlun.exchange import get_exchange, Market

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
    zx = zixuan.ZiXuan(market_type='stock')

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

    ex = get_exchange(Market.A)
    klines = ex.klines(code, frequency=frequency)
    cd = batch_cls(code, {frequency: klines}, cl_config, )[0]
    stock_info = ex.stock_info(code)
    orders = rd.stock_order_query(code)
    chart = kcharts.render_charts(
        stock_info['code'] + ':' + stock_info['name'] + ':' + cd.get_frequency(),
        cd, orders=orders, config=chart_config)
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
