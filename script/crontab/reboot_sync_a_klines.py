import random
import time
from chanlun.exchange.exchange_db import ExchangeDB
from chanlun.exchange.exchange_baostock import ExchangeBaostock
from tqdm.auto import tqdm

"""
同步股票数据到数据库中
"""

db_ex = ExchangeDB('a')
line_ex = ExchangeBaostock()

# 获取所有 A 股股票
stocks = line_ex.all_stocks()
run_codes = [s['code'] for s in stocks]
random.shuffle(run_codes)  # 打乱，可以多进程运行

# run_codes = ['sh.600006']

print('Run code num: ', len(run_codes))

# 创建表
db_ex.create_tables(run_codes)


def sync_code(_code):
    try:
        for f in ['m', 'w', 'd', '30m', '5m']:
            time.sleep(1)
            while True:
                last_dt = db_ex.query_last_datetime(_code, f)
                # tqdm.write('%s - %s last dt %s' % (_code, f, last_dt))
                if last_dt is None:
                    klines = line_ex.klines(_code, f, start_date='2021-01-01', args={'fq': 'hfq'})
                    if len(klines) == 0:
                        klines = line_ex.klines(_code, f, args={'fq': 'hfq'})
                else:
                    klines = line_ex.klines(_code, f, start_date=last_dt, args={'fq': 'hfq'})

                tqdm.write('Run code %s frequency %s klines len %s' % (_code, f, len(klines)))
                db_ex.insert_klines(_code, f, klines)
                if len(klines) <= 100:
                    break
    except Exception as e:
        tqdm.write('执行 %s 同步K线异常 %s' % (_code, str(e)))
        time.sleep(10)


for code in tqdm(run_codes):
    sync_code(code)

print('Done')
