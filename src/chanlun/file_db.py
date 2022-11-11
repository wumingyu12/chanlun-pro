import hashlib
import os
import pickle

from chanlun import cl
from chanlun.exchange.exchange_db import ExchangeDB
from chanlun.cl_interface import ICL


class FileDB(object):
    """
    文件数据对象
    """

    def __init__(self):
        """
        初始化，判断文件并进行创建
        """
        self.home_path = os.path.expanduser('~')
        self.project_path = self.home_path + '/.chanlun_pro'
        if os.path.isdir(self.project_path) is False:
            os.mkdir(self.project_path)
        self.data_path = self.project_path + '/data'
        if os.path.isdir(self.data_path) is False:
            os.mkdir(self.data_path)

    def get_cl_data(self, market: str, code: str, frequency: str, cl_config: dict) -> ICL:
        """
        专门为递归到高级别图表写的方法，初始数据量较多，所以只能从数据库中获取
        计算一次后进行落盘保存，后续读盘进行更新操作，减少重复计算的时间
        建议定时频繁的进行读取，保持更新，避免太多时间不读取，后续造成数据缺失情况
        """
        config_keys = [
            'kline_type', 'fx_qj', 'fx_bh', 'bi_type', 'bi_bzh', 'bi_qj', 'bi_fx_cgd',
            'xd_bzh', 'xd_qj', 'zsd_bzh', 'zsd_qj', 'zs_bi_type', 'zs_xd_type', 'zs_qj', 'zs_wzgx',
            'idx_macd_fast', 'idx_macd_slow', 'idx_macd_signal'
        ]
        key = hashlib.md5(
            f'{[f"{k}:{v}" for k, v in cl_config.items() if k in config_keys]}'.encode('UTF-8')
        ).hexdigest()
        filename = f'{self.data_path}/{market}_{code.replace("/", "_")}_{frequency}_{key}.pkl'
        cd: ICL
        if os.path.isfile(filename) is False:
            cd = cl.CL(code, frequency, cl_config)
        else:
            with open(filename, 'rb') as fp:
                cd = pickle.load(fp)
        ex = ExchangeDB(market)
        limit = 200000
        if len(cd.get_klines()) > 10000:
            limit = 1000
        klines = ex.klines(code, frequency, args={'limit': limit})
        cd.process_klines(klines)
        with open(filename, 'wb') as fp:
            pickle.dump(cd, fp)
        return cd


if __name__ == '__main__':
    from chanlun.cl_utils import query_cl_chart_config

    market = 'a'
    code = 'SHSE.000001'
    frequency = '5m'
    cl_config = query_cl_chart_config(market, code)

    fdb = FileDB()
    cd = fdb.get_cl_data(market, code, frequency, cl_config)
    print(len(cd.get_klines()))
    print(cd)
