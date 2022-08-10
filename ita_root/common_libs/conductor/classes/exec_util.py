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

from flask import g
from common_libs.common.dbconnect import DBConnectWs  # noqa: F401

from common_libs.common import *  # noqa: F403
from common_libs.loadtable import *  # noqa: F403

import json
import uuid
import copy
import textwrap



class ConductorExecuteLibs():
    """
        ConductorExecuteLibs
        COnductor作業関連
    """

    def __init__(self, objdbca, menu, objmenus, cmd_type='Register', target_uuid=''):

        # メニューID
        self.menu = menu
        
        # DB接続
        self.objdbca = objdbca

        # 環境情報
        self.lang = g.LANGUAGE
        
        # 各loadtableクラス
        self.objmenus = objmenus

        # 実行種別
        self.cmd_type = cmd_type

        # 対象conductorID
        self.target_uuid = target_uuid

    def get_class_info_data(self, mode=""):
        """
            Conductor基本情報の取得
            ARGS:
                mode: "" (list key:[{id,name}] and dict key:{id:name}) or "all"  dict key:{rest_key:db rows})
            RETRUN:
                statusCode, {}, msg
        """

        try:
            lang_upper = self.lang.upper()
            
            dict_target_table = {
                "conductor_status": {
                    "table_name": "T_COMN_CONDUCTOR_STATUS",
                    "pk": "STATUS_ID",
                    "name": "STATUS_NAME_" + lang_upper,
                },
                "node_status": {
                    "table_name": "T_COMN_CONDUCTOR_NODE_STATUS",
                    "pk": "STATUS_ID",
                    "name": "STATUS_NAME_" + lang_upper,
                },
                "node_type": {
                    "table_name": "T_COMN_CONDUCTOR_NODE",
                    "pk": "NODE_TYPE_ID",
                    "name": "NODE_TYPE_NAME"
                },
                "movement": {
                    "table_name": "T_COMN_MOVEMENT",
                    "sql": '',
                    "pk": "MOVEMENT_ID",
                    "name": "MOVEMENT_NAME",
                    "sortkey": "TAB_A.MOVEMENT_NAME",
                    "orc_id": "ORCHESTRA_ID",
                    "orc_name": "ORCHESTRA_NAME"
                },
                "orchestra": {
                    "table_name": "T_COMN_ORCHESTRA",
                    "pk": "ORCHESTRA_ID",
                    "name": "ORCHESTRA_NAME",
                },
                "operation": {
                    "table_name": "T_COMN_OPERATION",
                    "pk": "OPERATION_ID",
                    "name": "OPERATION_NAME",
                    "sortkey": "OPERATION_NAME",
                },
                "conductor": {
                    "table_name": "T_COMN_CONDUCTOR_CLASS",
                    "pk": "CONDUCTOR_CLASS_ID",
                    "name": "CONDUCTOR_NAME",
                    "sortkey": "CONDUCTOR_NAME",
                },
                "refresh_interval": {
                    "table_name": "T_COMN_CONDUCTOR_IF_INFO",
                    "pk": "CONDUCTOR_IF_INFO_ID",
                    "refresh_interval": "CONDUCTOR_REFRESH_INTERVAL",
                    "sortkey": "CONDUCTOR_IF_INFO_ID",
                }
            }

            movement_sql = textwrap.dedent("""
                SELECT `TAB_A`.*, `TAB_B`.*
                FROM `T_COMN_MOVEMENT` `TAB_A`
                LEFT JOIN `T_COMN_ORCHESTRA` TAB_B ON (`TAB_A`.`ITA_EXT_STM_ID` = `TAB_B`.`ORCHESTRA_ID`)
                WHERE `TAB_A`.`DISUSE_FLAG` = 0 AND `TAB_B`.`DISUSE_FLAG` = 0
            """).format().strip()
            dict_target_table['movement']['sql'] = movement_sql

            result = {}
            result.setdefault('list', {})
            result.setdefault('dict', {})
            for target_key, target_table_info in dict_target_table.items():
                table_name = target_table_info.get('table_name')
                sortkey = target_table_info.get('sortkey')
                if sortkey is None:
                    sortkey = 'DISP_SEQ'
                sql_str = target_table_info.get('sql')

                pk_col = target_table_info.get('pk')
                name_col = target_table_info.get('name')
                refresh_interval = target_table_info.get('refresh_interval')
                orc_id = target_table_info.get('orc_id')
                orc_name = target_table_info.get('orc_name')

                where_str = target_table_info.get('join')
                if where_str is None:
                    where_str = ' WHERE `DISUSE_FLAG` = 0 ORDER BY `' + sortkey + '` ASC '
                else:
                    sql_str = sql_str + ' ORDER BY `' + sortkey + '` ASC '

                if sql_str is None:
                    rows = self.objdbca.table_select(table_name, where_str, [])
                else:
                    rows = self.objdbca.sql_execute(sql_str, [])

                if mode == '':
                    if target_key == 'refresh_interval':
                        result.setdefault('refresh_interval', rows[0].get(refresh_interval))
                    else:
                        result['dict'].setdefault(target_key, {})
                        result['list'].setdefault(target_key, [])
                        for row in rows:
                            id = row.get(pk_col)
                            name = row.get(name_col)
                            tmp_arr = {"id": id, "name": name}
                            if target_key == 'movement':
                                orchestra_id = row.get(orc_id)
                                orchestra_name = row.get(orc_name)
                                tmp_arr = {"id": id, "name": name}
                                tmp_arr.setdefault("orchestra_id", orchestra_id)
                                tmp_arr.setdefault("orchestra_name", orchestra_name)
                            result['dict'][target_key].setdefault(id, name)
                            result['list'][target_key].append(tmp_arr)
                else:
                    result.setdefault(target_key, {})
                    for row in rows:
                        id = row.get(pk_col)
                        result[target_key].setdefault(id, row)
        except Exception:
            status_code = "200-00803"
            log_msg_args = []
            api_msg_args = []
            raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

        return result

    def create_execute_register_parameter(self, parameter, parent_conductor_instance_id=''):
        """
            Conductor実行(パラメータ生成)
            ARGS:
                parameter:パラメータ  {}
                parent_conductor_instance_id:親conductorID string
            RETRUN:
                data
        """
        
        try:
            status_code = "000-00000"
            lang = g.LANGUAGE
            lang_upper = lang.upper()
            
            conductor_instance_id = ''
            conductor_parameter = {}
            node_parameters = []

            objmovement = self.objmenus.get('objmovement')
            objcclass = self.objmenus.get('objcclass')

            # Conductor基本情報取得
            mode = "all"
            get_list_data = self.get_class_info_data(mode)
            # maintenance用パラメータ値生成
            # user_id = g.USER_ID
            user_name = g.USER_ID

            # conductor_instance_id 発番
            conductor_instance_id = str(uuid.uuid4())
            # parameterから取得
            conductor_class_id = parameter.get('conductor_class_id')
            operation_id = parameter.get('operation_id')
            schedule_date = parameter.get('schedule_date')
            conductor_data = parameter.get('conductor_data')

            # 上書き無し
            if conductor_data is None or conductor_data == '':
                conductor_data = json.loads(get_list_data.get('conductor').get(conductor_class_id).get('SETTING'))
            elif len(conductor_data) == 0:
                conductor_data = json.loads(get_list_data.get('conductor').get(conductor_class_id).get('SETTING'))

            if 'id' in conductor_data.get('conductor'):
                tmp_conductor_data_id = conductor_data.get('conductor').get('id')
            if conductor_class_id != tmp_conductor_data_id:
                raise Exception()

            # schedule_date 簡易チェック
            if schedule_date is not None:
                schedule_date_len = len(str(schedule_date))
                if schedule_date_len == 0:
                    schedule_date = None
                elif schedule_date_len == 19:
                    schedule_date = schedule_date + '.000000'

            # operation_id 簡易チェック
            if operation_id in get_list_data.get('operation'):
                operation_name = get_list_data.get('operation').get(operation_id).get('OPERATION_NAME')

            # conductor_class_id 簡易チェック, conductor名, 備考(作業実行画面優先)
            if conductor_class_id in get_list_data.get('conductor'):
                conductor_name = get_list_data.get('conductor').get(conductor_class_id).get('CONDUCTOR_NAME')
                conductor_remarks = get_list_data.get('conductor').get(conductor_class_id).get('NOTE')
                if 'note' in conductor_data.get('conductor'):
                    conductor_remarks = conductor_data.get('conductor').get('note')

            # Conductor初期ステータス設定(未実行,未実行(予約))
            if schedule_date is None:
                conductor_status_name = get_list_data.get('conductor_status').get('1').get('STATUS_NAME_' + lang_upper)
            else:
                conductor_status_name = get_list_data.get('conductor_status').get('2').get('STATUS_NAME_' + lang_upper)

            # Node初期ステータス設定(未実行,未実行(予約))
            node_status_name = get_list_data.get('node_status').get('1').get('STATUS_NAME_' + lang_upper)
                
            # 変更前(conductor_class)のconductor_data
            org_conductor_data = json.loads(get_list_data.get('conductor').get(conductor_class_id).get('SETTING'))

            # load_table用(conductor_instance_list)パラメータ生成
            c_parameter = {
                "conductor_instance_id": conductor_instance_id,
                "instance_source_class_id": conductor_class_id,
                "instance_source_class_name": conductor_name,
                "instance_source_settings": org_conductor_data,
                "instance_source_remarks": conductor_remarks,
                "class_settings": conductor_data,
                "operation_id": operation_id,
                "operation_name": operation_name,
                "execution_user": user_name,
                # "parent_conductor_instance_id": None,
                # "parent_conductor_instance_name": None,
                # "notice_info": None,
                # "notice_definition": None,
                "status_id": conductor_status_name,
                "abort_execute_flag": "0",
                "time_book": schedule_date,
                # "time_start": None,
                # "time_end": None,
                # "execution_log": None,
                # "notification_log": None,
                "remarks": conductor_remarks
                # "discard": 0,
                # "last_updated_user": user_id,
            }

            conductor_parameter = {
                'file': {},
                'parameter': c_parameter,
                "type": "Register"
            }
            # load_table用(conductor_node_instance_list)パラメータ生成
            # node用ベースパラメータ
            base_node_parameter = {
                "node_instance_id": None,
                "instance_source_node_name": None,
                "instance_source_remarks": None,
                "node_type": None,
                # "movement_type": None,
                # "instance_source_movement_id": None,
                # "instance_source_movement_name": None,
                # "instance_source_movement_info": None,
                # "instance_source_conductor_id": None,
                # "instance_source_conductor_name": None,
                # "instance_source_conductor_info": None,
                "conductor_instance_id": conductor_instance_id,
                "top_parent_id": None,
                "top_parent_name": None,
                "execution_id": None,
                "status_id": node_status_name,
                # "status_file": None,
                "released_flag": "0",
                "skip": "0",
                # "end_type": None,
                # "operation_id": None,
                # "operation_name": None,
                # "time_start": None,
                # "time_end": None,
                "remarks": None,
                "discard": "0",
                # "last_update_date_time": None,
                # "last_updated_user": None,
            }

            node_data = copy.deepcopy(conductor_data)
            node_parameters = []
            for node_name, node_info in node_data.items():
                # nodeのみ対象
                if 'node-' in node_name:
                    # 共通項目
                    n_parameter = copy.deepcopy(base_node_parameter)
                    node_type = node_info.get('type')
                    n_parameter["node_instance_id"] = str(uuid.uuid4())
                    n_parameter["instance_source_node_name"] = node_name
                    n_parameter["instance_source_remarks"] = node_info.get('note')
                    n_parameter["node_type"] = node_type
                    n_parameter["remarks"] = node_info.get('note')
                    
                    # Movement項目
                    if node_type in ["movement"]:
                        orchestra_id = get_list_data.get('orchestra').get(node_info.get('orchestra_id')).get('ORCHESTRA_NAME')
                        movement_id = node_info.get('movement_id')
                        movement_name = get_list_data.get('movement').get(movement_id).get('MOVEMENT_NAME')
                        filter_parameter = {"movement_id": {"LIST": [movement_id]}}
                        tmp_movement = objmovement.rest_filter(filter_parameter)
                        if tmp_movement[0] == '000-00000':
                            movement_class_json = tmp_movement[1][0]
                        else:
                            movement_class_json = []
                        n_parameter["movement_type"] = orchestra_id
                        n_parameter["instance_source_movement_id"] = movement_id
                        n_parameter["instance_source_movement_name"] = movement_name
                        n_parameter["instance_source_movement_info"] = movement_class_json
                    # Call項目
                    if node_type in ["call"]:
                        n_conductor_class_id = node_info.get('call_conductor_id')
                        n_conductor_class_name = get_list_data.get('conductor').get(n_conductor_class_id).get('CONDUCTOR_NAME')
                        filter_parameter = {"conductor_class_id": {"LIST": [n_conductor_class_id]}}
                        tmp_conductor = objcclass.rest_filter(filter_parameter)
                        if tmp_conductor[0] == '000-00000':
                            conductor_class_json = tmp_conductor[1][0]
                        else:
                            conductor_class_json = []
                        n_parameter["instance_source_conductor_id"] = n_conductor_class_id
                        n_parameter["instance_source_conductor_name"] = n_conductor_class_name
                        n_parameter["instance_source_conductor_info"] = conductor_class_json

                    # 個別OP,SKIP
                    if node_type in ["movement", "call"]:
                        skip_flag = node_info.get('skip_flag')
                        if skip_flag is not None:
                            n_parameter["operation_id"] = str(skip_flag)
                            
                        node_operation_id = node_info.get('operation_id')
                        if node_operation_id is not None:
                            if node_operation_id in get_list_data.get('operation'):
                                node_operation_name = get_list_data.get('operation').get(node_operation_id).get('OPERATION_NAME')
                        else:
                            node_operation_id = None
                            node_operation_name = None
                        n_parameter["operation_id"] = node_operation_id
                        n_parameter["operation_name"] = node_operation_name

                    # 終了タイプ
                    if node_type in ["end"]:
                        end_type = node_info.get('end_type')
                        if end_type is not None:
                            if end_type in get_list_data.get('conductor_status'):
                                end_type_name = get_list_data.get('conductor_status').get(end_type).get('STATUS_NAME_' + lang_upper)
                                n_parameter["end_type"] = end_type_name
                        else:
                            end_type_name = get_list_data.get('conductor_status').get('6').get('STATUS_NAME_' + lang_upper)
                            n_parameter["end_type"] = end_type_name

                    node_parameter = {
                        'file': {},
                        'parameter': copy.deepcopy(n_parameter),
                        "type": "Register"
                    }
                    node_parameters.append(node_parameter)
        except Exception:
            conductor_class_id = parameter.get('conductor_class_id')
            operation_id = parameter.get('operation_id')
            schedule_date = parameter.get('schedule_date')
            status_code = "200-00805"
            log_msg_args = [conductor_class_id, operation_id, schedule_date]
            api_msg_args = [conductor_class_id, operation_id, schedule_date]
            raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

        status_code = "000-00000"

        result = {
            "conductor_instance_id": conductor_instance_id,
            "conductor": conductor_parameter,
            "node": node_parameters
        }

        return status_code, result,

    def conductor_instance_exec_maintenance(self, conductor_parameter):
        """
            Conductor実行(conductorインスタンスの登録,更新)
            ARGS:
                conductor_parameter:conductorパラメータ
            RETRUN:
                bool, data
        """
        try:
            objconductor = self.objmenus.get('objconductor')
            # maintenance呼び出し
            tmp_result = objconductor.exec_maintenance(conductor_parameter, self.target_uuid, self.cmd_type)
            if tmp_result[0] is not True:
                return tmp_result
        except Exception:
            tmp_result = False,
        return tmp_result

    def node_instance_exec_maintenance(self, node_parameters):
        """
            Conductor実行(nodeインスタンスの登録,更新)
            ARGS:
                node_parameters:nodeパラメータ list
            RETRUN:
                bool, data
        """
        
        objnode = self.objmenus.get('objnode')

        for tmp_parameters in node_parameters:
            parameters = tmp_parameters
            target_uuid = ''
            if 'node_instance_id' in parameters.get('parameter'):
                target_uuid = parameters.get('parameter').get('node_instance_id')
                if target_uuid is None:
                    target_uuid = ''
            # maintenance呼び出し
            tmp_result = objnode.exec_maintenance(parameters, target_uuid, self.cmd_type)
            if tmp_result[0] is not True:
                return tmp_result
        return tmp_result

    def get_instance_info_data(self, conductor_instance_id, mode=''):
        """
            Conductor作業確認用の基本情報の取得
            ARGS:
                conductor_instance_id:作業id
                mode: "" (list key:[{id,name}] and dict key:{id:name}) or "all"  dict key:{rest_key:rows})
            RETRUN:
                {}
        """

        try:
            lang_upper = self.lang.upper()
                
            dict_target_table = {
                "conductor_status": {
                    "table_name": "T_COMN_CONDUCTOR_STATUS",
                    "pk": "STATUS_ID",
                    "name": "STATUS_NAME_" + lang_upper,
                },
                "node_status": {
                    "table_name": "T_COMN_CONDUCTOR_NODE_STATUS",
                    "pk": "STATUS_ID",
                    "name": "STATUS_NAME_" + lang_upper,
                },
                "node_type": {
                    "table_name": "T_COMN_CONDUCTOR_NODE",
                    "pk": "NODE_TYPE_ID",
                    "name": "NODE_TYPE_NAME"
                },
                "orchestra": {
                    "table_name": "T_COMN_ORCHESTRA",
                    "pk": "ORCHESTRA_ID",
                    "name": "ORCHESTRA_NAME",
                },
                "refresh_interval": {
                    "table_name": "T_COMN_CONDUCTOR_IF_INFO",
                    "pk": "CONDUCTOR_IF_INFO_ID",
                    "refresh_interval": "CONDUCTOR_REFRESH_INTERVAL",
                    "sortkey": "CONDUCTOR_IF_INFO_ID",
                }
            }

            result = {}
            result.setdefault('list', {})
            result.setdefault('dict', {})
            for target_key, target_table_info in dict_target_table.items():
                table_name = target_table_info.get('table_name')
                sortkey = target_table_info.get('sortkey')
                if sortkey is None:
                    sortkey = 'DISP_SEQ'
                sql_str = target_table_info.get('sql')

                pk_col = target_table_info.get('pk')
                name_col = target_table_info.get('name')
                refresh_interval = target_table_info.get('refresh_interval')
                orc_id = target_table_info.get('orc_id')
                orc_name = target_table_info.get('orc_name')

                where_str = target_table_info.get('join')
                if where_str is None:
                    where_str = ' WHERE `DISUSE_FLAG` = 0 ORDER BY `' + sortkey + '` ASC '
                else:
                    sql_str = sql_str + ' ORDER BY `' + sortkey + '` ASC '

                if sql_str is None:
                    rows = self.objdbca.table_select(table_name, where_str, [])
                else:
                    rows = self.objdbca.sql_execute(sql_str, [])

                if mode == '':
                    if target_key == 'refresh_interval':
                        result.setdefault('refresh_interval', rows[0].get(refresh_interval))
                    else:
                        result['dict'].setdefault(target_key, {})
                        result['list'].setdefault(target_key, [])
                        for row in rows:
                            id = row.get(pk_col)
                            name = row.get(name_col)
                            tmp_arr = {"id": id, "name": name}
                            if target_key == 'movement':
                                orchestra_id = row.get(orc_id)
                                orchestra_name = row.get(orc_name)
                                tmp_arr = {"id": id, "name": name}
                                tmp_arr.setdefault("orchestra_id", orchestra_id)
                                tmp_arr.setdefault("orchestra_name", orchestra_name)
                            result['dict'][target_key].setdefault(id, name)
                            result['list'][target_key].append(tmp_arr)
                else:
                    result.setdefault(target_key, {})
                    for row in rows:
                        id = row.get(pk_col)
                        result[target_key].setdefault(id, row)

            # 作業に関連する、Conductor、Movement、Operationのリスト
            objconductor = self.objmenus.get('objconductor')
            objnode = self.objmenus.get('objnode')

            # conductor instanceから一覧生成
            filter_parameter = {
                "conductor_instance_id": {"LIST": [conductor_instance_id]}
            }
            result['dict'].setdefault('conductor', {})
            result['list'].setdefault('conductor', [])
            result['dict'].setdefault('operation', {})
            result['list'].setdefault('operation', [])
            result['dict'].setdefault('movement', {})
            result['list'].setdefault('movement', [])

            result_ci_filter = objconductor.rest_filter(filter_parameter)
            if result_ci_filter[0] == '000-00000':
                for tmp_ci in result_ci_filter[1]:
                    ci_p = tmp_ci.get('parameter')
                    # conductor
                    id = ci_p.get('instance_source_class_id')
                    name = ci_p.get('instance_source_class_name')
                    tmp_arr = {"id": id, "name": name}
                    result['dict']['conductor'].setdefault(id, name)
                    result['list']['conductor'].append(tmp_arr)
                    p_id = ci_p.get('parent_conductor_instance_id')
                    p_name = ci_p.get('parent_conductor_instance_name')
                    if p_id is not None and p_name is not None:
                        tmp_arr = {"id": p_id, "name": p_name}
                        result['dict']['conductor'].setdefault(p_id, p_name)
                        result['list']['conductor'].append(tmp_arr)

                    # operation
                    id = ci_p.get('operation_id')
                    name = ci_p.get('operation_name')
                    tmp_arr = {"id": id, "name": name}
                    result['dict']['operation'].setdefault(id, name)
                    result['list']['operation'].append(tmp_arr)

            # node instanceからクラス一覧生成
            filter_parameter = {
                "conductor_instance_id": {"LIST": [conductor_instance_id]}
            }
            result_ni_filter = objnode.rest_filter(filter_parameter)
            if result_ni_filter[0] == '000-00000':
                for tmp_ni in result_ni_filter[1]:
                    ni_p = tmp_ni.get('parameter')

                    # movement
                    id = ni_p.get('instance_source_movement_id')
                    name = ni_p.get('instance_source_movement_name')
                    if id is not None and name is not None:
                        tmp_arr = {"id": id, "name": name}
                        result['dict']['movement'].setdefault(id, name)
                        result['list']['movement'].append(tmp_arr)
                        
                    # conductor
                    id = ni_p.get('instance_source_conductor_id')
                    name = ni_p.get('instance_source_conductor_name')
                    if id is not None and name is not None:
                        tmp_arr = {"id": id, "name": name}
                        result['dict']['conductor'].setdefault(id, name)
                        result['list']['conductor'].append(tmp_arr)

                    # operation
                    id = ni_p.get('operation_id')
                    name = ni_p.get('operation_name')
                    if id is not None and name is not None:
                        tmp_arr = {"id": id, "name": name}
                        result['dict']['operation'].setdefault(id, name)
                        result['list']['operation'].append(tmp_arr)
                    
        except Exception:
            status_code = "200-00803"
            log_msg_args = []
            api_msg_args = []
            raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

        return result

    def get_instance_data(self, conductor_instance_id):
        """
            対象のConductor作業の設定、ステータス取得
            ARGS:
                conductor_instance_id:作業id
            RETRUN:
                {}
        """

        try:

            result = {}
            result.setdefault('conductor_class', {})
            result.setdefault('conductor', {})
            result.setdefault('node', {})
            
            objconductor = self.objmenus.get('objconductor')
            objnode = self.objmenus.get('objnode')

            instance_info_data = self.get_instance_info_data(conductor_instance_id)
            
            conductor_status = {}
            class_settings = {}
            node_status = {}

            jump_menu_list = {
                "1": "check_operation_status",
                "2": "check_operation_status",
                "3": "check_operation_status"
            }

            # conductor
            filter_parameter = {
                "conductor_instance_id": {"LIST": [conductor_instance_id]}
            }
            result_ci_filter = objconductor.rest_filter(filter_parameter)
            if result_ci_filter[0] == '000-00000':
                if len(result_ci_filter[1]) == 1:
                    for tmp_ci in result_ci_filter[1]:
                        ci_p = tmp_ci.get('parameter')
                        class_settings = ci_p.get('class_settings')
                        conductor_status = {
                            "conductor_instance_id": ci_p.get('conductor_instance_id'),
                            "conductor_name": ci_p.get('instance_source_class_name'),
                            "status_id": ci_p.get('status_id'),
                            "execution_user": ci_p.get('execution_user'),
                            "abort_execute_flag": ci_p.get('abort_execute_flag'),
                            "operation_id": ci_p.get('operation_id'),
                            "operation_name": ci_p.get('operation_name'),
                            "time_book": ci_p.get('time_book'),
                            "time_start": ci_p.get('time_start'),
                            "time_end": ci_p.get('time_end'),
                            "execution_log": ci_p.get('execution_log'),
                            "remarks": ci_p.get('remarks'),
                        }

            # node instanceからクラス一覧生成
            filter_parameter = {
                "conductor_instance_id": {"LIST": [conductor_instance_id]}
            }
            result_ni_filter = objnode.rest_filter(filter_parameter)
            if result_ni_filter[0] == '000-00000':
                for tmp_ni in result_ni_filter[1]:
                    ni_p = tmp_ni.get('parameter')
                    node_name = ni_p.get('instance_source_node_name')
                    # 各作業確認のメニュー
                    jump_menu_id = None
                    tmp_orchestra = instance_info_data.get('dict').get('orchestra')
                    movement_type = ni_p.get('movement_type')
                    if movement_type is not None:
                        tmp_orchestra_id = [k for k, v in tmp_orchestra.items() if v == movement_type]
                        tmp_orchestra_id = tmp_orchestra_id[0]
                        jump_menu_id = jump_menu_list.get(tmp_orchestra_id)

                    tmp_node_status = {
                        "node_instance_id": ni_p.get('node_instance_id'),
                        "node_name": ni_p.get('instance_source_node_name'),
                        "node_type": ni_p.get('node_type'),
                        "status_id": ni_p.get('status_id'),
                        "status_file": ni_p.get('status_file'),
                        "skip": ni_p.get('skip'),
                        "remarks": ni_p.get('remarks'),
                        "time_start": ni_p.get('time_start'),
                        "time_end": ni_p.get('time_end'),
                        "operation_id": ni_p.get('operation_id'),
                        "operation_name": ni_p.get('operation_name'),
                        "jump": {
                            "menu_id": jump_menu_id,
                            "execution_id": ni_p.get('execution_id'),
                        }
                    }
                    node_status.setdefault(node_name, tmp_node_status)

            result['conductor_class'] = class_settings
            result['conductor'] = conductor_status
            result['node'] = node_status
            
        except Exception:
            status_code = "200-00803"
            log_msg_args = []
            api_msg_args = []
            raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

        return result

    def execute_action(self, mode='', conductor_instance_id='', node_instance_id=''):
        """
            Conductor作業に対する個別処理(cancel,scram,relese)
            ARGS:
                mode: "" (list key:[{id,name}] and dict key:{id:name}) or "all"  dict key:{rest_key:rows})
                conductor_instance_id: string
                node_instance_id: string
            RETRUN:
                retBool, status_code, msg_args,
        """

        try:
            retBool = True
            status_code = '000-00000'
            msg_args = []
    
            instance_info_data = self.get_instance_info_data(conductor_instance_id)
            
            objconductor = self.objmenus.get('objconductor')
            objnode = self.objmenus.get('objnode')
            tmp_parameter = {}
            
            if conductor_instance_id != '':
                filter_parameter = {
                    "conductor_instance_id": {"LIST": [conductor_instance_id]}
                }
                result_ci_filter = objconductor.rest_filter(filter_parameter)
                if result_ci_filter[0] == '000-00000':
                    if len(result_ci_filter[1]) == 1:
                        ci_p = result_ci_filter[1][0].get('parameter')
                        ci_last_update_date_time = ci_p.get('last_update_date_time')
                        ci_status_id = ci_p.get('status_id')
                        ci_abort_execute_flag = ci_p.get('abort_execute_flag')
            if node_instance_id != '':
                # node instanceからクラス一覧生成
                filter_parameter = {
                    "conductor_instance_id": {"LIST": [conductor_instance_id]},
                    "node_instance_id": {"LIST": [node_instance_id]}
                    # "node_type": {"LIST": ["pause"]},
                }
                result_ni_filter = objnode.rest_filter(filter_parameter)
                
                if result_ni_filter[0] == '000-00000':
                    if len(result_ni_filter[1]) == 1:
                        ni_p = result_ni_filter[1][0].get('parameter')
                        print(ni_p)
                        ni_released_flag = ni_p.get('released_flag')
                        ni_node_type = ni_p.get('node_type')
                        ni_last_update_date_time = ni_p.get('last_update_date_time')
                        ni_status_id = ni_p.get('status_id')

            if mode == 'cancel':
                # ステータス変更(未実行(予約)→予約取消)
                status_id = instance_info_data.get('dict').get('conductor_status').get('10')
                cancel_accept_status = instance_info_data.get('dict').get('conductor_status').get('2')
                # 未実行(予約)の時のみ
                if ci_status_id == cancel_accept_status:
                    tmp_parameter.setdefault('conductor_instance_id', conductor_instance_id)
                    tmp_parameter.setdefault('last_update_date_time', ci_last_update_date_time)
                    tmp_parameter.setdefault('status_id', status_id)
                    conductor_parameter = {
                        "file": {},
                        "parameter": tmp_parameter
                    }
                    tmp_result = objconductor.exec_maintenance(conductor_parameter, self.target_uuid, self.cmd_type)
                    if tmp_result[0] is not True:
                        status_code = "200-00807"
                        msg_args = [mode, conductor_instance_id, ci_status_id]
                        raise Exception()  # noqa: F405
                else:
                    status_code = "200-00808"
                    msg_args = [conductor_instance_id, ci_status_id]
                    raise Exception()  # noqa: F405

            elif mode == 'scram':
                # 緊急停止フラグON
                scram_accept_status = [
                    instance_info_data.get('dict').get('conductor_status').get('3'),
                    instance_info_data.get('dict').get('conductor_status').get('4'),
                    instance_info_data.get('dict').get('conductor_status').get('5')
                ]
                if ci_status_id in scram_accept_status:
                    if ci_abort_execute_flag != '0':
                        status_code = "200-00810"
                        msg_args = [conductor_instance_id, ci_status_id, ci_abort_execute_flag]
                        raise Exception()  # noqa: F405
                    tmp_parameter.setdefault('conductor_instance_id', conductor_instance_id)
                    tmp_parameter.setdefault('last_update_date_time', ci_last_update_date_time)
                    tmp_parameter.setdefault('abort_execute_flag', '1')
                    conductor_parameter = {
                        "file": {},
                        "parameter": tmp_parameter
                    }
                    tmp_result = objconductor.exec_maintenance(conductor_parameter, self.target_uuid, self.cmd_type)
                    if tmp_result[0] is not True:
                        status_code = "200-00807"
                        msg_args = [mode, conductor_instance_id, ci_status_id]
                        raise Exception()  # noqa: F405
                else:
                    status_code = "200-00809"
                    msg_args = [conductor_instance_id, ci_status_id]
                    raise Exception()  # noqa: F405

            elif mode == 'relese':
                if ni_node_type == "pause":
                    if ni_released_flag == "0":
                        released_accept_status = instance_info_data.get('dict').get('node_status').get('11')
                        if ni_status_id == released_accept_status:
                            status_id = instance_info_data.get('dict').get('node_status').get('3')
                            tmp_parameter.setdefault('last_update_date_time', ni_last_update_date_time)
                            tmp_parameter.setdefault('status_id', status_id)
                            tmp_parameter.setdefault('released_flag', '1')
                            tmp_parameter.setdefault('node_instance_id', node_instance_id)
                            node_parameter = {
                                "file": {},
                                "parameter": tmp_parameter
                            }
                            tmp_result = objnode.exec_maintenance(node_parameter, node_instance_id, self.cmd_type)
                            if tmp_result[0] is not True:
                                status_code = "200-00807"
                                msg_args = [mode, node_instance_id, ci_status_id]
                                raise Exception()  # noqa: F405
                        else:
                            status_code = "200-00813"
                            msg_args = [conductor_instance_id, node_instance_id, ni_status_id]
                            raise Exception()  # noqa: F405
                    else:
                        status_code = "200-00812"
                        msg_args = [conductor_instance_id, node_instance_id]
                        raise Exception()  # noqa: F405
                else:
                    status_code = "200-00811"
                    msg_args = [conductor_instance_id, node_instance_id, ni_node_type]
                    raise Exception()  # noqa: F405

        except Exception:
            retBool = False

        return retBool, status_code, msg_args,
