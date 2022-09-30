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
        qs_bc_info = self._query_qs_and_bc(low_lines, low_zss, low_line_type)

        low_level_qs = LOW_LEVEL_QS(low_zss, low_lines)
        low_level_qs.zs_num = len(low_zss)
        low_level_qs.line_num = len(low_lines)
        low_level_qs.last_line = low_lines[-1] if len(low_lines) > 0 else None
        low_level_qs.qs = qs_bc_info['qs']
        low_level_qs.pz = qs_bc_info['pz']
        low_level_qs.line_bc = qs_bc_info['line_bc']
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

    def _query_qs_and_bc(self, low_lines: List[LINE], low_zss: List[ZS], low_line_type='bi'):
        """
        根据低级别线和中枢，计算并给出是否中枢已经背驰信息
        """
        qs = False
        pz = False
        qs_bc = False
        pz_bc = False
        line_bc = False

        # 判断是否线背
        if len(low_lines) >= 3:
            one_line = low_lines[-3]
            two_line = low_lines[-1]
            if two_line.type == 'up' \
                    and two_line.high > one_line.high and two_line.low > one_line.low \
                    and compare_ld_beichi(one_line.get_ld(self.low_cd), two_line.get_ld(self.low_cd),
                                          two_line.type):
                line_bc = True
            elif two_line.type == 'down' \
                    and two_line.low < one_line.low and two_line.high < one_line.high \
                    and compare_ld_beichi(one_line.get_ld(self.low_cd), two_line.get_ld(self.low_cd),
                                          two_line.type):
                line_bc = True

        if len(low_zss) == 0:
            return {'qs': qs, 'pz': pz, 'line_bc': line_bc, 'qs_bc': qs_bc, 'pz_bc': pz_bc, 'bc_line': None}

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

        return {'qs': qs, 'pz': pz, 'line_bc': line_bc, 'qs_bc': qs_bc, 'pz_bc': pz_bc, 'bc_line': bc_line}


class LinesFormAnalyse:
    """
    线的形态分析
    找出其中的 aAb aAbBc 类似的结果，并找出背驰的比较段，来判断结束位置
    """

    def __init__(self, cl_data: ICL):
        self.cd = cl_data

    def lines_analyse(self, line_num: int, lines: List[Union[LINE, BI, XD]]) -> Union[None, LINE_FORM_INFOS]:
        """
        多线分析
        """
        # 线段数量必须是奇数
        if line_num != len(lines):
            return None
        line_num = len(lines)
        if line_num % 2 == 0:
            return None
        line_direction = lines[0].type
        # 起始结束必须是最高和最低 TODO 这样一些复杂的形态就不能分析了
        lines_max_high = max([l.high for l in lines])
        lines_min_low = min([l.low for l in lines])
        if (line_direction == 'up' and (lines[0].low != lines_min_low or lines[-1].high != lines_max_high)) or \
                (line_direction == 'down' and (lines[0].high != lines_max_high or lines[-1].low != lines_min_low)):
            return None

        # 三笔的最简单，之间判断其是否背驰即可
        if line_num == 3:
            line_1_ld = lines[0].get_ld(self.cd)
            line_2_ld = lines[-1].get_ld(self.cd)
            line_bc = compare_ld_beichi(line_1_ld, line_2_ld, line_direction)
            return LINE_FORM_INFOS(
                lines=lines, direction=line_direction, line_num=line_num, form_type='三笔形态', is_bc_line=line_bc
            )

        # 多线首先判断是否是类趋势，一浪高过一浪 or 一浪低过一浪
        is_qs = True
        for i in range(3, line_num, 2):
            if line_direction == 'up':
                if lines[i - 2].high > lines[i].low:
                    is_qs = False
                    break
            elif line_direction == 'down':
                if lines[i - 2].low < lines[i].high:
                    is_qs = False
                    break
        if is_qs:
            # 确定是类趋势，判断最后两同向线的背驰
            line_1_ld = lines[-3].get_ld(self.cd)
            line_2_ld = lines[-1].get_ld(self.cd)
            line_bc = compare_ld_beichi(line_1_ld, line_2_ld, line_direction)
            return LINE_FORM_INFOS(
                lines=lines, direction=line_direction, line_num=line_num,
                form_type='类趋势', is_bc_line=line_bc, form_qs='类趋势'
            )

        # 根据线来创建中枢
        zss = self.cd.create_dn_zs('line', lines)
        # 判断是否只能组成一个中枢，并且中枢起始与结束就是线列表的起始与结束，比较进入与离开段是否背驰
        if len(zss) == 1 and zss[0].lines[0].index == lines[0].index and zss[0].lines[-1].index == lines[-1].index:
            line_1_ld = lines[0].get_ld(self.cd)
            line_2_ld = lines[-1].get_ld(self.cd)
            line_bc = compare_ld_beichi(line_1_ld, line_2_ld, line_direction)
            return LINE_FORM_INFOS(
                lines=lines, direction=line_direction, line_num=line_num, zss=zss,
                form_type='盘整', is_bc_line=line_bc, form_qs='盘整',
                form_level=round(zss[0].line_num / 3, 2)
            )

        # 只有一个中枢，但是起始或结束不在开始与结束位置，中枢的前后两段进行力度比较
        if len(zss) == 1:
            line_1_ld = {'macd': query_macd_ld(self.cd, lines[0].start, zss[0].start)}
            line_2_ld = {'macd': query_macd_ld(self.cd, zss[0].end, lines[-1].end)}
            zs_pre_line_num = zss[0].lines[1].index - lines[0].index
            zs_next_line_num = lines[-1].index - zss[0].lines[-2].index
            line_bc = compare_ld_beichi(line_1_ld, line_2_ld, line_direction)
            return LINE_FORM_INFOS(
                lines=lines, direction=line_direction, line_num=line_num, zss=zss,
                form_type='盘整', is_bc_line=line_bc, form_qs='盘整',
                form_level=round(zss[0].line_num / 3, 2),
                infos={'zs_pre_line_num': zs_pre_line_num, 'zs_next_line_num': zs_next_line_num}
            )

        # 多个中枢，首先判断是否形成趋势（中枢与中枢之间没有重叠）
        zs_qs = True
        for i in range(1, len(zss)):
            if line_direction == 'up':
                if zss[i - 1].gg >= zss[i].dd:
                    zs_qs = False
                    break
            if line_direction == 'down':
                if zss[i - 1].dd < zss[i].gg:
                    zs_qs = False
                    break

        if zs_qs:
            # 如果是趋势，比较最后一个中枢前后两段
            line_1_ld = {'macd': query_macd_ld(self.cd, zss[-2].end, zss[-1].start)}
            line_2_ld = {'macd': query_macd_ld(self.cd, zss[-1].end, lines[-1].end)}
            zs_pre_line_num = zss[-1].lines[0].index - zss[-2].lines[-1].index + 1
            zs_next_line_num = lines[-1].index - zss[-1].lines[-2].index
            line_bc = compare_ld_beichi(line_1_ld, line_2_ld, line_direction)
            return LINE_FORM_INFOS(
                lines=lines, direction=line_direction, line_num=line_num, zss=zss,
                form_type='趋势', is_bc_line=line_bc, form_qs='趋势',
                form_level=round(zss[-1].line_num / 3, 2),
                infos={
                    'zs_pre_line_num': zs_pre_line_num, 'zs_next_line_num': zs_next_line_num,
                    'zs_pre_level': round(zss[-2].line_num / 3, 2), 'zs_next_level': round(zss[-1].line_num / 3, 2)
                }
            )

        # TODO 最后剩下的就是中枢扩展的情况了

        return None
