from .apps import login_required
from django.shortcuts import render

from chanlun import rd, zixuan
from . import utils


@login_required
def index_show(request):
    """
    定时任务配置
    """
    task_names = [
        {'task_name': 'a_1', 'market_type': 'a'},
        {'task_name': 'a_2', 'market_type': 'a'},
        {'task_name': 'hk', 'market_type': 'hk'},
        {'task_name': 'us', 'market_type': 'us'},
        {'task_name': 'futures', 'market_type': 'futures'},
        {'task_name': 'currency', 'market_type': 'currency'},
    ]
    res_obj = {}
    task_configs = {}
    for task in task_names:
        task_configs[task['task_name']] = rd.task_config_query(task['task_name'], False)
        zx = zixuan.ZiXuan(task['market_type'])
        task_configs[task['task_name']]['zx_list'] = zx.zixuan_list

    res_obj['nav'] = 'tasks'
    res_obj['task_names'] = task_names
    res_obj['task_configs'] = task_configs
    return render(request, 'charts/tasks/index.html', res_obj)


@login_required
def task_save(request):
    """
    定时任务保存
    """
    task_name = request.POST.get('task_name')
    task_config = {
        'is_run': request.POST.get('is_run', '0'),
        'interval_minutes': request.POST.get('interval_minutes', '5`'),
        'zixuan': request.POST.get('zixuan', ''),
        'frequencys': request.POST.get('frequencys', ''),
        'check_beichi': request.POST.get('check_beichi', ''),
        'check_mmd': request.POST.get('check_mmd', ''),
        'check_beichi_xd': request.POST.get('check_beichi_xd', ''),
        'check_mmd_xd': request.POST.get('check_mmd_xd', ''),
        'is_send_msg': request.POST.get('is_send_msg', '0'),
    }
    rd.task_config_save(task_name, task_config)
    return utils.json_response('OK')
