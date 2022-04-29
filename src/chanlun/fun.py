import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests

from chanlun import config
from chanlun.cl_interface import *


def get_logger(filename=None, level=logging.INFO):
    """
    获取一个日志记录的对象
    """
    logger = logging.getLogger('currency')
    logger.setLevel(level)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s : %(message)s')
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

    if filename:
        file_handler = logging.FileHandler(filename=filename)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def send_dd_msg(market, msg):
    """
    发送钉钉消息
    :param market:
    :param msg:
    :return:
    """
    dd_info = None
    if market == 'a':
        dd_info = config.DINGDING_KEY_A
    elif market == 'hk':
        dd_info = config.DINGDING_KEY_HK
    elif market == 'us':
        dd_info = config.DINGDING_KEY_US
    elif market == 'currency':
        dd_info = config.DINGDING_KEY_CURRENCY
    elif market == 'futures':
        dd_info = config.DINGDING_KEY_FUTURES
    else:
        raise Exception('没有配置钉钉的信息')

    url = 'https://oapi.dingtalk.com/robot/send?access_token=%s&timestamp=%s&sign=%s'

    def sign():
        timestamp = str(round(time.time() * 1000))
        secret = dd_info['secret']
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        _sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, _sign

    t, s = sign()
    url = url % (dd_info['token'], t, s)
    requests.post(url, json={
        'msgtype': 'text',
        'text': {"content": msg},
    })
    return True


def convert_stock_order_by_frequency(orders, frequency):
    """
    订单专用转换器
    :param orders:
    :param frequency:
    :return:
    """
    new_orders = []
    for o in orders:
        if isinstance(o['datetime'], str):
            dt = datetime.datetime.strptime(o['datetime'], '%Y-%m-%d %H:%M:%S')
        else:
            dt = o['datetime']
        dt_time = int(time.mktime(dt.timetuple()))
        seconds = 0
        if frequency == 'd':
            seconds = 24 * 60 * 60
        elif frequency == '120m':
            seconds = 2 * 60 * 60
        elif frequency == '60m':
            seconds = 60 * 60
        elif frequency == '30m':
            seconds = 30 * 60
        elif frequency == '15m':
            seconds = 15 * 60
        elif frequency == '5m':
            seconds = 5 * 60
        elif frequency == '1m':
            seconds = 1 * 60
        if seconds == 0:
            return new_orders
        dt_time -= dt_time % seconds

        if frequency in ['d']:
            dt_time -= 8 * 60 * 60
        if 'm' in frequency:
            dt_time += seconds

        if frequency == '60m':
            if (dt.hour == 9) or (dt.hour == 10 and dt.minute <= 30):
                dt_time = datetime.datetime.timestamp(
                    datetime.datetime.strptime(dt.strftime('%Y-%m-%d 10:30:00'), '%Y-%m-%d %H:%M:%S'))
            elif (dt.hour == 10 and dt.minute >= 30) or (dt.hour == 11):
                dt_time = datetime.datetime.timestamp(
                    datetime.datetime.strptime(dt.strftime('%Y-%m-%d 11:30:00'), '%Y-%m-%d %H:%M:%S'))
        if frequency == '120m':
            if dt.hour == 9 or dt.hour == 10 or dt.hour == 11:
                dt_time = datetime.datetime.timestamp(
                    datetime.datetime.strptime(dt.strftime('%Y-%m-%d 11:30:00'), '%Y-%m-%d %H:%M:%S'))
            elif dt.hour >= 13:
                dt_time = datetime.datetime.timestamp(
                    datetime.datetime.strptime(dt.strftime('%Y-%m-%d 15:00:00'), '%Y-%m-%d %H:%M:%S'))
        dt_time = datetime.datetime.fromtimestamp(dt_time)
        dt_time = dt_time.strftime('%Y-%m-%d %H:%M:%S')
        new_orders.append({
            'datetime': dt_time,
            'type': o['type'],
            'price': o['price'],
            'amount': o['amount'],
            'info': '' if 'info' not in o else o['info'],
        })
    return new_orders


def convert_currency_order_by_frequency(orders, frequency):
    """
    数字货币专用订单转换器
    :param orders:
    :param frequency:
    :return:
    """
    new_orders = []
    for o in orders:
        if isinstance(o['datetime'], str):
            dt = datetime.datetime.strptime(o['datetime'], '%Y-%m-%d %H:%M:%S')
        else:
            dt = o['datetime']
        dt_time = int(time.mktime(dt.timetuple()))
        seconds = 0
        if frequency == 'd':
            seconds = 24 * 60 * 60
        elif frequency == '4h':
            seconds = 4 * 60 * 60
        elif frequency == '60m':
            seconds = 60 * 60
        elif frequency == '30m':
            seconds = 30 * 60
        elif frequency == '15m':
            seconds = 15 * 60
        elif frequency == '5m':
            seconds = 5 * 60
        elif frequency == '1m':
            seconds = 1 * 60
        dt_time -= dt_time % seconds
        dt_time = datetime.datetime.fromtimestamp(dt_time)
        dt_time = dt_time.strftime('%Y-%m-%d %H:%M:%S')
        new_orders.append({
            'datetime': dt_time,
            'type': o['type'],
            'price': o['price'],
            'amount': o['amount'],
            'info': '' if 'info' not in o else o['info'],
        })
    return new_orders


def timeint_to_str(_t, _format='%Y-%m-%d %H:%M:%S'):
    """
    时间戳转字符串
    :param _t:
    :param _format:
    :return:
    """
    time_arr = time.localtime(int(_t))
    return time.strftime(_format, time_arr)


def str_to_timeint(_t, _format='%Y-%m-%d %H:%M:%S'):
    """
    字符串转时间戳
    :param _t:
    :param _format:
    :return:
    """
    return int(time.mktime(time.strptime(_t, _format)))


def str_to_datetime(_s, _format='%Y-%m-%d %H:%M:%S'):
    """
    字符串转datetime类型
    :param _s:
    :param _format:
    :return:
    """
    return datetime.datetime.strptime(_s, _format)


def datetime_to_str(_dt: datetime.datetime, _format='%Y-%m-%d %H:%M:%S'):
    """
    datetime转字符串
    :param _dt:
    :param _format:
    :return:
    """
    return _dt.strftime(_format)


def str_add_seconds_to_str(_s, _seconds, _format='%Y-%m-%d %H:%M:%S'):
    """
    字符串日期时间，加上秒数，在返回新的字符串日期
    """
    _time = int(time.mktime(time.strptime(_s, _format)))
    _time += _seconds
    _time = time.localtime(int(_time))
    return time.strftime(_format, _time)


def now_dt():
    """
    返回当前日期字符串
    """
    return datetime_to_str(datetime.datetime.now())
