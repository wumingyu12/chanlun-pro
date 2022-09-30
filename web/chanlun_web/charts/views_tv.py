import datetime

from django.shortcuts import render

from chanlun.cl_utils import batch_cls, query_cl_chart_config, cl_date_to_tv_chart
from .apps import login_required
from .utils import *
from chanlun.exchange import *
from chanlun import fun

'''
TradingView 行情图表
'''

# 项目中的周期与 tv 的周期对应表
frequency_maps = {
    '10s': '10S', '30s': '30S',
    '1m': '1', '5m': '5', '10m': '10', '15m': '15', '30m': '30', '60m': '60', '120m': '120',
    '2h': '120', '4h': '240',
    'd': '1D', '2d': '2D',
    'w': '1W', 'm': '1M', 'y': '12M'
}

resolution_maps = dict(zip(frequency_maps.values(), frequency_maps.keys()))

# 各个市场支持的时间周期
market_frequencys = {
    'a': ['y', 'm', 'w', 'd', '120m', '60m', '30m', '15m', '5m', '1m'],
    'hk': ['y', 'm', 'w', 'd', '120m', '60m', '30m', '15m', '10m', '5m', '1m'],
    'us': ['y', 'm', 'w', 'd', '120m', '60m', '30m', '15m', '5m', '1m'],
    'futures': ['w', 'd', '60m', '30m', '15m', '10m', '6m', '5m', '1m', '30s', '10s'],
    'currency': ['w', 'd', '4h', '60m', '30m', '15m', '10m', '5m', '1m'],
}

# 各个市场的交易时间
market_session = {
    'a': '0930-1130,1300-1500',
    'hk': '0930-1230,1430-1600',
    'us': '0930-1600',
    'futures': '0900-1015,1030-1130,1330-1500,2100-2300',
    'currency': '24x7',
}

# 各个交易所的时区
market_timezone = {
    'a': 'Asia/Shanghai',
    'hk': 'Asia/Hong_Kong',
    'us': 'America/New_York',
    'futures': 'Asia/Shanghai',
    'currency': 'Asia/Shanghai',
}


@login_required
def index_show(request):
    """
    TV 行情首页
    :param request:
    :return:
    """

    return render(request, 'charts/tv/index.html', {

    })


@login_required
def config(request):
    """
    配置项
    """
    frequencys = list(set(market_frequencys['a']) & set(market_frequencys['hk']) & set(market_frequencys['us']) & set(
        market_frequencys['futures']) & set(market_frequencys['currency']))
    supportedResolutions = [v for k, v in frequency_maps.items() if k in frequencys]
    return response_as_json({
        'supports_search': True,
        'supports_group_request': False,
        'supported_resolutions': supportedResolutions,
        'supports_marks': False,
        'supports_timescale_marks': False,
        'supports_time': False,
        'exchanges': [
            {'value': "a", 'name': "沪深", 'desc': "沪深A股"},
            {'value': "hk", 'name': "港股", 'desc': "港股"},
            {'value': "us", 'name': "美股", 'desc': "美股"},
            {'value': "futures", 'name': "期货", 'desc': "期货"},
            {'value': "currency", 'name': "数字货币", 'desc': "数字货币"},
        ],
    })


@login_required
def symbol_info(request):
    """
    商品集合信息
    supports_search is True 则不会调用这个接口
    """
    group = request.GET.get('group')
    ex = get_exchange(Market(group))
    all_symbols = ex.all_stocks()

    info = {
        'symbol': [s['code'] for s in all_symbols],
        'description': [s['name'] for s in all_symbols],
        'exchange-listed': group,
        'exchange-traded': group,
    }
    return response_as_json(info)


@login_required
def symbols(request):
    """
    商品解析
    """
    symbol: str = request.GET.get('symbol')
    symbol: list = symbol.split(':')
    market = symbol[0]
    code = symbol[1]

    ex = get_exchange(Market(market))
    stocks = ex.stock_info(code)

    info = {
        # "symbol": stocks['code'],
        "full_name": f'{market}:{stocks["code"]}',
        "description": stocks['name'],
        "exchange": market,
        "ticker": f'{market}:{stocks["code"]}',
        "type": '',
        'session': market_session[market],
        'timezone': market_timezone[market],
        'supported_resolutions': [v for k, v in frequency_maps.items() if k in market_frequencys[market]],
        'has_intraday': True,
        'has_seconds': True if market == 'futures' else False,
        'has_daily': True,
        'has_weekly_and_monthly': True,
    }
    return response_as_json(info)


@login_required
def search(request):
    """
    商品检索
    """
    query = request.GET.get('query')
    type = request.GET.get('type')
    exchange = request.GET.get('exchange')
    limit = request.GET.get('limit')

    ex = get_exchange(Market(exchange))
    all_stocks = ex.all_stocks()

    res_stocks = [
        stock for stock in all_stocks
        if query.lower() in stock['code'].lower() or query.lower() in stock['name'].lower()
    ]
    res_stocks = res_stocks[0:int(limit)]

    infos = []
    for stock in res_stocks:
        infos.append({
            "symbol": stock['code'],
            "full_name": f'{exchange}:{stock["code"]}',
            "description": stock['name'],
            "exchange": exchange,
            "ticker": f'{exchange}:{stock["code"]}',
            "type": type,
            'session': market_session[exchange],
            'timezone': market_timezone[exchange],
            'supported_resolutions': [v for k, v in frequency_maps.items() if k in market_frequencys[exchange]],
        })
    return response_as_json(infos)


@login_required
def history(request):
    """
    K线柱
    """
    symbol = request.GET.get('symbol')
    _from = request.GET.get('from')
    _to = request.GET.get('to')
    resolution = request.GET.get('resolution')
    countback = request.GET.get('countback')

    # 没有过去的数据，如果请求的话，返回 no_data
    now_time = fun.datetime_to_int(datetime.datetime.now()) - 10
    if now_time > int(_to):
        return response_as_json({'s': 'no_data', 'errmsg': '不支持历史数据加载', 'nextTime': now_time + 9999 * 10000})

    market = symbol.split(':')[0]
    code = symbol.split(':')[1]

    ex = get_exchange(Market(market))
    frequency = resolution_maps[resolution]
    klines = ex.klines(code, frequency)

    cl_chart_config = query_cl_chart_config(market, code)
    cd = batch_cls(code, {resolution: klines}, cl_chart_config, )[0]

    # 将缠论数据，转换成 tv 画图的坐标数据
    cl_chart_data = cl_date_to_tv_chart(cd, cl_chart_config)

    info = {
        's': 'ok',
        't': [fun.datetime_to_int(k.date) for k in cd.get_klines()],
        'c': [k.c for k in cd.get_klines()],
        'o': [k.o for k in cd.get_klines()],
        'h': [k.h for k in cd.get_klines()],
        'l': [k.l for k in cd.get_klines()],
        'v': [k.a for k in cd.get_klines()],
        'bis': cl_chart_data['bis'],
        'xds': cl_chart_data['xds'],
        'zsds': cl_chart_data['zsds'],
        'bi_zss': cl_chart_data['bi_zss'],
        'xd_zss': cl_chart_data['xd_zss'],
        'zsd_zss': cl_chart_data['zsd_zss'],
        'bcs': cl_chart_data['bcs'],
        'mmds': cl_chart_data['mmds'],
    }
    return response_as_json(info)


@login_required
def time(request):
    """
    服务器时间
    """
    return HttpResponse(fun.datetime_to_int(datetime.datetime.now()))
