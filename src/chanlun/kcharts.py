import os

import talib
import MyTT
# 画图配置
from pyecharts import options as opts
from pyecharts.charts import Kline as cKline, Line, Bar, Grid, Scatter
from pyecharts.commons.utils import JsCode

from chanlun.cl_interface import *
from chanlun.fun import str_to_datetime
from chanlun.cl_utils import cl_qstd

if "JPY_PARENT_PID" in os.environ:
    from pyecharts.globals import CurrentConfig, NotebookType

    CurrentConfig.NOTEBOOK_TYPE = NotebookType.JUPYTER_LAB
    cKline().load_javascript()
    Line().load_javascript()
    Bar().load_javascript()
    Grid().load_javascript()
    Scatter().load_javascript()


def render_charts(title, cl_data: ICL, orders=None, config=None):
    """
    缠论数据图表化展示
    :param title:
    :param cl_data:
    :param orders:
    :param config: 画图配置
    :return:
    """

    if orders is None:
        orders = []
    if config is None:
        config = {}

    default_config = {
        # 展示配置项
        'chart_show_bi_zs': True,
        'chart_show_xd_zs': True,
        'chart_show_zsd_zs': True,
        'chart_show_bi_mmd': True,
        'chart_show_xd_mmd': True,
        'chart_show_zsd_mmd': True,
        'chart_show_bi_bc': True,
        'chart_show_xd_bc': True,
        'chart_show_zsd_bc': True,
        'chart_show_ma': True,
        'chart_show_boll': False,
        'chart_show_futu': 'macd',
        # 指标配置项
        'chart_kline_nums': 1000,
        'chart_idx_ma_period': '120,250',
        'chart_idx_vol_ma_period': '5,60',
        'chart_idx_boll_period': 20,
        'chart_idx_rsi_period': 14,
        'chart_idx_atr_period': 14,
        'chart_idx_cci_period': 14,
        'chart_idx_kdj_period': '9,3,3',
        'chart_qstd': 'xd,0',
        # 图表高度
        'chart_high': 800,
    }

    # 配置项整理
    for _k, _v in default_config.items():
        if _k not in config.keys():
            config[_k] = _v
        else:
            try:
                if _k in [
                    'chart_idx_ma_period', 'chart_idx_vol_ma_period',
                    'chart_idx_kdj_period', 'chart_show_futu',
                    'chart_qstd'
                ]:
                    config[_k] = str(config[_k])
                elif 'chart_show_' in _k:
                    config[_k] = bool(int(config[_k]))
                elif 'chart_idx_' in _k or 'chart_kline_nums' in _k:
                    config[_k] = int(config[_k])
            except Exception as e:
                print(f'{_k} val error {config[_k]}')
                config[_k] = _v

    # 颜色配置
    color_k_up = '#FD1050'
    color_k_down = '#0CF49B'
    color_bi = '#FDDD60'
    color_bi_zs = '#FFFFFF'
    color_bi_zs_up = '#FFFFFF'  # '#993333'
    color_bi_zs_down = '#FFFFFF'  # '#99CC99'

    color_xd = '#FFA710'
    color_xd_zs = '#e9967a'
    color_xd_zs_up = '#e9967a'  # '#CC0033'
    color_xd_zs_down = '#e9967a'  # '#66CC99'

    color_zsd = '#A1C0FC'
    color_zsd_zs = '#00BFFF'

    color_last_bi_zs = 'RGB(144,238,144,0.5)'
    color_last_xd_zs = 'RGB(255,182,193,0.5)'

    color_qstd_up = 'RGB(255,127,80,0.7)'
    color_qstd_down = 'RGB(100,149,237,0.7)'

    brush_opts = opts.BrushOpts(tool_box=["rect", "polygon", "lineX", "lineY", "keep", "clear"],
                                x_axis_index="all", brush_link="all",
                                out_of_brush={"colorAlpha": 0.1}, brush_type="lineX")

    klines = cl_data.get_klines()
    cl_klines = cl_data.get_cl_klines()
    fxs = cl_data.get_fxs()
    bis = cl_data.get_bis()
    xds = cl_data.get_xds()
    zsds = cl_data.get_zsds()
    zsd_zss = cl_data.get_zsd_zss()
    last_bi_zs = cl_data.get_last_bi_zs()
    last_xd_zs = cl_data.get_last_xd_zs()

    idx = cl_data.get_idx()

    range_start = 0
    if len(klines) > config['chart_kline_nums']:
        range_start = 100 - (config['chart_kline_nums'] / len(klines)) * 100

    # 重新整理Kline数据
    klines_yaxis = []
    klines_xaxis = []
    klines_vols = []

    cl_klines_yaxis = []
    cl_klines_xaxis = []

    for k in klines:
        klines_xaxis.append(k.date)
        # 开/收/低/高
        klines_yaxis.append([k.o, k.c, k.l, k.h])
        klines_vols.append(k.a)

    label_not_show_opts = opts.LabelOpts(is_show=False)
    red_item_style = opts.ItemStyleOpts(color=color_k_up, opacity=0.5)
    green_item_style = opts.ItemStyleOpts(color=color_k_down, opacity=0.5)
    vol = []
    for row in klines:
        item_style = red_item_style if row.c > row.o else green_item_style
        bar = opts.BarItem(name='', value=row.a, itemstyle_opts=item_style, label_opts=label_not_show_opts)
        vol.append(bar)

    for clk in cl_klines:
        cl_klines_xaxis.append(clk.date)
        # 开/收/低/高
        cl_klines_yaxis.append([clk.l, clk.h, clk.l, clk.h])

    # 找到顶和底的坐标
    point_ding = {'index': [], 'val': []}
    point_di = {'index': [], 'val': []}
    for fx in fxs:
        if fx.ld() < 5:
            continue
        if fx.type == 'ding':
            point_ding['index'].append(fx.k.date)
            point_ding['val'].append([fx.val, '强分型' if fx.ld() >= 5 else ''])
        else:
            point_di['index'].append(fx.k.date)
            point_di['val'].append([fx.val, '强分型' if fx.ld() >= 5 else ''])

    # 画 笔
    line_bis = {'index': [], 'val': []}
    line_xu_bis = {'index': [], 'val': []}
    bis_done = [_bi for _bi in bis if _bi.is_done()]
    bis_no_done = [_bi for _bi in bis if _bi.is_done() is False]
    if len(bis_done) > 0:
        line_bis['index'].append(bis_done[0].start.k.date)
        line_bis['val'].append(bis_done[0].start.val)
    for b in bis_done:
        line_bis['index'].append(b.end.k.date)
        line_bis['val'].append(b.end.val)
    if len(bis_no_done) > 0:
        line_xu_bis['index'].append(bis_no_done[0].start.k.date)
        line_xu_bis['val'].append(bis_no_done[0].start.val)
    for b in bis_no_done:
        line_xu_bis['index'].append(b.end.k.date)
        line_xu_bis['val'].append(b.end.val)

    # 画 线段
    line_xds = {'index': [], 'val': []}
    line_xu_xds = {'index': [], 'val': []}
    xds_done = [_xd for _xd in xds if _xd.is_done()]
    xds_no_done = [_xd for _xd in xds if _xd.is_done() is False]
    if len(xds_done) > 0:
        line_xds['index'].append(xds_done[0].start.k.date)
        line_xds['val'].append(xds_done[0].start.val)
    for x in xds_done:
        line_xds['index'].append(x.end.k.date)
        line_xds['val'].append(x.end.val)
    if len(xds_no_done) > 0:
        line_xu_xds['index'].append(xds_no_done[0].start.k.date)
        line_xu_xds['val'].append(xds_no_done[0].start.val)
    for x in xds_no_done:
        line_xu_xds['index'].append(x.end.k.date)
        line_xu_xds['val'].append(x.end.val)

    # 画 走势段
    line_zsds = {'index': [], 'val': []}
    line_xu_zsds = {'index': [], 'val': []}
    zsds_done = [_qs for _qs in zsds if _qs.is_done()]
    zsds_no_done = [_qs for _qs in zsds if _qs.is_done() is False]
    if len(zsds_done) > 0:
        line_zsds['index'].append(zsds_done[0].start.k.date)
        line_zsds['val'].append(zsds_done[0].start.val)
    for x in zsds_done:
        line_zsds['index'].append(x.end.k.date)
        line_zsds['val'].append(x.end.val)
    if len(zsds_no_done) > 0:
        line_xu_zsds['index'].append(zsds_no_done[0].start.k.date)
        line_xu_zsds['val'].append(zsds_no_done[0].start.val)
    for x in zsds_no_done:
        line_xu_zsds['index'].append(x.end.k.date)
        line_xu_zsds['val'].append(x.end.val)

    # 画 笔 中枢 (遍历所有计算的中枢类型)
    line_bi_zss = []
    for zs_type in cl_data.get_config()['zs_bi_type']:
        bi_zss = cl_data.get_bi_zss(zs_type)
        for zs in bi_zss:
            if config['chart_show_bi_zs'] is False:
                break
            if zs.real is False:
                continue
            start_index = zs.start.k.date
            end_index = zs.end.k.date
            l_zs = [
                # 两竖，两横，5个点，转一圈
                [start_index, start_index, end_index, end_index, start_index],
                [zs.zg, zs.zd, zs.zd, zs.zg, zs.zg],
            ]
            if zs.type == 'up':
                l_zs.append(color_bi_zs_up)
            elif zs.type == 'down':
                l_zs.append(color_bi_zs_down)
            else:
                l_zs.append(color_bi_zs)

            l_zs.append(zs.level + 1)
            l_zs.append(zs.done)

            line_bi_zss.append(l_zs)

    # 画 线段 中枢
    line_zs_zss = []
    for zs_type in cl_data.get_config()['zs_xd_type']:
        xd_zss = cl_data.get_xd_zss(zs_type)
        for zs in xd_zss:
            if config['chart_show_xd_zs'] is False:
                break
            if zs.real is False:
                continue
            start_index = zs.start.k.date
            end_index = zs.end.k.date
            l_zs = [
                # 两竖，两横，5个点，转一圈
                [start_index, start_index, end_index, end_index, start_index],
                [zs.zg, zs.zd, zs.zd, zs.zg, zs.zg],
            ]
            if zs.type == 'up':
                l_zs.append(color_xd_zs_up)
            elif zs.type == 'down':
                l_zs.append(color_xd_zs_down)
            else:
                l_zs.append(color_xd_zs)

            l_zs.append(zs.level + 1)
            l_zs.append(zs.done)

            line_zs_zss.append(l_zs)

    # 画 走势段 中枢
    line_zsd_zss = []
    for zs in zsd_zss:
        if config['chart_show_zsd_zs'] is False:
            break
        if zs.real is False:
            continue
        start_index = zs.start.k.date
        end_index = zs.end.k.date
        l_zs = [
            # 两竖，两横，5个点，转一圈
            [start_index, start_index, end_index, end_index, start_index],
            [zs.zg, zs.zd, zs.zd, zs.zg, zs.zg],
        ]
        if zs.type == 'up':
            l_zs.append(color_zsd_zs)
        elif zs.type == 'down':
            l_zs.append(color_zsd_zs)
        else:
            l_zs.append(color_zsd_zs)

        l_zs.append(zs.level + 1)
        l_zs.append(zs.done)

        line_zsd_zss.append(l_zs)

    # 画最后一笔中枢
    line_last_bi_zs = []
    if last_bi_zs is not None:
        start_index = last_bi_zs.start.k.date
        end_index = last_bi_zs.end.k.date
        line_last_bi_zs = [
            [start_index, start_index, end_index, end_index, start_index],
            [last_bi_zs.zg, last_bi_zs.zd, last_bi_zs.zd, last_bi_zs.zg, last_bi_zs.zg],
            color_last_bi_zs,
            last_bi_zs.level + 1,
            last_bi_zs.done
        ]
    # 画最后一线段中枢
    line_last_xd_zs = []
    if last_xd_zs is not None:
        start_index = last_xd_zs.start.k.date
        end_index = last_xd_zs.end.k.date
        line_last_xd_zs = [
            [start_index, start_index, end_index, end_index, start_index],
            [last_xd_zs.zg, last_xd_zs.zd, last_xd_zs.zd, last_xd_zs.zg, last_xd_zs.zg],
            color_last_xd_zs,
            last_xd_zs.level + 1,
            last_xd_zs.done
        ]

    # 分型中的 背驰 和 买卖点信息，归类，一起显示
    fx_bcs_mmds = {}
    for _bi in bis:
        _fx = _bi.end
        if _fx.index not in fx_bcs_mmds.keys():
            fx_bcs_mmds[_fx.index] = {'fx': _fx, 'bcs': [], 'mmds': []}
        for zs_type in cl_data.get_config()['zs_bi_type']:
            for _bc in _bi.get_bcs(zs_type):
                if config['chart_show_bi_bc'] is False:
                    break
                if _bc.bc:
                    fx_bcs_mmds[_fx.index]['bcs'].append(_bc)
            for _mmd in _bi.get_mmds(zs_type):
                if config['chart_show_bi_mmd'] is False:
                    break
                fx_bcs_mmds[_fx.index]['mmds'].append(_mmd)
    for _xd in xds:
        _fx = _xd.end
        if _fx.index not in fx_bcs_mmds.keys():
            fx_bcs_mmds[_fx.index] = {'fx': _fx, 'bcs': [], 'mmds': []}
        for zs_type in cl_data.get_config()['zs_xd_type']:
            for _bc in _xd.get_bcs(zs_type):
                if config['chart_show_xd_bc'] is False:
                    break
                if _bc.bc:
                    fx_bcs_mmds[_fx.index]['bcs'].append(_bc)
            for _mmd in _xd.get_mmds(zs_type):
                if config['chart_show_xd_mmd'] is False:
                    break
                fx_bcs_mmds[_fx.index]['mmds'].append(_mmd)
    for _zsd in zsds:
        _fx = _zsd.end
        if _fx.index not in fx_bcs_mmds.keys():
            fx_bcs_mmds[_fx.index] = {'fx': _fx, 'bcs': [], 'mmds': []}
        for _bc in _zsd.bcs:
            if config['chart_show_zsd_bc'] is False:
                break
            if _bc.bc:
                fx_bcs_mmds[_fx.index]['bcs'].append(_bc)
        for _mmd in _zsd.mmds:
            if config['chart_show_zsd_mmd'] is False:
                break
            fx_bcs_mmds[_fx.index]['mmds'].append(_mmd)

    # 画 背驰
    scatter_bc = {'i': [], 'val': []}  # 背驰
    bc_maps = {'bi': '笔背驰', 'xd': '线段背驰', 'zsd': '走势段背驰', 'pz': '盘整背驰', 'qs': '趋势背驰'}
    zs_type_maps = {'bi': '笔', 'xd': '线段', 'zsd': '走势'}
    for fx_index in fx_bcs_mmds.keys():
        fx_bc_info = fx_bcs_mmds[fx_index]
        bc_label = ''
        fx = fx_bc_info['fx']
        for bc in fx_bc_info['bcs']:
            # 避免信息混乱，只显示同类型的一个
            if bc_maps[bc.type] not in bc_label:
                if bc.zs is not None:
                    bc_label += zs_type_maps[bc.zs.zs_type] + ':'
                bc_label += bc_maps[bc.type] + ' '
                # if bc.zs is not None:
                #     bc_label += ' ZS[%s (%.2f - %.2f)]' % (bc.zs.type, bc.zs.zg, bc.zs.zd)
                bc_label += ' /'

        if bc_label != '':
            scatter_bc['i'].append(fx.k.date)
            scatter_bc['val'].append([fx.val, bc_label.strip('/')])

    # 画买卖点
    mmd_maps = {'1buy': '一买', '2buy': '二买', 'l2buy': '类二买', '3buy': '三买', 'l3buy': '类三买',
                '1sell': '一卖', '2sell': '二卖', 'l2sell': '类二卖', '3sell': '三卖', 'l3sell': '类三卖'}
    scatter_buy = {'i': [], 'val': []}
    scatter_sell = {'i': [], 'val': []}
    for fx_index in fx_bcs_mmds.keys():
        fx = fx_bcs_mmds[fx_index]['fx']
        mmds = fx_bcs_mmds[fx_index]['mmds']
        if len(mmds) == 0:
            continue
        buy_label = ''
        sell_label = ''
        for mmd in mmds:
            # 避免信息混乱，只显示同类型的一个
            if mmd_maps[mmd.name] not in buy_label:
                if mmd.name in ['1buy', '2buy', '3buy', 'l2buy', 'l3buy']:
                    buy_label += '%s %s /' % (zs_type_maps[mmd.zs.zs_type], mmd_maps[mmd.name])
            if mmd_maps[mmd.name] not in sell_label:
                if mmd.name in ['1sell', '2sell', '3sell', 'l2sell', 'l3sell']:
                    sell_label += '%s %s /' % (zs_type_maps[mmd.zs.zs_type], mmd_maps[mmd.name])

        if buy_label != '':
            scatter_buy['i'].append(fx.k.date)
            scatter_buy['val'].append([fx.val, buy_label.strip('/')])
        if sell_label != '':
            scatter_sell['i'].append(fx.k.date)
            scatter_sell['val'].append([fx.val, sell_label.strip('/')])

    # 画订单记录
    scatter_buy_orders = {'i': [], 'val': []}
    scatter_sell_orders = {'i': [], 'val': []}
    # 　order type 允许的值：buy 买入 sell 卖出  open_long 开多  close_long 平多 open_short 开空 close_short 平空
    order_type_maps = {
        'buy': '买入', 'sell': '卖出',
        'open_long': '买入开多', 'open_short': '买入开空', 'close_long': '卖出平多', 'close_short': '买入平空'
    }
    if orders:
        # 处理订单时间坐标
        dts = pd.Series(klines_xaxis)
        for o in orders:
            if type(o['datetime']) == 'str':
                odt = str_to_datetime(o['datetime'])
            else:
                odt = o['datetime']
            k_dt = dts[dts <= odt]
            if len(k_dt) == 0:
                continue
            if o['type'] in ['buy', 'open_long', 'close_short']:
                scatter_buy_orders['i'].append(k_dt.iloc[-1])
                scatter_buy_orders['val'].append([o['price'],
                                                  f"{order_type_maps[o['type']]}[{o['price']}/{o['amount']}]:{'' if 'info' not in o else o['info']}"])
            elif o['type'] in ['sell', 'close_long', 'open_short']:
                scatter_sell_orders['i'].append(k_dt.iloc[-1])
                scatter_sell_orders['val'].append([o['price'],
                                                   f"{order_type_maps[o['type']]}[{o['price']}/{o['amount']}]:{'' if 'info' not in o else o['info']}"])

    # 滑动区块设置
    datazoom_opts = [
        opts.DataZoomOpts(
            is_show=False, type_="inside", xaxis_index=[0, 0], range_start=range_start, range_end=100
        ),
        opts.DataZoomOpts(
            is_show=True, xaxis_index=[0, 1], pos_top="97%", range_start=range_start, range_end=100
        ),
        opts.DataZoomOpts(
            is_show=False, xaxis_index=[0, 2], range_start=range_start, range_end=100
        ),
    ]
    if config['chart_show_futu'] != 'macd':
        datazoom_opts.append(
            opts.DataZoomOpts(
                is_show=False, xaxis_index=[0, 3], range_start=range_start, range_end=100
            ),
        )

    klines_chart = (cKline().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
        series_name="",
        y_axis=klines_yaxis,
        itemstyle_opts=opts.ItemStyleOpts(
            color=color_k_up,
            color0=color_k_down,
            border_color=color_k_up,
            border_color0=color_k_down,
        ),

    ).set_global_opts(
        title_opts=opts.TitleOpts(title=title, pos_left="0"),
        xaxis_opts=opts.AxisOpts(
            type_="category",
            is_scale=True,
            axisline_opts=opts.AxisLineOpts(is_on_zero=False),
            splitline_opts=opts.SplitLineOpts(is_show=False),
            axislabel_opts=opts.LabelOpts(is_show=False),
            split_number=20,
            min_="dataMin",
            max_="dataMax",
        ),
        yaxis_opts=opts.AxisOpts(
            is_scale=True,
            splitline_opts=opts.SplitLineOpts(is_show=False),
            position="right",
            axislabel_opts=opts.LabelOpts(is_show=False),
            axisline_opts=opts.AxisLineOpts(is_show=False),
            axistick_opts=opts.AxisTickOpts(is_show=False),
        ),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        datazoom_opts=datazoom_opts,
        brush_opts=brush_opts
    )
    )

    # 画 完成笔
    line_bi = (
        Line().add_xaxis(line_bis['index']).add_yaxis(
            "笔",
            line_bis['val'],
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=1, color=color_bi),
        )
    )
    overlap_kline = klines_chart.overlap(line_bi)

    # 画 未完成笔
    line_xu_bi = (
        Line().add_xaxis(line_xu_bis['index']).add_yaxis(
            "笔",
            line_xu_bis['val'],
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=1, type_='dashed', color=color_bi),
        )
    )
    overlap_kline = overlap_kline.overlap(line_xu_bi)

    # 画顶底分型
    fenxing_ding = (
        Scatter().add_xaxis(point_ding['index']).add_yaxis(
            "分型",
            point_ding['val'],
            itemstyle_opts=opts.ItemStyleOpts(color='red'),
            symbol_size=2,
            label_opts=opts.LabelOpts(is_show=False)
        ).set_series_opts(
            label_opts=opts.LabelOpts(
                color='rgb(255,200,44,0.3)', position='top', font_weight='bold',
                formatter=JsCode('function (params) {return params.value[2];}'),
            )
        )
    )
    fenxing_di = (
        Scatter().add_xaxis(point_di['index']).add_yaxis(
            "分型",
            point_di['val'],
            itemstyle_opts=opts.ItemStyleOpts(color='green'),
            symbol_size=2,
            label_opts=opts.LabelOpts(is_show=False)
        ).set_series_opts(
            label_opts=opts.LabelOpts(
                color='rgb(255,200,44,0.3)', position='bottom', font_weight='bold',
                formatter=JsCode('function (params) {return params.value[2];}'),
            )
        )
    )
    overlap_kline = overlap_kline.overlap(fenxing_ding)
    overlap_kline = overlap_kline.overlap(fenxing_di)

    # 画 完成线段
    line_xd = (
        Line().add_xaxis(line_xds['index']).add_yaxis(
            "线段",
            line_xds['val'],
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2, color=color_xd)
        )
    )
    overlap_kline = overlap_kline.overlap(line_xd)
    # 画 未完成线段
    line_xu_xd = (
        Line().add_xaxis(line_xu_xds['index']).add_yaxis(
            "线段",
            line_xu_xds['val'],
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2, type_='dashed', color=color_xd)
        )
    )
    overlap_kline = overlap_kline.overlap(line_xu_xd)

    # 画线段的特征序列
    # line_xd_xl_dings = []
    # line_xd_xl_dis = []
    # for xd in xds:
    #     if xd.type == 'up':
    #         for xl in xd.ding_fx.xls:
    #             if xl is None:
    #                 continue
    #             line_xd_xl_dings.append(
    #                 {'index': [xl.get_start_fx().k.date, xl.get_end_fx().k.date],
    #                  'val': [xl.get_start_fx().val, xl.get_end_fx().val]}
    #             )
    #     elif xd.type == 'down':
    #         for xl in xd.di_fx.xls:
    #             if xl is None:
    #                 continue
    #             line_xd_xl_dis.append(
    #                 {'index': [xl.get_start_fx().k.date, xl.get_end_fx().k.date],
    #                  'val': [xl.get_start_fx().val, xl.get_end_fx().val]}
    #             )
    # for line_xl in line_xd_xl_dings:
    #     overlap_kline = overlap_kline.overlap(Line().add_xaxis(line_xl['index']).add_yaxis(
    #         "特征序列",
    #         line_xl['val'],
    #         label_opts=opts.LabelOpts(is_show=False),
    #         linestyle_opts=opts.LineStyleOpts(width=4, type_='solid', color='red')
    #     ))
    # for line_xl in line_xd_xl_dis:
    #     overlap_kline = overlap_kline.overlap(Line().add_xaxis(line_xl['index']).add_yaxis(
    #         "特征序列",
    #         line_xl['val'],
    #         label_opts=opts.LabelOpts(is_show=False),
    #         linestyle_opts=opts.LineStyleOpts(width=4, type_='solid', color='green')
    #     ))

    # 画 完成大趋势
    line_qs = (
        Line().add_xaxis(line_zsds['index']).add_yaxis(
            "走势段",
            line_zsds['val'],
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2, color=color_zsd)
        )
    )
    overlap_kline = overlap_kline.overlap(line_qs)
    # 画 未完成大趋势
    line_xu_qs = (
        Line().add_xaxis(line_xu_zsds['index']).add_yaxis(
            "走势段",
            line_xu_zsds['val'],
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2, type_='dashed', color=color_zsd)
        )
    )
    overlap_kline = overlap_kline.overlap(line_xu_qs)

    # 画趋势通道线
    idx_qstd = cl_qstd(cl_data, config['chart_qstd'].split(',')[0], int(config['chart_qstd'].split(',')[1]))
    if idx_qstd is not None:
        qstd_up_line = (
            Line().add_xaxis(idx_qstd['up']['chart']['x']).add_yaxis(
                "趋势通道线",
                idx_qstd['up']['chart']['y'],
                is_connect_nones=True,
                is_clip=False,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=3, color=color_qstd_up),
            )
        )
        qstd_down_line = (
            Line().add_xaxis(idx_qstd['down']['chart']['x']).add_yaxis(
                "趋势通道线",
                idx_qstd['down']['chart']['y'],
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=3, color=color_qstd_down),
            )
        )
        overlap_kline = overlap_kline.overlap(qstd_up_line)
        overlap_kline = overlap_kline.overlap(qstd_down_line)

    if config['chart_show_boll']:
        # 计算boll线
        boll_up, boll_mid, boll_low = talib.BBANDS(np.array([k.c for k in klines]),
                                                   timeperiod=config['chart_idx_boll_period'])
        # 画 指标线
        line_idx_boll = (
            Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
                series_name="BOLL",
                is_symbol_show=False,
                y_axis=boll_up,
                linestyle_opts=opts.LineStyleOpts(width=1, color='#99CC99'),
                label_opts=opts.LabelOpts(is_show=False),
            ).add_yaxis(
                series_name="BOLL",
                is_symbol_show=False,
                y_axis=boll_mid,
                linestyle_opts=opts.LineStyleOpts(width=1, color='#FF6D00'),
                label_opts=opts.LabelOpts(is_show=False),
            ).add_yaxis(
                series_name="BOLL",
                is_symbol_show=False,
                y_axis=boll_low,
                linestyle_opts=opts.LineStyleOpts(width=1, color='#99CC99'),
                label_opts=opts.LabelOpts(is_show=False),
            ).set_global_opts()
        )
        overlap_kline = overlap_kline.overlap(line_idx_boll)
    if config['chart_show_ma']:
        # 计算ma线
        ma_colors = ['rgb(255,141,30)', 'rgb(12,174,230)', 'rgb(233,112,220)', 'rgb(0,128,250)', 'rgb(34,197,126)']
        ma_periods = config['chart_idx_ma_period'].split(',')[0:5]
        for i in range(len(ma_periods)):
            ma_period = ma_periods[i]
            ma = talib.MA(np.array([k.c for k in klines]), timeperiod=int(ma_period))
            line_idx_ma = (
                Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
                    series_name=f"MA{ma_period}",
                    is_symbol_show=False,
                    y_axis=ma,
                    linestyle_opts=opts.LineStyleOpts(width=1, color=ma_colors[i]),
                    label_opts=opts.LabelOpts(is_show=False),
                ).set_global_opts()
            )
            overlap_kline = overlap_kline.overlap(line_idx_ma)

    # 画 笔中枢
    for zs in line_bi_zss:
        bi_zs = (
            Line().add_xaxis(zs[0]).add_yaxis(
                "笔中枢",
                zs[1],
                symbol=None,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=zs[3], color=zs[2], type_='solid' if zs[4] else 'dashed'),
                areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color=zs[2]),
                tooltip_opts=opts.TooltipOpts(is_show=False),
            )
        )
        overlap_kline = overlap_kline.overlap(bi_zs)
    # 画 线段 中枢
    for zs in line_zs_zss:
        xd_zs = (
            Line().add_xaxis(zs[0]).add_yaxis(
                "线段中枢",
                zs[1],
                symbol=None,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=zs[3], color=zs[2], type_='solid' if zs[4] else 'dashed'),
                areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color=zs[2]),
                tooltip_opts=opts.TooltipOpts(is_show=False),
            )
        )
        overlap_kline = overlap_kline.overlap(xd_zs)
    # 画 走势段 中枢
    for zs in line_zsd_zss:
        xd_zs = (
            Line().add_xaxis(zs[0]).add_yaxis(
                "走势段中枢",
                zs[1],
                symbol=None,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=zs[3], color=zs[2], type_='solid' if zs[4] else 'dashed'),
                areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color=zs[2]),
                tooltip_opts=opts.TooltipOpts(is_show=False),
            )
        )
        overlap_kline = overlap_kline.overlap(xd_zs)

    # 画最后一笔、线段中枢
    if len(line_last_bi_zs) > 0:
        overlap_kline = overlap_kline.overlap(
            (
                Line().add_xaxis(line_last_bi_zs[0]).add_yaxis(
                    "笔中枢",
                    line_last_bi_zs[1],
                    symbol=None,
                    label_opts=opts.LabelOpts(is_show=False),
                    linestyle_opts=opts.LineStyleOpts(width=line_last_bi_zs[3], color=line_last_bi_zs[2],
                                                      type_='solid' if line_last_bi_zs[4] else 'dashed'),
                    # areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color=line_last_bi_zs[2]),
                    tooltip_opts=opts.TooltipOpts(is_show=False),
                )
            )
        )
    # if len(line_last_xd_zs) > 0:
    #     overlap_kline = overlap_kline.overlap(
    #         (
    #             Line().add_xaxis(line_last_xd_zs[0]).add_yaxis(
    #                 "线段中枢",
    #                 line_last_xd_zs[1],
    #                 symbol=None,
    #                 label_opts=opts.LabelOpts(is_show=False),
    #                 linestyle_opts=opts.LineStyleOpts(width=line_last_xd_zs[3], color=line_last_xd_zs[2],
    #                                                   type_='solid' if line_last_xd_zs[4] else 'dashed'),
    #                 # areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color=line_last_xd_zs[2]),
    #                 tooltip_opts=opts.TooltipOpts(is_show=False),
    #             )
    #         )
    #     )

    # 画背驰
    scatter_bc_tu = (
        Scatter().add_xaxis(xaxis_data=scatter_bc['i']).add_yaxis(
            series_name="背驰",
            y_axis=scatter_bc['val'],
            symbol_size=10,
            symbol='circle',
            itemstyle_opts=opts.ItemStyleOpts(color='rgba(223,148,100,0.7)'),
            label_opts=opts.LabelOpts(is_show=False),
            tooltip_opts=opts.TooltipOpts(
                textstyle_opts=opts.TextStyleOpts(font_size=12),
                formatter=JsCode(
                    "function (params) {return params.value[2];}"
                )
            ),
        )
        # ).set_series_opts(
        #     label_opts=opts.LabelOpts(color='red', formatter=JsCode("function (params) {return params.value[2];}"))
        # )
    )
    overlap_kline = overlap_kline.overlap(scatter_bc_tu)

    # 画买卖点
    scatter_buy_tu = (
        Scatter().add_xaxis(xaxis_data=scatter_buy['i']).add_yaxis(
            series_name="买卖点",
            y_axis=scatter_buy['val'],
            symbol_size=10,
            symbol='arrow',
            itemstyle_opts=opts.ItemStyleOpts(color='rgba(250,128,114,0.8)'),
            # tooltip_opts=opts.TooltipOpts(
            #     textstyle_opts=opts.TextStyleOpts(font_size=12),
            #     formatter=JsCode(
            #         "function (params) {return params.value[2];}"
            #     )
            # ),
        ).set_series_opts(
            label_opts=opts.LabelOpts(
                color='rgb(255,200,44)', position='bottom', font_weight='bold',
                formatter=JsCode('function (params) {return params.value[2];}'),
            )
        )
    )
    scatter_sell_tu = (
        Scatter().add_xaxis(xaxis_data=scatter_sell['i']).add_yaxis(
            series_name="买卖点",
            y_axis=scatter_sell['val'],
            symbol_size=10,
            symbol='arrow',
            symbol_rotate=180,
            itemstyle_opts=opts.ItemStyleOpts(color='rgba(30,144,255,0.8)'),
            # tooltip_opts=opts.TooltipOpts(
            #     textstyle_opts=opts.TextStyleOpts(font_size=12),
            #     formatter=JsCode(
            #         "function (params) {return params.value[2];}"
            #     )
            # ),
        ).set_series_opts(
            label_opts=opts.LabelOpts(
                color='rgb(255,200,44)', position='top', font_weight='bold',
                formatter=JsCode('function (params) {return params.value[2];}'),
            )
        )
    )
    overlap_kline = overlap_kline.overlap(scatter_buy_tu)
    overlap_kline = overlap_kline.overlap(scatter_sell_tu)

    # 画订单记录
    if orders and len(orders) > 0:
        scatter_buy_orders_tu = (
            Scatter().add_xaxis(xaxis_data=scatter_buy_orders['i']).add_yaxis(
                series_name="订单",
                y_axis=scatter_buy_orders['val'],
                symbol_size=15,
                symbol='arrow',
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgba(255,215,0,0.7)'),
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode(
                        "function (params) {return params.value[2];}"
                    )
                ),
            )
        )
        overlap_kline = overlap_kline.overlap(scatter_buy_orders_tu)
        scatter_sell_orders_tu = (
            Scatter().add_xaxis(xaxis_data=scatter_sell_orders['i']).add_yaxis(
                series_name="订单",
                y_axis=scatter_sell_orders['val'],
                symbol_size=15,
                symbol='arrow',
                symbol_rotate=180,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgba(127,255,212,0.7)'),
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode(
                        "function (params) {return params.value[2];}"
                    )
                ),
            )
        )
        overlap_kline = overlap_kline.overlap(scatter_sell_orders_tu)

    # 成交量
    bar_vols = (
        Bar().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
            series_name="volume",
            y_axis=vol,
            bar_width='60%',
        ).set_global_opts(
            legend_opts=opts.LegendOpts(is_show=False),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=True, color="#9b9da9"),
                                     type_='category', grid_index=1),
            yaxis_opts=opts.AxisOpts(
                position="right",
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
            )
        )
    )
    # 成交量均线
    vols_periods = config['chart_idx_vol_ma_period'].split(',')[0:2]
    vols_line_color = ['white', 'yellow']
    line_vols_ma = (
        Line().add_xaxis(xaxis_data=klines_xaxis).set_global_opts(
            legend_opts=opts.LegendOpts(is_show=True),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
            yaxis_opts=opts.AxisOpts(position="right",
                                     axislabel_opts=opts.LabelOpts(is_show=False),
                                     axisline_opts=opts.AxisLineOpts(is_show=False),
                                     axistick_opts=opts.AxisTickOpts(is_show=False)),
        )
    )
    for i in range(len(vols_periods)):
        vol_ma = talib.MA(np.array(klines_vols), timeperiod=int(vols_periods[i]))
        line_vols_ma.add_yaxis(
            series_name=f"MA{vols_periods[i]}",
            y_axis=vol_ma,
            is_symbol_show=False,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(color=vols_line_color[i]),
            linestyle_opts=opts.LineStyleOpts(width=2),

        )

    # 最下面的柱状图和折线图
    vols_bar_line = bar_vols.overlap(line_vols_ma)

    # MACD
    # macd_dif, macd_dea, macd_hist = talib.MACD(np.array([k.c for k in klines]),
    #                                            fastperiod=12,
    #                                            slowperiod=26,
    #                                            signalperiod=9)
    bar_macd = (
        Bar().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
            series_name="MACD",
            y_axis=list(idx['macd']['hist']),
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                color=JsCode('function(p){var c;if (p.data >= 0) {c = \'#ef232a\';} else {c = \'#14b143\';}return c;}')
            ),
        ).set_global_opts(
            legend_opts=opts.LegendOpts(is_show=False),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
            yaxis_opts=opts.AxisOpts(
                position="right",
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
            ),
        )
    )

    line_macd_dif = (
        Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
            series_name="DIF",
            y_axis=idx['macd']['dif'],
            is_symbol_show=False,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(color='white'),
        ).add_yaxis(
            series_name="DEA",
            y_axis=idx['macd']['dea'],
            is_symbol_show=False,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(color='yellow'),
        ).set_global_opts(
            legend_opts=opts.LegendOpts(is_show=True),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
            yaxis_opts=opts.AxisOpts(position="right",
                                     axislabel_opts=opts.LabelOpts(is_show=False),
                                     axisline_opts=opts.AxisLineOpts(is_show=False),
                                     axistick_opts=opts.AxisTickOpts(is_show=False)),
        )
    )

    # 最下面的柱状图和折线图
    macd_bar_line = bar_macd.overlap(line_macd_dif)

    # 最后的 Grid
    grid_chart = Grid(init_opts=opts.InitOpts(width="100%", height=f"{config['chart_high']}px", theme='dark'))

    grid_chart.add(
        overlap_kline,
        grid_opts=opts.GridOpts(width="96%", height="65%", pos_left='1%', pos_right='3%'),
    )

    # Volumn 柱状图
    grid_chart.add(
        vols_bar_line,
        grid_opts=opts.GridOpts(
            pos_bottom="15%", height="20%", width="96%", pos_left='1%', pos_right='3%'
        ),
    )

    futu_charts = [macd_bar_line]

    if config['chart_show_futu'] == 'rsi':
        rsi = talib.RSI(np.array([_k.c for _k in klines]), timeperiod=config['chart_idx_rsi_period'])
        rsi_line = (
            Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
                series_name="RSI",
                y_axis=rsi,
                is_symbol_show=False,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgb(233,112,220'),
            ).set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
                yaxis_opts=opts.AxisOpts(position="right",
                                         axislabel_opts=opts.LabelOpts(is_show=False),
                                         axisline_opts=opts.AxisLineOpts(is_show=False),
                                         axistick_opts=opts.AxisTickOpts(is_show=False)),
            )
        )
        futu_charts.append(rsi_line)
    elif config['chart_show_futu'] == 'atr':
        atr = talib.ATR(
            np.array([_k.h for _k in klines]),
            np.array([_k.l for _k in klines]),
            np.array([_k.c for _k in klines]),
            timeperiod=config['chart_idx_atr_period']
        )
        atr_line = (
            Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
                series_name="ATR",
                y_axis=atr,
                is_symbol_show=False,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgb(12,174,210'),
            ).set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
                yaxis_opts=opts.AxisOpts(position="right",
                                         axislabel_opts=opts.LabelOpts(is_show=False),
                                         axisline_opts=opts.AxisLineOpts(is_show=False),
                                         axistick_opts=opts.AxisTickOpts(is_show=False)),
            )
        )
        futu_charts.append(atr_line)
    elif config['chart_show_futu'] == 'cci':
        cci = talib.CCI(
            np.array([_k.h for _k in klines]),
            np.array([_k.l for _k in klines]),
            np.array([_k.c for _k in klines]),
            timeperiod=config['chart_idx_cci_period']
        )
        cci_line = (
            Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
                series_name="CCI",
                y_axis=cci,
                is_symbol_show=False,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgb(12,174,210'),
            ).set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
                yaxis_opts=opts.AxisOpts(position="right",
                                         axislabel_opts=opts.LabelOpts(is_show=False),
                                         axisline_opts=opts.AxisLineOpts(is_show=False),
                                         axistick_opts=opts.AxisTickOpts(is_show=False)),
            )
        )
        futu_charts.append(cci_line)
    elif config['chart_show_futu'] == 'kdj':
        _K, _D, _J = MyTT.KDJ(
            np.array([_k.c for _k in klines]),
            np.array([_k.h for _k in klines]),
            np.array([_k.l for _k in klines]),
            N=int(config['chart_idx_kdj_period'].split(',')[0]),
            M1=int(config['chart_idx_kdj_period'].split(',')[1]),
            M2=int(config['chart_idx_kdj_period'].split(',')[2])
        )
        kdj_line = (
            Line().add_xaxis(xaxis_data=klines_xaxis).add_yaxis(
                series_name="CCI K",
                y_axis=_K,
                is_symbol_show=False,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgb(12,174,210'),
            ).add_yaxis(
                series_name="CCI D",
                y_axis=_D,
                is_symbol_show=False,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color='rgb(25,201,14'),
            ).set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(is_show=False), ),
                yaxis_opts=opts.AxisOpts(position="right",
                                         axislabel_opts=opts.LabelOpts(is_show=False),
                                         axisline_opts=opts.AxisLineOpts(is_show=False),
                                         axistick_opts=opts.AxisTickOpts(is_show=False)),
            )
        )
        futu_charts.append(kdj_line)
    elif config['chart_show_futu'] == 'custom':
        pass

    # 副图技术指标
    for i in range(len(futu_charts)):
        grid_chart.add(
            futu_charts[i],
            grid_opts=opts.GridOpts(
                pos_bottom=f"{int(15 / len(futu_charts)) * i}%",
                height=f"{int(15 / len(futu_charts))}%",
                width="96%", pos_left='1%', pos_right='3%'
            ),
        )

    if "JPY_PARENT_PID" in os.environ:
        return grid_chart.render_notebook()
    else:
        return grid_chart.dump_options()
