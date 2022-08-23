# Copyright 2022 NEC Corporation#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from flask import g  # noqa: F401
from common_libs.common.exception import AppException  # noqa: F401

from common_libs.common import *  # noqa: F403
from common_libs.loadtable import *  # noqa: F403
from common_libs.conductor.classes.util import ConductorCommonLibs  # noqa: F401
from common_libs.conductor.classes.exec_util import *  # noqa: F403

import os
from pprint import pprint  # noqa: F401


backyard_name = 'ita_by_conductor_synchronize'
backyard_name = ''


def backyard_main(organization_id, workspace_id):
    print("backyard_main ita_by_conductor_synchronize called")

    """
        Conductor作業実行処理（backyard）
        
        DB接続
        環境設定(言語,Lib読込,etc...)
        ConductorIF情報取得
        MVIF情報取得,(Orchestra毎)
        対象Conductor取得
            Conductor処理(※繰り返し開始)
                transaction開始
                Conductor処理1
                    共有パスを生成
                    Conductor開始
                Node処理開始(※繰り返し)
                    Node処理
                Conductor処理1
                    ステータス反映
                transaction終了
            Conductor処理終了(※繰り返し終了)
    """
    retBool = True
    result = {}
    # g.applogger.set_level("INFO") # ["ERROR", "INFO", "DEBUG"]
    
    tmp_msg = 'Process Start'
    g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405  # noqa: F405

    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405
    
    # 環境情報設定
    # 言語情報
    if 'LANGUAGE' not in g:
        g.LANGUAGE = 'ja'
    if 'USER_ID' not in g:
        g.USER_ID = '1'

    # storageパス
    strage_path = os.environ.get('STORAGEPATH')
    # 実行制限数初期値
    execute_limit = 10000
    execute_limit_key = 'CONDUCTOR_LIMIT'

    # conductor backyard lib読込
    objcbkl = ConductorExecuteBkyLibs(objdbca)  # noqa: F405
    if objcbkl.get_objmenus() is False:
        tmp_msg = 'ConductorExecuteBkyLibs Error'
        # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        exit()

    # Sysrtem configの取得
    tmp_result = objcbkl.get_system_config()
    if tmp_result[0] is not True:
        tmp_msg = 'get_system_config Error'
        # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        exit()
    
    # conductor実行制限
    system_config = tmp_result[1]
    if execute_limit_key in system_config:
        tmp_execute_limit = system_config.get(execute_limit_key)
        if tmp_execute_limit is not None:
            execute_limit = tmp_execute_limit
            
    # conductorif からstoragepath 取得
    tmp_result = objcbkl.get_conductor_interface()
    if tmp_result[0] is not True:
        tmp_msg = 'get_conductor_interface Error'
        # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        exit()
    conductor_storage_path_ita = tmp_result[1].get('CONDUCTOR_STORAGE_PATH_ITA')
    base_conductor_storage_path = "{}{}/{}{}".format(strage_path, organization_id, workspace_id, conductor_storage_path_ita)

    # Orchestra毎 MVIF情報取得
    #
    #
    #

    # 作業対象のConductorの取得
    tmp_result = objcbkl.get_execute_conductor_list(execute_limit)
    if tmp_result[0] is not True:
        tmp_msg = 'get_execute_conductor_list Error'
        # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        exit()
    target_conductor_list = tmp_result[1]
    
    # 作業対象無しで終了
    if len(target_conductor_list) == 0:
        tmp_msg = 'No Execute Conductor'
        # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        exit()
        
    # 参照系リスト取得
    instance_info_data = objcbkl.get_instance_info_data()
    start_status = []
    for tmp_status in ['1', '2']:
        start_status.append(instance_info_data.get('dict').get('conductor_status').get(tmp_status))
    end_status = []
    for tmp_status in ['6', '7', '8', '11', '9']:
        end_status.append(instance_info_data.get('dict').get('conductor_status').get(tmp_status))

    # 作業実行件数
    tmp_msg = 'EXECUTE COUNT:{} '.format(len(target_conductor_list))
    g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
    
    # Conductor毎に繰り返し処理
    execute_conductor_cnt = 0
    for conductor_instance_id, tmp_info in target_conductor_list.items():
        tmp_msg = 'ID:{} Start'.format(conductor_instance_id)
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        ci_status = tmp_info.get('status')

        # トランザクション開始
        objdbca.db_transaction_start()
        locktable_list = ['T_COMN_CONDUCTOR_INSTANCE', 'T_COMN_CONDUCTOR_NODE_INSTANCE']
        tmp_result = objdbca.table_lock(locktable_list)
        
        # update_flg = ON
        ci_update_flg = 1
        ni_update_flg = 1
        
        # Conductor instance処理_1
        try:
            # 共有パスを生成
            conductor_storage_path = "{}/{}".format(base_conductor_storage_path, conductor_instance_id)
            ci_status_id = tmp_info.get('status')
            tmp_result = objcbkl.create_data_storage_path(conductor_storage_path, ci_status_id)
            if tmp_result is False:
                tmp_msg = 'Create storage path Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()
            
            # 未実行,未実行(予約)時、ステータス更新＋開始時刻
            if ci_status in ['1', '2']:
                # Conductor instanceステータス更新
                tmp_result = objcbkl.conductor_status_update(conductor_instance_id)
                if tmp_result[0] is not True:
                    tmp_msg = 'Update Conductor instance Error'
                    # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                    g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                    raise Exception()

        except Exception:
            ci_update_flg = 0

        # Node instance処理
        try:
            if ni_update_flg != 1 and ci_update_flg != 1:
                tmp_msg = ' Conductor Node instance update Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()

            # Node instance取得
            tmp_result = objcbkl.get_filter_node(conductor_instance_id)
            if tmp_result[0] is not True:
                tmp_msg = 'Get Filter Node instance Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()
            all_node_filter = tmp_result[1]
            
            # 全 Nodeのステータス取得
            tmp_result = objcbkl.get_execute_all_node_list(conductor_instance_id)
            if tmp_result[0] is not True:
                tmp_msg = 'Get Node instance Status Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()
            target_all_node_list = tmp_result[1]

            # Start Nodeのnode_instance_id取得
            tmp_result = objcbkl.get_start_node(conductor_instance_id)
            if tmp_result[0] is not True:
                tmp_msg = 'Get Start Node instance Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()
            start_node_instance_id = tmp_result[1]

            # Start Nodeが未実行か判定
            start_node_execute_flg = objcbkl.chk_conductor_start(start_node_instance_id, target_all_node_list)
            if start_node_execute_flg is True:
                # START Node開始処理
                tmp_result = objcbkl.execute_node_action(conductor_instance_id, start_node_instance_id, all_node_filter)
                if tmp_result[0] is not True:
                    tmp_msg = 'Execute Start Node instance Error'
                    # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                    g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                    raise Exception()

            # Conductor実行中
            if start_node_execute_flg is False:
                # Node毎の処理
                for target_status, target_node in target_all_node_list['status'].items():
                    # 実行中,実行中(遅延),一時停止を処理
                    if target_status in ['3', '4', '11']:
                        for node_instance_id in target_node:
                            #  Node処理
                            tmp_result = objcbkl.execute_node_action(conductor_instance_id, node_instance_id, all_node_filter)
                            if tmp_result[0] is not True:
                                tmp_msg = 'Execute Node Error'
                                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                                raise Exception()
        except Exception:
            ni_update_flg = 0

        # Conductor instance処理_2
        try:
            if ni_update_flg != 1 or ci_update_flg != 1:
                tmp_msg = ' Conductor Node instance update Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()
            # Conductor instanceステータス更新
            tmp_result = objcbkl.conductor_status_update(conductor_instance_id)
            if tmp_result[0] is not True:
                tmp_msg = 'Update Conductor instance Error'
                # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
                raise Exception()
            
        except Exception:
            ci_update_flg = 0

        try:
            if (ni_update_flg == 1 and ci_update_flg == 1) is True:
                # トランザクション終了
                objdbca.db_transaction_end(True)
                tmp_msg = 'db_transaction_end(True)'.format()
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
            else:
                retBool = False
                # トランザクション終了
                objdbca.db_transaction_end(False)
                tmp_msg = 'db_transaction_end(False)'.format()
                g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        except Exception:
            retBool = False
            # トランザクション終了
            objdbca.db_transaction_end(False)
            tmp_msg = 'db_transaction_end(False)'.format()
            g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        finally:
            execute_conductor_cnt = execute_conductor_cnt + 1

        tmp_msg = 'ID:{} END'.format(conductor_instance_id)
        g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
        # print(execute_conductor_cnt, execute_limit, execute_conductor_cnt <= execute_limit)
        if (execute_conductor_cnt <= execute_limit) is False:
            tmp_msg = 'execute_limit:{}'.format(execute_limit)
            # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
            # g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
            break

    tmp_msg = 'Process End'
    g.applogger.debug(addline_msg('{}'.format(tmp_msg), backyard_name))  # noqa: F405
    # tmp_msg = g.appmsg.get_log_message(status_code, [msg_args])
    
    return retBool, result,
