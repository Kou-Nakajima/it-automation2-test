import pprint
import json
from common_libs.conductor.classes.util import ConductorCommonLibs

from flask import g

def external_valid_before(objdbca, objtable, option):
    # print('xxxxx-1001')
    # print('external_valid_before')
    retBool = True
    msg = ''
    #  pprint.pprint(option)
    return retBool, msg, option,

def external_valid_after(objdbca, objtable, option):
    # print('xxxxx-1001')
    # print('external_valid_after')
    retBool = True
    msg = ''
    #  pprint.pprint(option)
    return retBool, msg, option,

def external_valid_menu_before(objdbca, objtable, option):
    # print('xxxxx-1001')
    # print('external_valid_menu_before')
    retBool = True
    msg = ''
    option = convert_conductor_ver_1(option)
    # pprint.pprint(option)

    target_rest_name = 'setting'
    entry_parameter = option.get('entry_parameter')
    tmp_parameter = entry_parameter.get('parameter')
    conductor_data = json.loads(tmp_parameter.get(target_rest_name))
    CCL = ConductorCommonLibs()
    result = CCL.chk_format(conductor_data)
    if result[0] is False:
        status_code = '200-00201'
        msg_args = ["{}".format(result)]
        msg = g.appmsg.get_api_message(status_code, msg_args)
        retBool = result[0]

    return retBool, msg, option,

def external_valid_menu_after(objdbca, objtable, option):
    # print('xxxxx-1001')
    # print('external_valid_menu_after')
    retBool = True
    msg = ''
    #  pprint.pprint(option)
    return retBool, msg, option,

def convert_conductor_ver_1(option):
    target_rest_name = 'setting'
    entry_parameter = option.get('entry_parameter')
    tmp_parameter = entry_parameter.get('parameter')
    tmp_setting = tmp_parameter.get(target_rest_name)
    if tmp_setting is not None:
        tmp_setting = tmp_setting.replace("LUT4U", "last_update_date_time")
        tmp_setting = tmp_setting.replace("SKIP_FLAG", "skip_flag")
        tmp_setting = tmp_setting.replace("CALL_CONDUCTOR_ID", "call_conductor_id")
        tmp_setting = tmp_setting.replace("OPERATION_NO_IDBH", "operation_id")
        tmp_setting = tmp_setting.replace("PATTERN_ID", "movement_id")
        tmp_setting = tmp_setting.replace("OPERATION_NO_IDBH", "operation_id")
        tmp_setting = tmp_setting.replace("ORCHESTRATOR_ID", "orchestra_id")
        tmp_setting = tmp_setting.replace("CONDUCTOR_NAME", "Name")
        tmp_setting = tmp_setting.replace("OPERATION_NAME", "operation_name")
        tmp_setting = tmp_setting.replace("END_TYPE", "end_type")
        json_setting = json.loads(tmp_setting)
        if 'ACCESS_AUTH' in json_setting['conductor']:
            del json_setting['conductor']['ACCESS_AUTH']
        if 'NOTICE_INFO' in json_setting['conductor']:
            del json_setting['conductor']['NOTICE_INFO']
        tmp_setting = json.dumps(json_setting, ensure_ascii=False)
    option['entry_parameter']['parameter']['setting'] = tmp_setting
    # pprint.pprint(option)
    return option
