from chanlun.exchange.exchange_binance import ExchangeBinance
from chanlun.exchange.exchange_db import ExchangeDB
import traceback
from tqdm.auto import tqdm

"""
同步数字货币行情到数据库中
"""

exchange = ExchangeDB('currency')
line_exchange = ExchangeBinance()

# 创建表
stocks = line_exchange.all_stocks()
codes = [s['code'] for s in stocks]
exchange.create_tables(codes)

for code in tqdm(codes):
    try:
        for f in ['w', 'd', '4h', '60m', '30m', '15m', '5m', '1m']:
            while True:
                try:
                    last_dt = exchange.query_last_datetime(code, f)
                    if last_dt is None:
                        klines = line_exchange.klines(code, f, end_date='2021-06-01 00:00:00')
                        if len(klines) == 0:
                            klines = line_exchange.klines(code, f, start_date='2021-06-01 00:00:00')
                    else:
                        klines = line_exchange.klines(code, f, start_date=last_dt)

                    tqdm.write('Run code %s frequency %s klines len %s' % (code, f, len(klines)))
                    exchange.insert_klines(code, f, klines)
                    if len(klines) <= 1:
                        break
                except Exception as e:
                    tqdm.write('执行 %s 同步K线异常' % code)
                    tqdm.write(traceback.format_exc())
                    break

    except Exception as e:
        tqdm.write('执行 %s 同步K线异常' % code)
        tqdm.write(e)
        tqdm.write(traceback.format_exc())
