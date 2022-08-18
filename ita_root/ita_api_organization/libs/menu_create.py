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

import json
from common_libs.common import *  # noqa: F403
from common_libs.loadtable import *  # noqa: F403
from flask import g
from libs.organization_common import check_auth_menu
from libs.menu_info import add_tmp_column_group, collect_column_group_sort_order, collect_parent_sord_order
from common_libs.api import check_request_body_key


def collect_menu_create_data(objdbca):
    """
        メニュー定義・作成(新規)用の情報取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
        RETRUN:
            create_data
    """
    # 共通部分を取得
    create_data = _collect_common_menu_create_data(objdbca)

    return create_data


def collect_exist_menu_create_data(objdbca, menu_create):
    """
        メニュー定義・作成(既存)用の情報取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
        RETRUN:
            create_data
    """
    # テーブル/ビュー名
    t_menu_define = 'T_MENU_DEFINE'
    t_menu_column = 'T_MENU_COLUMN'
    t_menu_column_group = 'T_MENU_COLUMN_GROUP'
    t_menu_unique_constraint = 'T_MENU_UNIQUE_CONSTRAINT'
    t_menu_convert = 'T_MENU_CONVERT'
    
    # 変数定義
    lang = g.get('LANGUAGE')
    menu_info = {}
    
    # 共通部分を取得
    create_data = _collect_common_menu_create_data(objdbca)
    
    # 対象メニューグループのデータを形成
    format_target_menu_group_list = {}
    for target in create_data['target_menu_group_list']:
        format_target_menu_group_list[target.get('menu_group_id')] = target.get('menu_group_name')
    
    # シートタイプのデータを形成
    format_sheet_type_list = {}
    for target in create_data['sheet_type_list']:
        format_sheet_type_list[target.get('sheet_type_id')] = target.get('sheet_type_name')
        
    # カラムクラスのデータを形成
    format_column_class_list = {}
    for target in create_data['column_class_list']:
        format_column_class_list[target.get('column_class_id')] = {'column_class_name': target.get('column_class_name'), 'column_class_disp_name': target.get('column_class_disp_name')}  # noqa: E501
    
    # 「メニュー定義一覧」から対象のメニューのレコードを取得
    ret = objdbca.table_select(t_menu_define, 'WHERE MENU_NAME_REST = %s AND DISUSE_FLAG = %s', [menu_create, 0])
    if not ret:
        log_msg_args = [menu_create]
        api_msg_args = [menu_create]
        # ####メモ：「対象のメニューがメニュー定義一覧にありません」的なメッセージ
        raise AppException("999-00001", log_msg_args, api_msg_args)  # noqa: F405
    
    # 対象のuuidを取得
    menu_create_id = ret[0].get('MENU_CREATE_ID')
    
    # 対象メニューグループについて、名称を取得
    menu_group_for_input_id = ret[0].get('MENU_GROUP_ID_INPUT')
    menu_group_for_subst_id = ret[0].get('MENU_GROUP_ID_SUBST')
    menu_group_for_ref_id = ret[0].get('MENU_GROUP_ID_REF')
    menu_group_for_input = format_target_menu_group_list.get(menu_group_for_input_id)
    menu_group_for_subst = format_target_menu_group_list.get(menu_group_for_subst_id)
    menu_group_for_ref = format_target_menu_group_list.get(menu_group_for_ref_id)
    
    # シートタイプについて、名称を取得
    sheet_type_id = ret[0].get('SHEET_TYPE')
    sheet_type_name = format_sheet_type_list.get(sheet_type_id)
    
    # 最終更新日時のフォーマット
    last_update_timestamp = ret[0].get('LAST_UPDATE_TIMESTAMP')
    last_update_date_time = last_update_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    # 縦メニュー利用の有無を取得
    vertical = ret[0].get('VERTICAL')

    # メニューデータを格納
    menu = {
        "menu_name": ret[0].get('MENU_NAME_' + lang.upper()),
        "menu_name_rest": ret[0].get('MENU_NAME_REST'),
        "sheet_type_id": sheet_type_id,
        "sheet_type_name": sheet_type_name,
        "disp_seq": ret[0].get('DISP_SEQ'),
        "purpose_id": ret[0].get('PURPOSE'),
        "vertical": vertical,
        "menu_group_for_input_id": menu_group_for_input_id,
        "menu_group_for_subst_id": menu_group_for_subst_id,
        "menu_group_for_ref_id": menu_group_for_ref_id,
        "menu_group_for_input": menu_group_for_input,
        "menu_group_for_subst": menu_group_for_subst,
        "menu_group_for_ref": menu_group_for_ref,
        "description": ret[0].get('DESCRIPTION_' + lang.upper()),
        "remarks": ret[0].get('NOTE'),
        "menu_create_done_status_id": ret[0].get('MENU_CREATE_DONE_STATUS'),
        "last_update_date_time": last_update_date_time
    }
    
    # 「一意制約(複数項目)作成情報」から対象のレコードを取得
    menu['unique_constraint_current'] = None
    ret = objdbca.table_select(t_menu_unique_constraint, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
    if ret:
        str_unique_constraint = json.dumps(ret[0].get('UNIQUE_CONSTRAINT_ITEM'))
        unique_constraint_current = json.loads(str_unique_constraint)
        menu['unique_constraint_current'] = unique_constraint_current
    
    # メニュー情報を格納
    menu_info['menu'] = menu
    
    # ####メモ：縦メニュー系の処理未実装
    # # 縦メニュー利用がある場合、繰り返し情報を取得して格納
    repeat = {}
    if int(vertical):
        # 「メニュー(縦)作成情報」から対象のレコードを取得
        ret = objdbca.table_select(t_menu_convert, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
        # ####メモ：縦メニュー情報を格納する処理
        
    menu_info['repeat'] = repeat
    
    # 「カラムグループ作成情報」からレコードをすべて取得
    column_group_list = {}
    ret = objdbca.table_select(t_menu_column_group, 'WHERE DISUSE_FLAG = %s', [0])
    col_group_recode_count = len(ret)  # 「カラムグループ作成情報」のレコード数を格納
    for recode in ret:
        add_data = {
            "column_group_id": recode.get('CREATE_COL_GROUP_ID'),
            "column_group_name": recode.get('COL_GROUP_NAME_' + lang.upper()),
            "full_column_group_name": recode.get('FULL_COL_GROUP_NAME_' + lang.upper()),
            "parent_column_group_id": recode.get('PA_COL_GROUP_ID')
        }
        column_group_list[recode.get('CREATE_COL_GROUP_ID')] = add_data
    
    # 「メニュー項目作成情報」から対象のメニューのレコードを取得
    column_info_data = {}
    column_group_info_data = {}
    tmp_column_group = {}
    column_group_parent_of_child = {}  # カラムグループの親子関係があるとき、子の一番大きい親を結びつける
    ret = objdbca.table_select(t_menu_column, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s ORDER BY DISP_SEQ ASC', [menu_create_id, 0])
    if ret:
        for count, recode in enumerate(ret, 1):
            # 最終更新日時のフォーマット
            last_update_timestamp = recode.get('LAST_UPDATE_TIMESTAMP')
            last_update_date_time = last_update_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
            
            # カラムデータを格納
            col_detail = {
                "create_column_id": recode.get('CREATE_COLUMN_ID'),
                "item_name": recode.get('COLUMN_NAME_' + lang.upper()),
                "item_name_rest": recode.get('COLUMN_NAME_REST'),
                "display_order": recode.get('DISP_SEQ'),
                "required": recode.get('REQUIRED'),
                "uniqued": recode.get('UNIQUED'),
                "autoreg_hide_item": recode.get('AUTOREG_HIDE_ITEM'),
                "autoreg_only_item": recode.get('AUTOREG_ONLY_ITEM'),
                "column_class_id": "",
                "column_class_name": "",
                "description": recode.get('DESCRIPTION_' + lang.upper()),
                "remarks": recode.get(''),
                "last_update_date_time": last_update_date_time
            }
            
            # フルカラムグループ名を格納
            column_group_id = recode.get('CREATE_COL_GROUP_ID')
            col_detail['column_group_id'] = column_group_id
            col_detail['column_group_name'] = None
            if column_group_id:
                target_data = column_group_list.get(column_group_id)
                if target_data:
                    col_detail['column_group_name'] = target_data.get('full_column_group_name')
                
            # カラムクラス情報を格納
            column_class_id = recode.get('COLUMN_CLASS')
            column_class_name = format_column_class_list.get(column_class_id).get('column_class_name')
            column_class_disp_name = format_column_class_list.get(column_class_id).get('column_class_disp_name')
            col_detail['column_class_id'] = column_class_id
            col_detail['column_class_name'] = column_class_name
            col_detail['column_class_disp_name'] = column_class_disp_name
            
            # カラムクラスに応じて必要な値を格納
            # カラムクラス「文字列(単一行)」用のパラメータを追加
            if column_class_name == "SingleTextColumn":
                col_detail["string_maximum_bytes"] = recode.get('SINGLE_MAX_LENGTH')  # 文字列(単一行) 最大バイト数
                col_detail["string_regular_expression"] = recode.get('SINGLE_PREG_MATCH')  # 文字列(単一行) 正規表現
                col_detail["string_default_value"] = recode.get('SINGLE_DEFAULT_VALUE')  # 文字列(単一行) 初期値
            
            # カラムクラス「文字列(複数行)」用のパラメータを追加
            if column_class_name == "MultiTextColumn":
                col_detail["multi_string_maximum_bytes"] = recode.get('MULTI_MAX_LENGTH')  # 文字列(複数行) 最大バイト数
                col_detail["multi_string_regular_expression"] = recode.get('MULTI_PREG_MATCH')  # 文字列(複数行) 正規表現
                col_detail["multi_string_default_value"] = recode.get('MULTI_DEFAULT_VALUE')  # 文字列(複数行) 初期値
            
            # カラムクラス「整数」用のパラメータを追加
            if column_class_name == "NumColumn":
                col_detail["integer_maximum_value"] = recode.get('NUM_MAX')  # 整数 最大値
                col_detail["integer_minimum_value"] = recode.get('NUM_MIN')  # 整数 最小値
                col_detail["integer_default_value"] = recode.get('NUM_DEFAULT_VALUE')  # 整数 初期値
            
            # カラムクラス「小数」用のパラメータを追加
            if column_class_name == "FloatColumn":
                col_detail["decimal_maximum_value"] = recode.get('FLOAT_MAX')  # 小数 最大値
                col_detail["decimal_minimum_value"] = recode.get('FLOAT_MIN')  # 小数 最小値
                col_detail["decimal_digit"] = recode.get('decimal_digit')  # 小数 桁数
                col_detail["decimal_default_value"] = recode.get('FLOAT_DEFAULT_VALUE')  # 小数 初期値
            
            # カラムクラス「日時」用のパラメータを追加
            if column_class_name == "DateTimeColumn":
                col_detail["detetime_default_value"] = recode.get('DATETIME_DEFAULT_VALUE')  # 日時 初期値
            
            # カラムクラス「日付」用のパラメータを追加
            if column_class_name == "DateColumn":
                col_detail["dete_default_value"] = recode.get('DATE_DEFAULT_VALUE')  # 日付 初期値
            
            # カラムクラス「プルダウン選択」用のパラメータを追加
            if column_class_name == "IDColumn":
                col_detail["pulldown_selection"] = recode.get('OTHER_MENU_LINK_ID')  # プルダウン選択 メニューグループ:メニュー:項目
                col_detail["pulldown_selection_default_value"] = recode.get('OTHER_MENU_LINK_DEFAULT_VALUE')  # プルダウン選択 初期値
                col_detail["reference_item"] = recode.get('REFERENCE_ITEM')  # プルダウン選択 参照項目
            
            # カラムクラス「パスワード」用のパラメータを追加
            if column_class_name == "PasswordColumn":
                col_detail["password_maximum_bytes"] = recode.get('PASSWORD_MAX_LENGTH')  # パスワード 最大バイト数
            
            # カラムクラス「ファイルアップロード」用のパラメータを追加
            if column_class_name == "FileUploadColumn":
                col_detail["file_upload_maximum_bytes"] = recode.get('FILE_UPLOAD_MAX_SIZE')  # ファイルアップロード 最大バイト数
            
            # カラムクラス「ファイルアップロード(暗号化)」用のパラメータを追加
            if column_class_name == "FileUploadEncryptColumn":
                col_detail["file_upload_encrypt_maximum_bytes"] = recode.get('FILE_UPLOAD_ENC_MAX_SIZE')  # ファイルアップロード(暗号化) 最大バイト数
            
            # カラムクラス「リンク」用のパラメータを追加
            if column_class_name == "HostInsideLinkTextColumn":
                col_detail["link_maximum_bytes"] = recode.get('LINK_MAX_LENGTH')  # リンク 最大バイト数
                col_detail["link_default_value"] = recode.get('LINK_DEFAULT_VALUE')  # リンク 初期値
            
            # カラムクラス「パラメータシート参照」用のパラメータを追加 (未実装)
            # if column_class_name == "LinkIDColumn":
            #     col_detail["parameter_sheet_reference"] = recode.get('PARAM_SHEET_LINK_ID')  # パラメータシート参照
            
            # 縦メニュー利用のチェック
            # ####メモ：未実装
            col_detail["repeat_item"] = "0"
            
            col_num = 'c{}'.format(count)
            column_info_data[col_num] = col_detail
            
            # ####メモ：縦メニュー用の考慮がされていないため、最終的な修正が必要。
            # カラムグループ利用があれば、カラムグループ管理用配列に追加
            if column_group_id:
                tmp_column_group, column_group_parent_of_child = add_tmp_column_group(column_group_list, col_group_recode_count, column_group_id, col_num, tmp_column_group, column_group_parent_of_child)  # noqa: E501
        
        # カラムグループ管理用配列について、カラムグループIDをg1,g2,g3...に変換し、idやnameを格納する。
        column_group_info_data, key_to_id = collect_column_group_sort_order(column_group_list, tmp_column_group, column_group_info_data)
        
        # 大元のカラムの並び順を作成し格納
        # ####メモ：縦メニュー用の考慮がされていないため、最終的な修正が必要。
        menu_info['menu']['columns'] = collect_parent_sord_order(column_info_data, column_group_parent_of_child, key_to_id)
    
    # カラム情報およびカラムグループ情報の個数を取得し、menu_info['menu']に格納
    menu_info['menu']['number_item'] = len(column_info_data)
    menu_info['menu']['number_group'] = len(column_group_info_data)
    
    # カラム情報を格納
    menu_info['column'] = column_info_data
    
    # カラムグループ情報を格納
    menu_info['group'] = column_group_info_data
    
    # 情報を返却値に格納
    create_data['menu_info'] = menu_info
    
    return create_data


def _collect_common_menu_create_data(objdbca):
    """
        【内部呼び出し用】メニュー定義・作成用情報の共通部分取得
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
        RETRUN:
            common_data
    """
    # テーブル/ビュー名
    # t_common_column_class = 'T_COMN_COLUMN_CLASS'
    v_menu_column_class = 'V_MENU_COLUMN_CLASS'
    v_menu_sheet_type = 'V_MENU_SHEET_TYPE'
    v_menu_target_menu_group = 'V_MENU_TARGET_MENU_GROUP'
    v_menu_other_link = 'V_MENU_OTHER_LINK'

    # 変数定義
    lang = g.get('LANGUAGE')

    # カラムクラスの選択肢一覧
    column_class_list = []
    ret = objdbca.table_select(v_menu_column_class, 'ORDER BY DISP_SEQ ASC')
    for recode in ret:
        column_class_id = recode.get('COLUMN_CLASS_ID')
        column_class_name = recode.get('COLUMN_CLASS_NAME')
        column_class_disp_name = recode.get('COLUMN_CLASS_DISP_NAME_' + lang.upper())
        column_class_list.append({'column_class_id': column_class_id, 'column_class_name': column_class_name, 'column_class_disp_name': column_class_disp_name})  # noqa: E501

    # 対象メニューグループの選択肢一覧
    target_menu_group_list = []
    ret = objdbca.table_select(v_menu_target_menu_group, 'ORDER BY DISP_SEQ ASC')
    for recode in ret:
        menu_group_id = recode.get('MENU_GROUP_ID')
        menu_group_name = recode.get('MENU_GROUP_NAME_' + lang.upper())
        full_menu_group_name = recode.get('FULL_MENU_GROUP_NAME_' + lang.upper())
        target_menu_group_list.append({'menu_group_id': menu_group_id, 'menu_group_name': menu_group_name, 'full_menu_group_name': full_menu_group_name})  # noqa: E501

    # シートタイプの選択肢一覧
    sheet_type_list = []
    ret = objdbca.table_select(v_menu_sheet_type, 'ORDER BY DISP_SEQ ASC')
    for recode in ret:
        sheet_type_id = recode.get('SHEET_TYPE_NAME_ID')
        sheet_type_name = recode.get('SHEET_TYPE_NAME_' + lang.upper())
        sheet_type_list.append({'sheet_type_id': sheet_type_id, 'sheet_type_name': sheet_type_name})

    # カラムクラス「プルダウン選択」の選択項目一覧
    pulldown_item_list = []
    ret = objdbca.table_select(v_menu_other_link, 'ORDER BY MENU_GROUP_ID ASC')
    for recode in ret:
        link_id = recode.get('LINK_ID')
        menu_id = recode.get('MENU_ID')
        link_pulldown = recode.get('LINK_PULLDOWN_' + lang.upper())
        pulldown_item_list.append({'link_id': link_id, 'menu_id': menu_id, 'link_pulldown': link_pulldown})
    
    # ロールの選択肢一覧
    # ####メモ：共通基盤と結合後、ロール取得APIを実施して対象のロールを取得する。
    # 選択可能なロールは、Workspaceが持っているロールすべて。
    role_list = ["dummy_role1", "dummy_role2", "dummy_role3"]
    
    common_data = {
        "column_class_list": column_class_list,
        "target_menu_group_list": target_menu_group_list,
        "sheet_type_list": sheet_type_list,
        "pulldown_item_list": pulldown_item_list,
        "role_list": role_list
    }
    
    return common_data


def menu_create_execute(objdbca, exec_target):
    """
        メニュー作成の実行
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            exec_target: メニュー作成の実行対象
        RETRUN:
            result_data
    """
    
    return {"aaa": "bbb"}


def menu_create_define(objdbca, create_param):
    """
        メニュー定義および作成の実行
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            create_param: メニュー定義用パラメータ
        RETRUN:
            result_data
    """
    # typeから「新規作成」「初期化」「編集」のいずれかを判断
    type = create_param.get('type')
    if type == 'create_new':  # 「新規作成」
        print('タイプは：' + str(type))
        result = _create_new_execute(objdbca, create_param)
        
        status = result.get('status')
        message = result.get('message')
        # print(status)
        # if not status:
        #     # ####メモ：関数で失敗した際にメッセージを受け取ってそれを入れる。
        #     # ####まだここの動き全然考えてないので、あとでやる。
        #     raise AppException('999-00001')  # noqa: F405
        
    elif type == 'initialize':  # 「初期化」
        print('タイプは：' + str(type))
        
    elif type == 'edit':  # 「編集」
        print('タイプは：' + str(type))
        
    else:
        # ####メモ：typeが指定された値ではない場合のエラー。あとでちゃんと作る。
        msg = 'type:' + str(type)
        log_msg_args = [msg]
        api_msg_args = [msg]
        raise AppException('499-00212', log_msg_args, api_msg_args)  # noqa: F405
    
    # 「新規作成」「編集」「初期化」のどれかを判定
    # 上記のタイプごとに処理を関数分けして、呼び出すようにする。
    
    result_data = {'status': status, 'message': message}
    return result_data


def _create_new_execute(objdbca, create_param):
    """
        【内部呼び出し用】「新規作成」時のメニュー作成用メニューに対するレコードをの登録
        ARGS:
            objdbca:DB接クラス  DBConnectWs()
            create_param: メニュー定義用パラメータ
        RETRUN:
            result_data
    """
    # テーブル名
    t_menu_create_done_status = 'T_MENU_CREATE_DONE_STATUS'
    t_menu_column_group = 'T_MENU_COLUMN_GROUP'
    t_menu_create_history = 'T_MENU_CREATE_HISTORY'
    
    # 変数定義
    lang = g.get('LANGUAGE')
    user_id = g.get('USER_ID')
    
    # 登録するためのデータを抽出
    menu_data = check_request_body_key(create_param, 'menu')  # "menu" keyが無かったら400-00002エラー
    column_data_list = check_request_body_key(create_param, 'column')  # "column" keyが無かったら400-00002エラー
    group_data_list = create_param.get('group')
    
    # 「メニュー作成状態」のステータス名称(未作成)を取得
    ret = objdbca.table_select(t_menu_create_done_status, 'WHERE DONE_STATUS_ID = %s AND DISUSE_FLAG = %s', [1, 0])
    menu_create_done_status = ret[0].get('DONE_STATUS_NAME_' + lang.upper())
    
    status = False
    try:
        # トランザクション開始
        objdbca.db_transaction_start()
        
        # 「メニュー定義一覧」にレコードを登録
        # loadTableの呼び出し
        objmenu = load_table.loadTable(objdbca, 'menu_definition_list')  # noqa: F405
        
        # 登録用パラメータを作成
        parameters = {
            "parameter": {
                "menu_name_ja": menu_data.get('menu_name'),  # メニュー名称(ja)
                "menu_name_en": menu_data.get('menu_name'),  # メニュー名称(en)
                "menu_name_rest": menu_data.get('menu_name_rest'),  # メニュー名称(rest)
                "sheet_type": menu_data.get('sheet_type'),  # シートタイプ名
                "display_order": menu_data.get('display_order'),  # 表示順序
                "description_ja": menu_data.get('description'),  # 説明(ja)
                "description_en": menu_data.get('description'),  # 説明(en)
                "remarks": menu_data.get('remarks'),  # 備考
                "purpose": menu_data.get('purpose'),  # 用途
                "vertical": menu_data.get('vertical'),  # 縦メニュー利用有無
                "menu_group_for_input": menu_data.get('menu_group_for_input'),  # 入力用メニューグループ名
                "menu_group_for_subst": menu_data.get('menu_group_for_subst'),  # 代入値自動登録用メニューグループ名
                "menu_group_for_ref": menu_data.get('menu_group_for_ref'),  # 参照用メニューグループ名
                "menu_create_done_status": menu_create_done_status
            },
            "type": "Register"
        }

        # 登録を実行
        exec_result = objmenu.exec_maintenance(parameters)  # noqa: F405
        if not exec_result[0]:
            print("「メニュー定義一覧」にレコードを登録する際にエラーが起きた。")
            raise Exception(exec_result[2])
        
        # 登録されたレコードのUUIDを保管
        menu_create_id = exec_result[1].get('uuid')
        
        tmp_data = objmenu.get_exec_count()  # noqa: F405
        print(tmp_data)
        
        # カラムグループ用データがある場合、「カラムグループ作成情報」にレコードを登録
        if group_data_list:
            # 現在登録されている「カラムグループ作成情報」のレコード一覧を取得
            column_group_list = objdbca.table_select(t_menu_column_group, 'WHERE DISUSE_FLAG = %s', [0])
            
            # loadTableの呼び出し
            objmenu = load_table.loadTable(objdbca, 'column_group_creation_info')  # noqa: F405
            
            # 「「カラムグループ作成情報」登録処理のループスタート
            for num, group_data in group_data_list.items():
                # リピートされたカラムグループである場合はスキップ
                if group_data.get('repeat_group'):
                    continue
                
                # 登録用パラメータを作成
                col_group_name_ja = group_data.get('col_group_name')
                col_group_name_en = group_data.get('col_group_name')
                parent_full_col_group_name = group_data.get('parent_full_col_group_name')
                
                # 親カラムグループがあれば、対象の「フルカラムグループ名」を取得
                parent_column_group = None
                if parent_full_col_group_name:
                    if lang.lower() == 'ja':
                        target_parent = objdbca.table_select(t_menu_column_group, 'WHERE FULL_COL_GROUP_NAME_JA = %s AND DISUSE_FLAG = %s', [parent_full_col_group_name, 0])  # noqa: E501
                    elif lang.lower() == 'en':
                        target_parent = objdbca.table_select(t_menu_column_group, 'WHERE FULL_COL_GROUP_NAME_EN = %s AND DISUSE_FLAG = %s', [parent_full_col_group_name, 0])  # noqa: E501
                    
                    if not target_parent:
                        raise Exception("「カラムグループ作成情報」にレコードを登録する際に、存在しない親IDを指定しようとした。")
                    
                    # ####メモ：本来は「カラムグループ作成情報」に対する「before_function」にてフルカラムグループ名を作成する処理を実行する。
                    # 最終で気にここでフルカラムグループ名を作成する処理は書かない想定。
                    # 『親フルカラムグループ/カラムグループ名』の命名規則でフルカラムグループ名を作成。
                    parent_full_name_ja = target_parent[0].get('FULL_COL_GROUP_NAME_JA')
                    parent_full_name_en = target_parent[0].get('FULL_COL_GROUP_NAME_EN')
                    full_column_group_name_ja = parent_full_name_ja + '/' + col_group_name_ja
                    full_column_group_name_en = parent_full_name_en + '/' + col_group_name_en
                    
                    parent_full_name = target_parent[0].get('FULL_COL_GROUP_NAME_' + lang.upper())
                    parent_column_group = parent_full_name
                    
                else:
                    full_column_group_name_ja = col_group_name_ja
                    full_column_group_name_en = col_group_name_en
                
                # 『「フルカラムグループ(ja)」』か『「フルカラムグループ(en)」』ですでに同じレコードがあれば処理をスキップ
                skip_flag = False
                for recode in column_group_list:
                    if full_column_group_name_ja == recode.get('FULL_COL_GROUP_NAME_JA') or full_column_group_name_en == recode.get('FULL_COL_GROUP_NAME_EN'):  # noqa: E501
                        skip_flag = True
                
                if skip_flag:
                    continue
                
                # 登録用パラメータを作成
                parameters = {
                    "parameter": {
                        "parent_column_group": parent_column_group,
                        "column_group_name_ja": col_group_name_ja,
                        "column_group_name_en": col_group_name_en,
                        "full_column_group_name_ja": full_column_group_name_ja,
                        "full_column_group_name_en": full_column_group_name_en
                    },
                    "type": "Register"
                }

                # 登録を実行
                exec_result = objmenu.exec_maintenance(parameters)  # noqa: F405
                if not exec_result[0]:
                    print("「カラムグループ作成情報」にレコードを登録する際にエラーが起きた。")
                    raise Exception(exec_result[2])
                
                # 現在登録されている「カラムグループ作成情報」のレコード一覧を更新
                column_group_list = objdbca.table_select(t_menu_column_group, 'WHERE DISUSE_FLAG = %s', [0])
            
            tmp_data = objmenu.get_exec_count()  # noqa: F405
            print(tmp_data)
        
        # 「メニュー項目作成情報」にレコードを登録
        # loadTableの呼び出し
        objmenu = load_table.loadTable(objdbca, 'menu_item_creation_info')  # noqa: F405
        
        # menu_dataから登録用のメニュー名を取得
        menu_name = menu_data.get('menu_name')
        
        # 「メニュー項目作成情報」登録処理のループスタート
        for column_data in column_data_list.values():
            # 登録用パラメータを作成
            column_class = column_data.get('column_class')
            parameter = {
                "menu_name": menu_name,  # メニュー名(「メニュー定義一覧」のメニュー名)
                "item_name_ja": column_data.get('item_name'),  # 項目名(ja)
                "item_name_en": column_data.get('item_name'),  # 項目名(en)
                "item_name_rest": column_data.get('item_name_rest'),  # 項目名(rest)
                "description_ja": column_data.get('description'),  # 説明(ja)
                "description_en": column_data.get('description'),  # 説明(en)
                "column_class": column_class,  # カラムクラス
                "display_order": column_data.get('display_order'),  # 表示順序
                "required": column_data.get('required'),  # 必須
                "uniqued": column_data.get('uniqued'),  # 一意制約
                "autoreg_hide_item": column_data.get('autoreg_hide_item'),  # 代入値自動登録対象外フラグ
                "autoreg_only_item": column_data.get('autoreg_only_item'),  # 対象外自動登録選択フラグ
                "remarks": column_data.get('remarks'),  # 備考
            }
            
            # カラムグループがある場合
            column_group = column_data.get('column_group')
            if column_group:
                parameter["column_group"] = column_group  # カラムグループ(「カラムグループ作成情報」のフルカラムグループ名)
            
            # カラムクラス「文字列(単一行)」用のパラメータを追加
            if column_class == "SingleTextColumn":
                parameter["string_maximum_bytes"] = column_data.get('single_maximum_bytes')  # 文字列(単一行) 最大バイト数
                parameter["string_regular_expression"] = column_data.get('single_preg_match')  # 文字列(単一行) 正規表現
                parameter["string_default_value"] = column_data.get('single_default_value')  # 文字列(単一行) 初期値
            
            # カラムクラス「文字列(複数行)」用のパラメータを追加
            if column_class == "MultiTextColumn":
                parameter["multi_string_maximum_bytes"] = column_data.get('multi_string_maximum_bytes')  # 文字列(複数行) 最大バイト数
                parameter["multi_string_regular_expression"] = column_data.get('multi_string_regular_expression')  # 文字列(複数行) 正規表現
                parameter["multi_string_default_value"] = column_data.get('multi_string_default_value')  # 文字列(複数行) 初期値
            
            # カラムクラス「整数」用のパラメータを追加
            if column_class == "NumColumn":
                parameter["integer_maximum_value"] = column_data.get('integer_maximum_value')  # 整数 最大値
                parameter["integer_minimum_value"] = column_data.get('integer_minimum_value')  # 整数 最小値
                parameter["integer_default_value"] = column_data.get('integer_default_value')  # 整数 初期値
            
            # カラムクラス「小数」用のパラメータを追加
            if column_class == "FloatColumn":
                parameter["decimal_maximum_value"] = column_data.get('decimal_maximum_value')  # 小数 最大値
                parameter["decimal_minimum_value"] = column_data.get('decimal_minimum_value')  # 小数 最小値
                parameter["decimal_digit"] = column_data.get('decimal_digit')  # 小数 桁数
                parameter["decimal_default_value"] = column_data.get('decimal_default_value')  # 小数 初期値
            
            # カラムクラス「日時」用のパラメータを追加
            if column_class == "DateTimeColumn":
                parameter["detetime_default_value"] = column_data.get('detetime_default_value')  # 日時 初期値
            
            # カラムクラス「日付」用のパラメータを追加
            if column_class == "DateColumn":
                parameter["dete_default_value"] = column_data.get('dete_default_value')  # 日付 初期値
            
            # カラムクラス「プルダウン選択」用のパラメータを追加
            if column_class == "IDColumn":
                parameter["pulldown_selection"] = column_data.get('pulldown_selection')  # プルダウン選択 メニューグループ:メニュー:項目
                parameter["pulldown_selection_default_value"] = column_data.get('pulldown_selection_default_value')  # プルダウン選択 初期値
                parameter["reference_item"] = column_data.get('reference_item')  # プルダウン選択 参照項目
            
            # カラムクラス「パスワード」用のパラメータを追加
            if column_class == "PasswordColumn":
                parameter["password_maximum_bytes"] = column_data.get('password_maximum_bytes')  # パスワード 最大バイト数
            
            # カラムクラス「ファイルアップロード」用のパラメータを追加
            if column_class == "FileUploadColumn":
                parameter["file_upload_maximum_bytes"] = column_data.get('file_upload_maximum_bytes')  # ファイルアップロード 最大バイト数
            
            # カラムクラス「ファイルアップロード(暗号化)」用のパラメータを追加
            if column_class == "FileUploadEncryptColumn":
                parameter["file_upload_encrypt_maximum_bytes"] = column_data.get('file_upload_encrypt_maximum_bytes')  # ファイルアップロード(暗号化) 最大バイト数
            
            # カラムクラス「リンク」用のパラメータを追加
            if column_class == "HostInsideLinkTextColumn":
                parameter["link_maximum_bytes"] = column_data.get('link_maximum_bytes')  # リンク 最大バイト数
                parameter["link_default_value"] = column_data.get('link_default_value')  # リンク 初期値
            
            # カラムクラス「パラメータシート参照」用のパラメータを追加 (未実装)
            # if column_class == "LinkIDColumn":
            #     parameter["parameter_sheet_reference"] = column_data.get('parameter_sheet_reference')  # パラメータシート参照
            
            parameters = {
                "parameter": parameter,
                "type": "Register"
            }
            
            # 登録を実行
            exec_result = objmenu.exec_maintenance(parameters)  # noqa: F405
            if not exec_result[0]:
                print("「メニュー項目作成情報」にレコードを登録する際にエラーが起きた。")
                raise Exception(exec_result[2])
        
        tmp_data = objmenu.get_exec_count()  # noqa: F405
        print(tmp_data)
        
        # 「メニュー(縦)作成情報」にレコードを登録
        # ####メモ：未実装
        
        # 一意制約(複数項目)用データがある場合、「一意制約(複数項目)作成情報」にレコードを登録
        unique_constraint = json.dumps(menu_data.get('unique_constraint'))
        if unique_constraint:
            # loadTableの呼び出し
            objmenu = load_table.loadTable(objdbca, 'unique_constraint_creation_info')  # noqa: F405
            parameters = {
                "parameter": {
                    "menu_name": menu_name,
                    "unique_constraint_item": str(unique_constraint)
                },
                "type": "Register"
            }
            
            # 登録を実行
            exec_result = objmenu.exec_maintenance(parameters)  # noqa: F405
            if not exec_result[0]:
                print("「一意制約(複数項目)」にレコードを登録する際にエラーが起きた。")
                raise Exception(exec_result[2])
        
        # 「メニュー作成履歴」にレコードを登録(loadTableを通さず直接データベースに登録)
        status_id = "1"  # (1:未実行)
        create_type = "1"  # (1:新規作成)
        data_list = {
            "MENU_CREATE_ID": menu_create_id,
            "STATUS_ID": status_id,
            "CREATE_TYPE": create_type,
            "MENU_MATERIAL": "",
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": user_id
        }
        primary_key_name = 'HISTORY_ID'
        ret = objdbca.table_insert(t_menu_create_history, data_list, primary_key_name)
        if not ret:
            raise Exception("「メニュー作成履歴」にレコードを登録する際にエラーが起きた。")
            
        # コミット/トランザクション終了
        objdbca.db_transaction_end(True)
        
        status = True
        msg = ''
    except Exception as e:
        # ####メモ：失敗時のメッセージはちゃんと取り出したいので、作りこみ予定。
        # ロールバック トランザクション終了
        print("なんか起きたのでロールバックする")
        objdbca.db_transaction_end(False)
        print(e)
        if len(e.args) == 2:
            status_code = '{}'.format(e.args[0])
            msg_args = '{}'.format(e.args[1])
            msg = g.appmsg.get_api_message(status_code, [msg_args])
        else:
            status_code = '999-99999'
            msg_args = '{}'.format(*e.args)
            msg = g.appmsg.get_api_message(status_code, [msg_args])

        status = False

    result_data = {
        'status': status,
        'message': msg
    }
    
    return result_data


def _initialize_execute(create_param):
    # 「メニュー定義一覧」にレコードを登録
    
    # 「カラムグループ作成情報」にレコードを登録
    
    # 「メニュー項目作成情報」にレコードを登録
    
    # 「メニュー(縦)作成情報」にレコードを登録
    
    # 「一意制約(複数項目)作成情報」にレコードを登録
    
    # 「メニュー作成履歴」にレコードを登録
    
    status = True
    message = ''
    result = {
        'status': status,
        'message': message
    }
    
    return result


def _edit_execute(create_param):
    # 「メニュー定義一覧」にレコードを登録
    
    # 「カラムグループ作成情報」にレコードを登録
    
    # 「メニュー項目作成情報」にレコードを登録
    
    # 「メニュー(縦)作成情報」にレコードを登録
    
    # 「一意制約(複数項目)作成情報」にレコードを登録
    
    # 「メニュー作成履歴」にレコードを登録
    
    status = True
    message = ''
    result = {
        'status': status,
        'message': message
    }
    
    return result
