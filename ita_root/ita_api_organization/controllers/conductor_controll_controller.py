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

import connexion
import six  # noqa: F401

from common_libs.common import *  # noqa: F403
from libs import execute_info
from common_libs.api import api_filter

from libs import conductor_controll


# Conductorクラス関連
@api_filter
def get_conductor_class_info(organization_id, workspace_id, menu):  # noqa: E501
    """get_conductor_class_info

    ConductorClassの基本情報取得 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str

    :rtype: InlineResponse20012
    """

    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841

    # メニューのカラム情報を取得
    result_data = conductor_controll.get_conductor_class_info(objdbca, menu)
    return result_data,


@api_filter
def get_conductor_class_data(organization_id, workspace_id, menu, conductor_class_id):  # noqa: E501
    """get_conductor_class_data

    ConductorClassの情報取得 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_class_id: Conductor Class ID
    :type conductor_class_id: str

    :rtype: InlineResponse20011
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841

    # メニューのカラム情報を取得
    result_data = conductor_controll.get_conductor_data(objdbca, menu, conductor_class_id)
    return result_data,


@api_filter
def post_conductor_data(organization_id, workspace_id, menu, body=None):  # noqa: E501
    """post_conductor_data

    Conductorの新規登録 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param body:
    :type body: dict | bytes

    :rtype: InlineResponse20011
    """
    result_data = {}
    conductor_data = {}
    if connexion.request.is_json:
        conductor_data = dict(connexion.request.get_json())  # noqa: E501

    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841

    result_data = conductor_controll.conductor_maintenance(objdbca, menu, conductor_data)
    return result_data,


@api_filter
def patch_conductor_data(organization_id, workspace_id, menu, conductor_class_id, body=None):  # noqa: E501
    """patch_conductor_data

    Conductorの更新 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_class_id: Conductor Class ID
    :type conductor_class_id: str
    :param body:
    :type body: dict | bytes

    :rtype: InlineResponse20011
    """
    result_data = {}
    conductor_data = {}
    if connexion.request.is_json:
        conductor_data = dict(connexion.request.get_json())  # noqa: E501

    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    result_data = conductor_controll.conductor_maintenance(objdbca, menu, conductor_data, conductor_class_id)
    return result_data,


# 作業実行画面関連
@api_filter
def get_conductor_execute_info(organization_id, workspace_id, menu):  # noqa: E501
    """get_conductor_execute_info

    Conductor,Operationのメニューの基本情報および項目情報を取得する # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str

    :rtype: InlineResponse20013
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405
    
    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    # 作業実行関連のメニューの基本情報および項目情報の取得
    target_menu = ["operation_list", "movement_list", "conductor_list"]
    data = execute_info.call_collect_menu_info(objdbca, target_menu)
    return data,


@api_filter
def get_execute_search_candidates(organization_id, workspace_id, menu, target, column):  # noqa: E501
    """get_execute_search_candidates

    表示フィルタで利用するプルダウン検索の候補一覧を取得する # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param target: conductor_list or operation_list
    :type target: str
    :param column: REST用項目名
    :type column: str

    :rtype: InlineResponse2003
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405
    
    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    # 対象項目のプルダウン検索候補一覧を取得
    data = execute_info.collect_search_candidates(objdbca, target, column)
    return data,


@api_filter
def post_execute_filter(organization_id, workspace_id, menu, target, body=None):  # noqa: E501
    """post_execute_filter

    Conductor,Operationを対象に、検索条件を指定し、レコードを取得する # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param target: conductor_list or operation_list
    :type target: str
    :param body:
    :type body: dict | bytes

    :rtype: InlineResponse2005
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    filter_parameter = {}
    if connexion.request.is_json:
        body = dict(connexion.request.get_json())
        filter_parameter = body
        
    # メニューのカラム情報を取得
    result_data = execute_info.rest_filter(objdbca, target, filter_parameter)
    return result_data,


# 作業実行
@api_filter
def post_conductor_excecute(organization_id, workspace_id, menu, body=None):  # noqa: E501
    """post_conductor_excecute

    Conductor作業実行 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param body:
    :type body: dict | bytes

    :rtype: InlineResponse20011
    """

    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    parameter = {}
    if connexion.request.is_json:
        body = dict(connexion.request.get_json())
        parameter = body
        
    # メニューのカラム情報を取得
    result_data = conductor_controll.conductor_execute(objdbca, menu, parameter)
    return result_data,


# Conductor作業確認関連
@api_filter
def get_conductor_info(organization_id, workspace_id, menu, conductor_instance_id):  # noqa: E501
    """get_conductor_info

    Conductorの基本情報取得 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str

    :rtype: InlineResponse20012
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841

    # メニューのカラム情報を取得
    result_data = conductor_controll.get_conductor_info(objdbca, menu, conductor_instance_id)
    return result_data,


@api_filter
def get_conductor_instance_data(organization_id, workspace_id, menu, conductor_instance_id):  # noqa: E501
    """get_conductor_instance_data

    Conductor作業の情報取得 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str

    :rtype: InlineResponse20014
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841

    # メニューのカラム情報を取得
    result_data = conductor_controll.get_conductor_instance_data(objdbca, menu, conductor_instance_id)
    return result_data,


@api_filter
def patch_conductor_cancel(organization_id, workspace_id, menu, conductor_instance_id, body=None):
    """patch_conductor_cancel

    Conductor作業の予約取り消し # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str

    :rtype: InlineResponse20011
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    # 予約取消の実行
    action_type = "cancel"
    result_data = conductor_controll.conductor_execute_action(objdbca, menu, action_type, conductor_instance_id)
    return result_data,


@api_filter
def patch_conductor_relese(organization_id, workspace_id, menu, conductor_instance_id, node_instance_id, body=None):  # noqa: E501
    """patch_conductor_relese

    Conductor作業の一時停止解除 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str
    :param node_instance_id: Node Instance ID
    :type node_instance_id: str

    :rtype: InlineResponse20011
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    # 一時停止解除の実行
    action_type = "relese"
    result_data = conductor_controll.conductor_execute_action(objdbca, menu, action_type, conductor_instance_id, node_instance_id)
    return result_data,


@api_filter
def patch_conductor_scram(organization_id, workspace_id, menu, conductor_instance_id, body=None):  # noqa: E501
    """patch_conductor_scram

    Conductor作業の緊急停止 # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str

    :rtype: InlineResponse20011
    """
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405

    # メニューに対するロール権限をチェック（Falseなら権限エラー）
    chk_auth_manu = execute_info.call_check_auth_menu(objdbca, menu)  # noqa: F841
    
    # 緊急停止の実行
    action_type = "scram"
    result_data = conductor_controll.conductor_execute_action(objdbca, menu, action_type, conductor_instance_id)
    return result_data,


# Conductor作業確認一覧個別関連
@api_filter
def get_conductor_input_data(organization_id, workspace_id, menu, conductor_instance_id):  # noqa: E501
    """get_conductor_input_data

    Conductor作業の投入データ # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str

    :rtype: InlineResponse20015
    """
    return 'do some magic!'


@api_filter
def get_conductor_result_data(organization_id, workspace_id, menu, conductor_instance_id):  # noqa: E501
    """get_conductor_result_data

    Conductor作業の結果データ # noqa: E501

    :param organization_id: OrganizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param menu: メニュー名
    :type menu: str
    :param conductor_instance_id: Conductor Instance ID
    :type conductor_instance_id: str

    :rtype: InlineResponse20016
    """
    return 'do some magic!'
