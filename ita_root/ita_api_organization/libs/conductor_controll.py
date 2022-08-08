#   Copyright 2022 NEC Corporation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
from unittest import result
from flask import g

from common_libs.common import *  # noqa: F403
from common_libs.loadtable import *

from libs.organization_common import check_menu_info
from libs.organization_common import check_auth_menu
from libs.organization_common import check_sheet_type

import uuid
from pprint import pprint

def conductor_maintenance(objdbca, menu, conductor_data, target_uuid=''):
    """
        メニューのレコード登録/更新(更新/廃止/復活)
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            parameter:パラメータ  {}
            target_uuid: 対象レコードID UUID
            lang: 言語情報 ja / en
        RETRUN:
            statusCode, {}, msg
    """

    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)
    if privilege == '2':
        status_code = "401-00001"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)
    
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)

    objmenu = load_table.loadTable(objdbca, menu)
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)

    # conductor_data load_table用パラメータ加工
    conductor_class_id = conductor_data.get('conductor').get('id')
    conductor_name = conductor_data.get('conductor').get('conductor_name')
    last_update_date_time = conductor_data.get('conductor').get('last_update_date_time')
    note = conductor_data.get('conductor').get('note')
    if target_uuid == '':
        conductor_class_id = str(uuid.uuid4())
        if 'conductor' in conductor_data:
            conductor_data['conductor']['id'] = conductor_class_id
            conductor_data['conductor']['last_update_date_time'] = None
        
        tmp_parameter = {}
        tmp_parameter.setdefault('conductor_class_id', conductor_class_id)
        tmp_parameter.setdefault('conductor_name', conductor_name)
        tmp_parameter.setdefault('setting', conductor_data)
        tmp_parameter.setdefault('remarks', note)

        parameter = {}
        parameter.setdefault('file', {})
        parameter.setdefault('parameter', tmp_parameter)
        parameter.setdefault('type', 'Register')
        target_uuid = conductor_class_id
    else:
        if 'conductor' in conductor_data:
            conductor_data['conductor']['id'] = target_uuid
            conductor_data['conductor']['last_update_date_time'] = None
        tmp_parameter = {}
        tmp_parameter.setdefault('conductor_class_id', target_uuid)
        tmp_parameter.setdefault('conductor_name', conductor_name)
        tmp_parameter.setdefault('setting', conductor_data) 
        tmp_parameter.setdefault('remarks', note)
        tmp_parameter.setdefault('last_update_date_time', last_update_date_time)

        parameter = {}
        parameter.setdefault('file', {})
        parameter.setdefault('parameter', tmp_parameter)
        parameter.setdefault('type', 'Update')

    status_code, result, msg = objmenu.rest_maintenance(parameter, target_uuid)

    if status_code != '000-00000':
        if status_code is None:
            status_code = '999-99999'
        elif len(status_code) == 0:
            status_code = '999-99999'
        if isinstance(msg,list):
            log_msg_args = msg
            api_msg_args = msg
        else:
            log_msg_args = [msg]
            api_msg_args = [msg] 
        raise AppException(status_code, log_msg_args, api_msg_args)

    return result


def get_conductor_data(objdbca, menu, conductor_class_id):
    """
        メニューのレコード登録/更新(更新/廃止/復活)
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            parameter:パラメータ  {}
            target_uuid: 対象レコードID UUID
            lang: 言語情報 ja / en
        RETRUN:
            statusCode, {}, msg
    """

    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)
    
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)

    objmenu = load_table.loadTable(objdbca, menu)
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)

    mode = "nomal"
    filter_parameter = {"conductor_class_id": {"LIST": [conductor_class_id]}}
    status_code, tmp_result, msg = objmenu.rest_filter(filter_parameter, mode)
    if status_code != '000-00000':
        if status_code is None:
            status_code = '999-99999'
        elif len(status_code) == 0:
            status_code = '999-99999'
        if isinstance(msg, list):
            log_msg_args = msg
            api_msg_args = msg
        else:
            log_msg_args = [msg]
            api_msg_args = [msg] 
        raise AppException(status_code, log_msg_args, api_msg_args)

    if len(tmp_result) == 1:
        tmp_data = tmp_result[0].get('parameter')
        tmp_conductor_class_id = tmp_data.get('conductor_class_id')
        tmp_remarks = tmp_data.get('remarks')
        tmp_last_update_date_time = tmp_data.get('last_update_date_time')

        result = tmp_data.get('setting')
        result['conductor']['id'] = tmp_conductor_class_id
        result['conductor']['note'] = tmp_remarks
        result['conductor']['last_update_date_time'] = tmp_last_update_date_time
    else:
        result = {}

    return result
