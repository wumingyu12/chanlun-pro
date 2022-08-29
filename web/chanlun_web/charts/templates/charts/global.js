// 请求 Kline 方法
function fetchKlinesData(chart_obj, market, code, frequency, update = false) {
    $('#loading').loading({theme: 'dark'});

    let market_klines_urls = {
        'a': '/stock/kline',
        'currency': '/currency/kline',
        'futures': '/futures/kline',
        'hk': '/hk/kline',
        'us': '/us/kline',
    };

    let post_data = {
        'code': code, 'frequency': frequency,
    }
    $.ajax({
        type: "POST", url: market_klines_urls[market], data: post_data, success: function (result) {
            var re_obj = (new Function("return " + result))();
            if (update === false) {
                chart_obj.clear();
            }
            chart_obj.setOption(re_obj);
            $('#loading').loading('stop');
        }
    });
}

// 定时刷新
$('#shuaxin').click(function () {
    let val = $(this).attr('value');
    if (val === '0') {
        // 开启自动更新
        $(this).attr('value', '1');
        $(this).text('关闭自动更新');
        intervalId = setInterval(function () {
            fetchKlinesData(chart_high, market, code, frequency_high, true);
            fetchKlinesData(chart_low, market, code, frequency_low, true);
        }, 15000);
    }
    if (val === '1') {
        // 关闭自动更新
        $(this).attr('value', '0');
        $(this).text('开启自动更新');
        clearInterval(intervalId);
    }
});

// 大图小图展示
function chart_show_height(_type) {
    if (_type === '0') {
        $('#kline_high').css('height', chart_div_high / 2);
        $('#kline_low').css('height', chart_div_high / 2);
    } else {
        $('#kline_high').css('height', chart_div_high);
        $('#kline_low').css('height', chart_div_high);
    }
    chart_high.resize();
    chart_low.resize();
}

$('#show_datu').click(function () {
    let val = $(this).attr('value');
    if (val === '0') {
        $.cookie(cookie_pre + '_show_datu', '0')
        $(this).attr('value', '1');
        $(this).text('切换到大图');
        chart_show_height(val)
    } else {
        $.cookie(cookie_pre + '_show_datu', '1')
        $(this).attr('value', '0');
        $(this).text('切换到小图');
        chart_show_height(val)
    }
});
if ($.cookie(cookie_pre + '_show_datu') === '1') {
    $('#show_datu').attr('value', '0');
    $('#show_datu').text('切换到小图');
    chart_show_height('1')
} else {
    $('#show_datu').attr('value', '1');
    $('#show_datu').text('切换到大图');
    chart_show_height('0')
}

// 周期切换功能
if ($.cookie(cookie_pre + '_frequency_high') !== undefined) {
    frequency_high = $.cookie(cookie_pre + '_frequency_high');
}
$('#zq_high').find('[data-zq="' + frequency_high + '"]').addClass('btn-primary');

$('#zq_high button').click(function () {
    $('#zq_high button').removeClass('btn-primary');
    $(this).addClass('btn-primary');
    frequency_high = $(this).attr('data-zq');
    $.cookie(cookie_pre + '_frequency_high', frequency_high, {expires: 999});
    fetchKlinesData(chart_high, market, code, frequency_high, false);
});

if ($.cookie(cookie_pre + '_frequency_low') !== undefined) {
    frequency_low = $.cookie(cookie_pre + '_frequency_low');
}
$('#zq_low').find('[data-zq="' + frequency_low + '"]').addClass('btn-primary');

$('#zq_low button').click(function () {
    $('#zq_low button').removeClass('btn-primary');
    $(this).addClass('btn-primary');
    frequency_low = $(this).attr('data-zq');
    $.cookie(cookie_pre + '_frequency_low', frequency_low, {expires: 999});
    fetchKlinesData(chart_low, market, code, frequency_low, false);
});


// 代码搜索
$('#search_code').typeahead(null, {
    name: 'search_code', display: 'code', minLength: 2, limit: 20, highlight: true, source: new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/search_code?market=' + market + '&query=%QUERY', wildcard: '%QUERY'
        }
    }), templates: {
        empty: ['<div class="empty-message">', '无代码信息', '</div>'].join('\n'), suggestion: function (res_json) {
            if (market === 'currency') {
                return '<div style="font-size:14px;"><b>' + res_json['code'] + '</b></div>'
            } else {
                return '<div style="font-size:14px;"><b>' + res_json['code'] + '</b>/' + res_json['name'] + '</div>'
            }
        },
    }
});

// 搜索框点击展示
$('#stock_ok').click(function () {
    var stock_code = $('#search_code').val();
    var stock_name = $('#search_code').attr('data-name');
    if (stock_code !== '') {
        code = stock_code;
        name = stock_name;
        fetchKlinesData(chart_high, market, code, frequency_high, false);
        fetchKlinesData(chart_low, market, code, frequency_low, false);
        query_cl_chart_config(market, code);
        if (market === 'a' || market === 'hk') {
            stock_plate(code);
        }
        zixuan_code_query_zx_names(code);
    }
});

// 点击切换股票行情
$("body").delegate('.code', 'click', function () {
    $('#my_stocks li').removeClass('active');
    $(this).addClass('active');
    code = $(this).attr('data-code');
    name = $(this).attr('data-name');
    fetchKlinesData(chart_high, market, code, frequency_high, false);
    fetchKlinesData(chart_low, market, code, frequency_low, false);
    query_cl_chart_config(market, code);
    if (market === 'a' || market === 'hk') {
        stock_plate(code);
    }
    zixuan_code_query_zx_names(code);
});

// 机会列表的展示
function jhs_list_show() {
    var urls = {
        'a': '/stock/jhs', 'currency': '/currency/jhs', 'hk': '/hk/jhs', 'us': '/us/jhs', 'futures': '/futures/jhs',
    }
    $.ajax({
        type: "GET", url: urls[market], dataType: 'json', success: function (result) {
            if (result['code'] === 200) {
                $('#jhs_ul').html('');
                for (let i = 0; i < result['data'].length; i++) {
                    jh = result['data'][i];
                    $('#jhs_ul').append('<li class="list-group-item"><p class="list-group-item-heading"><a href="javascript:void(0);" class="code" data-code="' + jh['code'] + '" data-name="' + jh['name'] + '">' + jh['name'] + '</a> <span>' + jh['frequency'] + '</span></p> <p class="list-group-item-text">' + jh['jh_type'] + ' <br/>' + jh['is_done'] + ' ' + jh['is_td'] + '<br/> ' + jh['datetime_str'] + '</p></li>');
                }
            }
        }
    });
}

// 获取股票行业与概念信息
function stock_plate(code) {
    $.ajax({
        type: "GET",
        url: "/stock/plate?code=" + code,
        dataType: 'json',
        success: function (result) {
            if (result['code'] === 200) {
                hy_list = '';
                gn_list = '';
                for (let i = 0; i < result['data']['HY'].length; i++) {
                    hy = result['data']['HY'][i];
                    hy_list += '<a href="javascript:void(0);" class="plate" data-hycode="' + hy['code'] + '">' + hy['name'] + '</a>  / '
                }
                for (let i = 0; i < result['data']['GN'].length; i++) {
                    gn = result['data']['GN'][i];
                    gn_list += '<a href="javascript:void(0);" class="plate" data-hycode="' + gn['code'] + '">' + gn['name'] + '</a>  / '
                }
                $('.hy_list').html(hy_list);
                $('.gn_list').html(gn_list);
            }
        }
    });
    return true
}


// 自选切换
$('.btn_zixuan').click(function () {
    $('.btn_zixuan').removeClass('btn-success');
    $(this).addClass('btn-success');
    var zx_name = $(this).attr('data-zxname');
    $.ajax({
        type: "GET",
        url: "/zixuan/stocks?market_type=" + market + "&zx_name=" + zx_name,
        dataType: 'json',
        success: function (result) {
            if (result['code'] === 200) {
                $('#my_stocks').html('');
                for (var i = 0; i < result['data'].length; i++) {
                    var stock = result['data'][i];
                    if (market === 'currency') {
                        $('#my_stocks').append('<li class="code" data-code="' + stock['code'] + '" data-name="' + stock['name'] + '"><a href="#' + stock['code'] + '"><span class="menu-text">' + stock['code'] + '</span></a></li>');
                    } else {
                        $('#my_stocks').append('<li class="code" data-code="' + stock['code'] + '" data-name="' + stock['name'] + '"><a href="#' + stock['code'] + '"><span class="menu-text">' + stock['code'] + ' / ' + stock['name'] + '</span></a></li>');
                    }
                }
                $('#stock_search').quicksearch('#my_stocks li');
            }
        }
    });
});

// 根据代码，查询自选分组
function zixuan_code_query_zx_names(code) {
    $.ajax({
        type: "GET",
        url: "/zixuan/code_zx_names?market_type=" + market + "&code=" + code,
        dataType: 'json',
        success: function (result) {
            if (result['code'] === 200) {
                $('#zixuan_zx_names').html('');
                for (let i = 0; i < result['data'].length; i++) {
                    var zx_name = result['data'][i];
                    var checked = zx_name['exists'] === 1 ? 'checked' : '';
                    $('#zixuan_zx_names').append('<li><div class="checkbox"><label>' + '<input name="zx_name" type="checkbox" data-zx-name="' + zx_name['zx_name'] + '" ' + checked + ' class="ace opt_zx">' + '<span class="lbl">' + zx_name['zx_name'] + '</span>' + '</label></div></li>');
                }
            }
        }
    });
}

// 自选操作
$("body").delegate('.opt_zx', 'change', function () {
    var checked = $(this).prop('checked');
    var zx_name = $(this).attr('data-zx-name');
    var opt = checked === true ? 'add' : 'del';
    $.ajax({
        type: "GET",
        url: '/zixuan/opt?market_type=' + market + '&zx_name=' + zx_name + '&opt=' + opt + '&code=' + code + '&name=' + name,
        dataType: 'json',
        success: function (result) {
            let msg = '';
            if (opt === 'add') {
                msg = '添加自选组 ' + zx_name + ' 成功';
            } else {
                msg = '删除自选组 ' + zx_name + ' 成功';
            }
            if (result['code'] === 200) {
                $.message({message: msg, type: 'success'});
            } else {
                $.message({message: '操作自选失败', type: 'error'});
            }
        }
    });
});
