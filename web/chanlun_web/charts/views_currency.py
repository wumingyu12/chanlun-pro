import datetime

from django.http import HttpResponse
from django.shortcuts import render

from chanlun import kcharts, fun
from chanlun import rd, zixuan
from chanlun.cl_utils import web_batch_get_cl_datas, query_cl_chart_config, kcharts_frequency_h_l_map
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

    cl_chart_config = query_cl_chart_config('currency', code)
    # 如果开启并设置的该级别的低级别数据，获取低级别数据，并在转换成高级图表展示
    frequency_low, kchart_to_frequency = kcharts_frequency_h_l_map('currency', frequency)
    frequency_new = frequency_low if frequency_low else frequency

    ex = get_exchange(Market.CURRENCY)
    klines = ex.klines(code, frequency=frequency_new)
    cd = web_batch_get_cl_datas('currency', code, {frequency_new: klines}, cl_chart_config, )[0]

    orders = rd.order_query('currency', code)
    title = code + ':' + f'{frequency_low}->{frequency}' if frequency_low else frequency
    chart = kcharts.render_charts(
        title, cd, to_frequency=kchart_to_frequency, orders=orders, config=cl_chart_config
    )

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


def pos_close(request):
    """
    数字货币平仓交易
    :param request:
    :return:
    """
    ex = get_exchange(Market.CURRENCY)
    code = request.GET.get('code')
    pos = ex.positions(code)
    if len(pos) == 0:
        return utils.json_error('当前没有持仓信息')

    pos = pos[0]
    if pos['side'] == 'short':
        trade_type = 'close_short'
    else:
        trade_type = 'close_long'

    res = ex.order(code, trade_type, pos['contracts'])
    if res is False:
        return utils.json_error('手动平仓失败')

    # 记录操作记录
    rd.currency_opt_record_save(code, '手动平仓交易：交易类型 %s 平仓价格 %s 数量 %s' % (
        trade_type, res['price'], res['amount']))
    rd.order_save('currency', code, {
        'code': code,
        'name': code,
        'datetime': fun.datetime_to_str(datetime.datetime.now()),
        'type': trade_type,
        'price': res['price'],
        'amount': res['amount'],
        'info': '手动平仓'
    })

    return utils.json_response(True)


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
