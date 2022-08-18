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


from flask import g  # noqa: F401

from common_libs.common import *  # noqa: F403
from common_libs.loadtable import *  # noqa: F403

from libs.organization_common import check_menu_info  # noqa: F401
from libs.organization_common import check_auth_menu  # noqa: F401
from libs.organization_common import check_sheet_type  # noqa: F401

from common_libs.conductor.classes.util import ConductorCommonLibs  # noqa: F401
from common_libs.conductor.classes.exec_util import ConductorExecuteLibs  # noqa: F401

import uuid  # noqa: F401


def conductor_maintenance(objdbca, menu, conductor_data, target_uuid=''):
    """
        Conductorの登録/更新
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            conductor_data:Conductor設定  {}
            target_uuid: 対象レコードID UUID
        RETRUN:
            data
    """
    msg = ''
    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)
    if privilege == '2':
        status_code = "401-00001"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    objmenu = load_table.loadTable(objdbca, menu)  # noqa: F405
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
    try:
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

        ###
        # conductor_data バリデーション処理
        ###
        # raise Exception()

    except Exception:
        # 499-00801
        status_code = "499-00801"
        log_msg_args = []
        api_msg_args = []
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    status_code, result, msg = objmenu.rest_maintenance(parameter, target_uuid)

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
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def get_conductor_data(objdbca, menu, conductor_class_id):
    """
        Conductorクラスの取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            conductor_class_id:ConductorクラスID string
        RETRUN:
            data
    """

    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)  # noqa: F841
    
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    objmenu = load_table.loadTable(objdbca, menu)  # noqa: F405
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    try:
        mode = "nomal"
        filter_parameter = {"conductor_class_id": {"LIST": [conductor_class_id]}}
        status_code, tmp_result, msg = objmenu.rest_filter(filter_parameter, mode)

        if len(tmp_result) == 1:
            tmp_data = tmp_result[0].get('parameter')
            tmp_conductor_class_id = tmp_data.get('conductor_class_id')
            tmp_remarks = tmp_data.get('remarks')
            tmp_last_update_date_time = tmp_data.get('last_update_date_time')

            result = tmp_data.get('setting')
            result['conductor']['id'] = tmp_conductor_class_id
            result['conductor']['note'] = tmp_remarks
            result['conductor']['last_update_date_time'] = tmp_last_update_date_time

        elif len(tmp_result) == 0:
            raise Exception()

    except Exception:
        status_code = "499-00802"
        log_msg_args = [conductor_class_id]
        api_msg_args = [conductor_class_id]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def get_conductor_data_execute(objdbca, menu, conductor_class_id):
    """
        Conductorクラスの取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            conductor_class_id:ConductorクラスID string
        RETRUN:
            data
    """
    menu = 'conductor_class_edit'
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    objmenu = load_table.loadTable(objdbca, menu)  # noqa: F405
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    try:
        mode = "nomal"
        filter_parameter = {"conductor_class_id": {"LIST": [conductor_class_id]}}
        status_code, tmp_result, msg = objmenu.rest_filter(filter_parameter, mode)

        if len(tmp_result) == 1:
            tmp_data = tmp_result[0].get('parameter')
            tmp_conductor_class_id = tmp_data.get('conductor_class_id')
            tmp_remarks = tmp_data.get('remarks')
            tmp_last_update_date_time = tmp_data.get('last_update_date_time')

            result = tmp_data.get('setting')
            result['conductor']['id'] = tmp_conductor_class_id
            result['conductor']['note'] = tmp_remarks
            result['conductor']['last_update_date_time'] = tmp_last_update_date_time

        elif len(tmp_result) == 0:
            raise Exception()

    except Exception:
        status_code = "499-00802"
        log_msg_args = [conductor_class_id]
        api_msg_args = [conductor_class_id]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def get_conductor_execute_class_info(objdbca, menu):
    """
        Conductor基本情報
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
        RETRUN:
            statusCode, {}, msg
    """
    menu = 'conductor_class_edit'
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    objmenu = load_table.loadTable(objdbca, menu)  # noqa: F405
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
    
    try:
        result = get_conductor_class_info_data(objdbca)
    except Exception:
        status_code = "499-00803"
        log_msg_args = []
        api_msg_args = []
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def get_conductor_class_info(objdbca, menu):
    """
        Conductor基本情報
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
        RETRUN:
            statusCode, {}, msg
    """

    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)  # noqa: F841
    
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    objmenu = load_table.loadTable(objdbca, menu)  # noqa: F405
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
    
    try:
        result = get_conductor_class_info_data(objdbca)
    except Exception:
        status_code = "499-00803"
        log_msg_args = []
        api_msg_args = []
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def get_conductor_class_info_data(objdbca, mode=""):
    """
        Conductor基本情報の取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
        RETRUN:
            statusCode, {}, msg
    """
    try:
        # 対象メニューのload_table生成(conductor_instance_list,conductor_node_instance_list,movement_list)
        c_menu = 'conductor_instance_list'
        cc_menu = 'conductor_class_edit'
        n_menu = 'conductor_node_instance_list'
        m_menu = 'movement_list'
        objconductor = load_table.loadTable(objdbca, c_menu)  # noqa: F405
        objnode = load_table.loadTable(objdbca, n_menu)  # noqa: F405
        objmovement = load_table.loadTable(objdbca, m_menu)  # noqa: F405
        objcclass = load_table.loadTable(objdbca, cc_menu)  # noqa: F405

        if (objconductor.get_objtable() is False or
                objnode.get_objtable() is False or
                objmovement.get_objtable() is False or
                objcclass.get_objtable() is False):
            raise Exception()

        objmenus = {
            "objconductor": objconductor,
            "objnode": objnode,
            "objmovement": objmovement,
            "objcclass": objcclass
        }

        objCexec = ConductorExecuteLibs(objdbca, '', objmenus)
        result = objCexec.get_class_info_data(mode)
    
    except Exception:
        status_code = "499-00803"
        log_msg_args = []
        api_msg_args = []
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def conductor_execute(objdbca, menu, parameter):
    """
        Conductor実行
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            parameter:パラメータ  {}
        RETRUN:
            data
    """

    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)
    if privilege == '2':
        status_code = "401-00001"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['15']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    try:

        conductor_class_id = parameter.get('conductor_class_id')
        operation_id = parameter.get('operation_id')
        schedule_date = parameter.get('schedule_date')

        # 対象メニューのload_table生成(conductor_instance_list,conductor_node_instance_list,movement_list)
        c_menu = 'conductor_instance_list'
        cc_menu = 'conductor_class_edit'
        n_menu = 'conductor_node_instance_list'
        m_menu = 'movement_list'
        objconductor = load_table.loadTable(objdbca, c_menu)  # noqa: F405
        objnode = load_table.loadTable(objdbca, n_menu)  # noqa: F405
        objmovement = load_table.loadTable(objdbca, m_menu)  # noqa: F405
        objcclass = load_table.loadTable(objdbca, cc_menu)  # noqa: F405

        if (objconductor.get_objtable() is False or
                objnode.get_objtable() is False or
                objmovement.get_objtable() is False or
                objcclass.get_objtable() is False):
            raise Exception()
        
        objmenus = {
            "objconductor": objconductor,
            "objnode": objnode,
            "objmovement": objmovement,
            "objcclass": objcclass
        }

        objCexec = ConductorExecuteLibs(objdbca, menu, objmenus)
        create_parameter = objCexec.create_execute_register_parameter(parameter)
        if create_parameter[0] != '000-00000':
            raise Exception()
    except Exception:
        status_code = "499-00804"
        log_msg_args = [conductor_class_id, operation_id, schedule_date]
        api_msg_args = [conductor_class_id, operation_id, schedule_date]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
    
    try:
        # conducror_instance_id発番、load_table用パラメータ
        conductor_parameter = create_parameter[1].get('conductor')
        node_parameters = create_parameter[1].get('node')
        conductor_instance_id = create_parameter[1].get('conductor_instance_id')
        
        status_code = "000-00000"
        
        # トランザクション開始
        objdbca.db_transaction_start()

        # 対象メニューのテーブルと「ロック対象テーブル」を昇順でロック
        locktable_list = objconductor.get_locktable()
        if locktable_list is not None:
            tmp_result = objdbca.table_lock([locktable_list])
        else:
            tmp_result = objdbca.table_lock([objconductor.get_table_name(), objnode.get_table_name()])  # noqa: F841

        # conductor instanceテーブルへのレコード追加
        iem_result = objCexec.conductor_instance_exec_maintenance(conductor_parameter)
        if iem_result[0] is not True:
            raise Exception()
        # node instanceテーブルへのレコード追加
        iem_result = objCexec.node_instance_exec_maintenance(node_parameters)
        if iem_result[0] is not True:
            raise Exception()

        objdbca.db_transaction_end(True)

    except Exception:
        # ロールバック トランザクション終了
        objdbca.db_transaction_end(False)
        status_code = "499-00804"
        log_msg_args = [conductor_class_id, operation_id, schedule_date]
        api_msg_args = [conductor_class_id, operation_id, schedule_date]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
        
    result = {
        "conductor_instance_id": conductor_instance_id
    }

    return result


def get_conductor_info(objdbca, menu, conductor_instance_id):
    """
        Conductor基本情報の取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
        RETRUN:
            statusCode, {}, msg
    """
    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)  # noqa: F841
    
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    objmenu = load_table.loadTable(objdbca, menu)  # noqa: F405
    if objmenu.get_objtable() is False:
        status_code = "401-00003"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
    
    try:
        # 対象メニューのload_table生成(conductor_instance_list,conductor_node_instance_list,movement_list)
        c_menu = 'conductor_instance_list'
        cc_menu = 'conductor_class_edit'
        n_menu = 'conductor_node_instance_list'
        m_menu = 'movement_list'
        objconductor = load_table.loadTable(objdbca, c_menu)  # noqa: F405
        objnode = load_table.loadTable(objdbca, n_menu)  # noqa: F405
        objmovement = load_table.loadTable(objdbca, m_menu)  # noqa: F405
        objcclass = load_table.loadTable(objdbca, cc_menu)  # noqa: F405

        if (objconductor.get_objtable() is False or
                objnode.get_objtable() is False or
                objmovement.get_objtable() is False or
                objcclass.get_objtable() is False):
            raise Exception()

        objmenus = {
            "objconductor": objconductor,
            "objnode": objnode,
            "objmovement": objmovement,
            "objcclass": objcclass
        }

        objCexec = ConductorExecuteLibs(objdbca, '', objmenus)
        result = objCexec.get_instance_info_data(conductor_instance_id)

    except Exception:
        status_code = "499-00805"
        log_msg_args = [conductor_instance_id]
        api_msg_args = [conductor_instance_id]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def get_conductor_instance_data(objdbca, menu, conductor_instance_id):
    """
        Conductorクラスの取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            conductor_class_id:ConductorクラスID string
        RETRUN:
            data
    """

    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)  # noqa: F841
    
    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['14', '15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    try:
        # 対象メニューのload_table生成(conductor_instance_list,conductor_node_instance_list,movement_list)
        c_menu = 'conductor_instance_list'
        cc_menu = 'conductor_class_edit'
        n_menu = 'conductor_node_instance_list'
        m_menu = 'movement_list'
        objconductor = load_table.loadTable(objdbca, c_menu)  # noqa: F405
        objnode = load_table.loadTable(objdbca, n_menu)  # noqa: F405
        objmovement = load_table.loadTable(objdbca, m_menu)  # noqa: F405
        objcclass = load_table.loadTable(objdbca, cc_menu)  # noqa: F405

        if (objconductor.get_objtable() is False or
                objnode.get_objtable() is False or
                objmovement.get_objtable() is False or
                objcclass.get_objtable() is False):
            raise Exception()

        objmenus = {
            "objconductor": objconductor,
            "objnode": objnode,
            "objmovement": objmovement,
            "objcclass": objcclass
        }

        objCexec = ConductorExecuteLibs(objdbca, '', objmenus)
        result = objCexec.get_instance_data(conductor_instance_id)
    
    except Exception:
        status_code = "499-00806"
        log_msg_args = [conductor_instance_id]
        api_msg_args = [conductor_instance_id]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    return result


def conductor_execute_action(objdbca, menu, mode='', conductor_instance_id='', node_instance_id=''):
    """
        Conductor作業に対する個別処理(cancel,scram,relese)
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            menu:メニュー名 string
            mode: 処理種別 cancel,scram,relese
            conductor_instance_id:
        RETRUN:
            data
    """
    msg = ''
    # メニューに対するロール権限をチェック
    privilege = check_auth_menu(menu, objdbca)
    if privilege == '2':
        status_code = "401-00001"
        log_msg_args = [menu]
        api_msg_args = [menu]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    # 『メニュー-テーブル紐付管理』の取得とシートタイプのチェック
    sheet_type_list = ['15', '16']
    menu_table_link_record = check_sheet_type(menu, sheet_type_list, objdbca)  # noqa: F841

    try:
        if mode == '' or mode is None:
            raise Exception()

        # 対象メニューのload_table生成(conductor_instance_list,conductor_node_instance_list)
        c_menu = 'conductor_instance_list'
        n_menu = 'conductor_node_instance_list'
        objconductor = load_table.loadTable(objdbca, c_menu)  # noqa: F405
        objnode = load_table.loadTable(objdbca, n_menu)  # noqa: F405

        if (objconductor.get_objtable() is False or
                objnode.get_objtable() is False):
            raise Exception()
        
        objmenus = {
            "objconductor": objconductor,
            "objnode": objnode
        }
        objCexec = ConductorExecuteLibs(objdbca, '', objmenus, 'Update', conductor_instance_id)
    except Exception:
        status_code = "499-00807"
        log_msg_args = [mode, conductor_instance_id, node_instance_id]
        api_msg_args = [mode, conductor_instance_id, node_instance_id]
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
    
    try:
        status_code = "000-00000"
        msg_args = []
        # トランザクション開始
        objdbca.db_transaction_start()

        # 対象メニューのテーブルと「ロック対象テーブル」を昇順でロック
        locktable_list = objconductor.get_locktable()
        if locktable_list is not None:
            tmp_result = objdbca.table_lock([locktable_list])
        else:
            tmp_result = objdbca.table_lock([objconductor.get_table_name(), objnode.get_table_name()])  # noqa: F841

        # conductor instanceテーブルへのレコード追加
        action_result = objCexec.execute_action(mode, conductor_instance_id, node_instance_id)
        if action_result[0] is not True:
            status_code = action_result[1]
            msg_args = action_result[2]
            raise Exception()

        objdbca.db_transaction_end(True)
        
        if mode == 'cancel':
            msg_code = 'MSG-40001'
        elif mode == 'scram':
            msg_code = 'MSG-40002'
        elif mode == 'relese':
            msg_code = 'MSG-40003'
        msg = g.appmsg.get_api_message(msg_code, [conductor_instance_id, node_instance_id])

    except Exception:
        # ロールバック トランザクション終了
        objdbca.db_transaction_end(False)
        log_msg_args = msg_args
        api_msg_args = msg_args
        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

    result = msg

    return result
