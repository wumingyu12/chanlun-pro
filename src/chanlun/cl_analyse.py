from chanlun.cl_interface import *


class MultiLevelAnalyse:
    """
    缠论多级别分析
    """

    def __init__(self, up_cd: ICL, low_cd: ICL):
        self.up_cd: ICL = up_cd
        self.low_cd: ICL = low_cd

    def low_level_qs(self, up_line: LINE, low_line_type='bi') -> LOW_LEVEL_QS:
        """
        根据高级别笔，获取其低级别笔的趋势信息
        """
        low_lines = self._query_low_lines(up_line, low_line_type)
        low_zss = self._query_low_zss(low_lines, low_line_type)
        qs_bc_info = self._query_qs_and_bc(low_zss, low_line_type)

        low_level_qs = LOW_LEVEL_QS()
        low_level_qs.zss = low_zss
        low_level_qs.zs_num = len(low_zss)
        low_level_qs.lines = low_lines
        low_level_qs.line_num = len(low_lines)
        low_level_qs.last_line = low_lines[-1] if len(low_lines) > 0 else None
        low_level_qs.qs = qs_bc_info['qs']
        low_level_qs.pz = qs_bc_info['pz']
        low_level_qs.qs_bc = qs_bc_info['qs_bc']
        low_level_qs.pz_bc = qs_bc_info['pz_bc']
        low_level_qs.bc_line = qs_bc_info['bc_line']

        return low_level_qs

    def up_bi_low_level_qs(self) -> LOW_LEVEL_QS:
        """
        高级别笔，最后一笔的低级别趋势信息(低级别查找的是笔)
        """
        last_bi = self.up_cd.get_bis()[-1]
        return self.low_level_qs(last_bi, 'bi')

    def up_xd_low_level_qs(self) -> LOW_LEVEL_QS:
        """
        高级别线段，最后一线段的低级别趋势信息(低级别查找的是笔)
        """
        last_xd = self.up_cd.get_xds()[-1]
        return self.low_level_qs(last_xd, 'bi')

    def _query_low_lines(self, up_line: LINE, query_line_type='bi'):
        """
        根据高级别的线，查询其包含的低级别的线
        """
        start_date = up_line.start.k.date
        end_date = up_line.end.k.date

        low_lines: List[LINE] = []
        find_lines = self.low_cd.get_bis() if query_line_type == 'bi' else self.low_cd.get_xds()
        for _line in find_lines:
            if _line.end.k.date < start_date:
                continue
            if end_date is not None and _line.start.k.date > end_date:
                break
            if len(low_lines) == 0 and _line.type != up_line.type:
                continue
            low_lines.append(_line)
        if len(low_lines) > 0 and low_lines[-1].type != up_line.type:
            del (low_lines[-1])

        return low_lines

    def _query_low_zss(self, low_lines: List[LINE], zs_type='bi'):
        """
        构建并返回低级别线构建的中枢
        """
        low_zss = self.low_cd.create_dn_zs(zs_type, low_lines)
        return low_zss

    def _query_qs_and_bc(self, low_zss: List[ZS], low_line_type='bi'):
        """
        根据低级别线和中枢，计算并给出是否中枢已经背驰信息
        """
        qs = False
        pz = False
        qs_bc = False
        pz_bc = False
        if len(low_zss) == 0:
            return {'qs': qs, 'pz': pz, 'qs_bc': qs_bc, 'pz_bc': pz_bc, 'bc_line': None}

        # 判断是否盘整背驰
        pz = True if low_zss[-1].type in ['up', 'down'] else False
        pz_bc, _ = self.low_cd.beichi_pz(low_zss[-1], low_zss[-1].lines[-1])

        # 判断是否趋势背驰
        base_lines = self.low_cd.get_bis() if low_line_type == 'bi' else self.low_cd.get_xds()
        if len(low_zss) >= 2:
            qs = self.low_cd.zss_is_qs(low_zss[-2], low_zss[-1])
            qs_bc, _ = self.low_cd.beichi_qs(base_lines, low_zss, low_zss[-1].lines[-1])

        bc_line = None
        if pz_bc or qs_bc:
            bc_line = low_zss[-1].lines[-1]

        return {'qs': qs, 'pz': pz, 'qs_bc': qs_bc, 'pz_bc': pz_bc, 'bc_line': bc_line}
