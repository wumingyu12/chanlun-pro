from django.http import HttpResponse
from django.shortcuts import render

from chanlun.backtesting.backtest_klines import BackTestKlines
from chanlun import kcharts
from .apps import login_required

bk_hq: BackTestKlines


@login_required
def index_show(request):
    """
    回放行情
    :param request:
    :return:
    """
    global bk_hq
    bk_hq = None

    return render(request, 'charts/back/index.html', {'nav': 'back'})


@login_required
def kline_show(request):
    """
    回放 K线
    :param request:
    :return:
    """
    global bk_hq
    market = request.POST.get('market')
    code = request.POST.get('code')
    start = request.POST.get('start')
    end = request.POST.get('end')
    frequencys: str = request.POST.get('frequencys')

    # 缠论配置设置
    cl_config_key = ['fx_qj', 'fx_bh', 'bi_type', 'bi_bzh', 'bi_fx_cgd', 'bi_qj', 'xd_bzh', 'xd_qj', 'zslx_bzh',
                     'zslx_qj', 'zs_bi_type',
                     'zs_xd_type', 'zs_qj', 'zs_wzgx']
    cl_config = {_k: request.POST.get(_k) for _k in cl_config_key}
    if bk_hq is None:
        bk_hq = BackTestKlines(market, start, end, frequencys.split(','), cl_config=cl_config)
        bk_hq.init(code, frequencys[0])

    is_next = bk_hq.next()
    if not is_next:
        return HttpResponse('')

    charts = '{'
    for f in bk_hq.frequencys:
        cd = bk_hq.get_cl_data(code, f)
        c = kcharts.render_charts(f'{code}:{f}', cd)
        charts += '"' + cd.get_frequency() + '" : ' + c + ','
    charts += '}'

    return HttpResponse(charts)
