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
import json
import re
from flask import g
# from common_libs.common.exception import AppException
from common_libs.common import *  # noqa: F403


def backyard_main(organization_id, workspace_id):
    """
        メニュー作成機能backyardメイン処理
        ARGS:
            organization_id: Organization ID
            workspace_id: Workspace ID
        RETRUN:
            
    """
    # ####メモ：エラー時の処理などほぼ未実装（とくにログへの出力系）
    # 例えば必要なデータが無いとかで処理を続けられない場合、その時点で「メニュー作成履歴」のステータスを「完(異常)」に変える処理に飛ばす。
    # その後、次の対象（メニュー作成履歴の「未実行」レコード）で処理を続けたいので「menu_create_exec」関数の中でそっちに飛ばすようにする。
    
    # テーブル/ビュー名
    t_menu_define = 'T_MENU_DEFINE'  # メニュー定義一覧
    t_menu_create_history = 'T_MENU_CREATE_HISTORY'  # メニュー作成履歴
    
    # DB接続
    objdbca = DBConnectWs(workspace_id)  # noqa: F405
    
    # 「メニュー作成履歴」から「未実行(ID:1)」のレコードを取得
    ret = objdbca.table_select(t_menu_create_history, 'WHERE STATUS_ID = %s AND DISUSE_FLAG = %s', [1, 0])
    
    # 0件なら処理を終了
    if not ret:
        print("0件なので何もせず終了。")
        return
    
    print("「未実行」ステータスのレコードの数だけ処理をループ")
    for recode in ret:
        print("-----ループスタート-----")
        history_id = str(recode.get('HISTORY_ID'))
        menu_create_id = str(recode.get('MENU_CREATE_ID'))
        create_type = str(recode.get('CREATE_TYPE'))
        
        # ステータスを「実行中」に更新
        objdbca.db_transaction_start()
        data_list = {
            "HISTORY_ID": history_id,
            "STATUS_ID": "2",  # 2: 実行中
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        ret = objdbca.table_update(t_menu_create_history, data_list, 'HISTORY_ID')
        if ret:
            objdbca.db_transaction_end(True)
        else:
            # ####メモ：ステータスの更新ができない異常終了
            # ####メモ：ログにステータスの更新に失敗した旨を出したい。
            return False
        
        # create_typeに応じたレコード登録/更新処理を実行
        if create_type == "1":  # 1: 新規作成
            print("新規作成を実行")
            res = menu_create_exec(objdbca, menu_create_id, 'create_new')
            
            # 「メニュー定義一覧」の対象レコードの「メニュー作成状態」を「2: 作成済み」に変更
            if res:
                objdbca.db_transaction_start()
                data_list = {
                    "MENU_CREATE_ID": menu_create_id,
                    "MENU_CREATE_DONE_STATUS": "2",  # 2: 作成済み
                    "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
                }
                ret = objdbca.table_update(t_menu_define, data_list, 'MENU_CREATE_ID')
                if ret:
                    objdbca.db_transaction_end(True)
                else:
                    # ####メモ：「メニュー作成状態」の更新ができない異常終了
                    # ####メモ：ログに「メニュー作成状態」の更新に失敗した旨を出したい。
                    # ####メモ：最終更新ステータスで「4: 完了(異常)」にするためresにFalseを指定
                    res = False
        
        elif create_type == "2":  # 2: 初期化
            print("初期化を実行")
            res = menu_create_exec(objdbca, menu_create_id, 'initialize')
        
        elif create_type == "3":  # 3: 編集
            print("編集を実行")
            res = menu_create_exec(objdbca, menu_create_id, 'edit')
        
        # 最終更新ステータスを指定(3: 完了, 4: 完了(異常))
        objdbca.db_transaction_start()
        status_id = 3 if res else 4
        data_list = {
            "HISTORY_ID": history_id,
            "STATUS_ID": status_id,
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        ret = objdbca.table_update(t_menu_create_history, data_list, 'HISTORY_ID')
        if ret:
            objdbca.db_transaction_end(True)
        else:
            # ####メモ：ステータスの更新ができない異常終了
            # ####メモ：ログにステータスの更新に失敗した旨を出したい。
            return False
    
    # 処理を終了
    print("メイン処理終了")
    return True


def menu_create_exec(objdbca, menu_create_id, create_type):  # noqa: C901
    """
        メニュー作成実行
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_create_id: メニュー作成の対象となる「メニュー定義一覧」のレコードのID
            create_type: 「新規作成(create_new」「初期化(initialize)」「編集(edit)」のいずれか
        RETRUN:
            
    """
    # テーブル/ビュー名
    t_comn_column_group = 'T_COMN_COLUMN_GROUP'
    
    try:
        # メニュー作成用の各テーブルからレコードを取得
        recode_t_menu_define, recode_t_menu_column_group, recode_t_menu_column, recode_t_menu_convert, recode_t_menu_unique_constraint, recode_t_menu_role, recode_t_menu_other_link \
            = _collect_menu_create_data(objdbca, menu_create_id)  # noqa: E501
        
        # テーブル名を生成
        create_table_name = 'T_CMDB_' + str(menu_create_id)
        create_table_name_jnl = 'T_CMDB_' + str(menu_create_id) + '_JNL'
        create_view_name = 'V_CMDB_' + str(menu_create_id)
        create_view_name_jnl = 'V_CMDB_' + str(menu_create_id) + '_JNL'
        
        # シートタイプを取得
        sheet_type = str(recode_t_menu_define.get('SHEET_TYPE'))
        
        # シートタイプによる処理の分岐
        file_upload_only_flag = False
        if sheet_type == "1":  # パラメータシート(ホスト/オペレーションあり)
            # テーブル作成用SQLのパス
            sql_file_path = "./sql/parameter_sheet_cmdb.sql"  # ####メモ：ファイルの格納先ディレクトリとかは定数で管理したほうがいいかも。
            
            # ループパターン(対象メニューグループのリスト)を設定
            target_menu_group_list = ['MENU_GROUP_ID_INPUT', 'MENU_GROUP_ID_SUBST', 'MENU_GROUP_ID_REF']
            
            # ファイルアップロードカラムのみの構成の場合、シートタイプを「4: パラメータシート(ファイルアップロードあり)」として扱う
            file_upload_only_flag = _check_file_upload_column(recode_t_menu_column)
        
        elif sheet_type == "2":  # データシート
            # テーブル作成用SQLのパス
            sql_file_path = "./sql/data_sheet_cmdb.sql"  # ####メモ：ファイルの格納先ディレクトリとかは定数で管理したほうがいいかも。
            
            # ループパターン(対象メニューグループのリスト)を設定
            target_menu_group_list = ['MENU_GROUP_ID_INPUT']
        
        else:
            print("シートタイプが不正")
            return False
        
        # 「新規作成」「初期化」の場合のみ、テーブル作成SQLを実行
        if create_type == 'create_new' or create_type == 'initialize':
            with open(sql_file_path, "r") as f:
                file = f.read()
                file = file.replace('____CMDB_TABLE_NAME____', create_table_name)
                file = file.replace('____CMDB_TABLE_NAME_JNL____', create_table_name_jnl)
                file = file.replace('____CMDB_VIEW_NAME____', create_view_name)
                file = file.replace('____CMDB_VIEW_NAME_JNL____', create_view_name_jnl)
                sql_list = file.split(";\n")
                for sql in sql_list:
                    if re.fullmatch(r'[\s\n\r]*', sql) is None:
                        objdbca.sql_execute(sql)
            
        # カラムグループ登録の処理に必要な形式にフォーマット
        dict_t_menu_column_group, target_column_group_list = _format_column_group_data(recode_t_menu_column_group, recode_t_menu_column)
        
        # 「他メニュー連携」を利用する処理に必要な形式にフォーマット
        dict_t_menu_other_link = _format_other_link(recode_t_menu_other_link)
        
        # トランザクション開始
        objdbca.db_transaction_start()
        
        # 「初期化」「編集」の場合のみ以下の処理を実施
        if create_type == 'initialize' or create_type == 'edit':
            # 対象のメニューについて、現在登録されているメニュー用のレコードを廃止する
            result, msg = _disuse_menu_create_recode(objdbca, recode_t_menu_define)
            
            # 利用していないメニューグループのメニューを廃止
            result, msg = _disuse_t_comn_menu(objdbca, recode_t_menu_define, target_menu_group_list)
        
        # 対象メニューグループ分だけ処理をループ
        for menu_group_col_name in target_menu_group_list:
            # 「新規作成」の場合「メニュー管理」にレコードを登録
            if create_type == 'create_new':
                result, msg = _insert_t_comn_menu(objdbca, recode_t_menu_define, menu_group_col_name)
                if not result:
                    raise Exception(msg)
            
            # 「初期化」「編集」の場合「メニュー管理」のレコードを更新および登録
            if create_type == 'initialize' or create_type == 'edit':
                result, msg = _update_t_comn_menu(objdbca, recode_t_menu_define, menu_group_col_name)
                if not result:
                    raise Exception(msg)
            
            # 「メニュー管理」に登録したレコードのuuidを取得
            menu_uuid = result[0].get('MENU_ID')
            
            # 「ロール-メニュー紐付管理」にレコードを登録
            # ####メモ：未実装。一時的な対処として、仮のレコードを登録する。
            result, msg = _insert_t_comn_role_menu_link(objdbca, menu_uuid)
            if not result:
                raise Exception(msg)
            
            # 「メニュー-テーブル紐付管理」にレコードを登録
            result, msg = _insert_t_comn_menu_table_link(objdbca, sheet_type, file_upload_only_flag, create_table_name, menu_uuid, recode_t_menu_define, recode_t_menu_unique_constraint, menu_group_col_name)  # noqa: E501
            if not result:
                raise Exception(msg)
            
            # 「カラムグループ管理」にレコードを登録(対象メニューグループ「入力用」の場合のみ実施)
            if menu_group_col_name == "MENU_GROUP_ID_INPUT":
                result, msg = _insert_t_comn_column_group(objdbca, target_column_group_list, dict_t_menu_column_group)
                if not result:
                    raise Exception(msg)
            
                # 「カラムグループ管理」から全てのレコードを取得
                recode_t_comn_column_group = objdbca.table_select(t_comn_column_group, 'WHERE DISUSE_FLAG = %s', [0])
                
                # 「カラムグループ管理」のレコードのidをkeyにしたdict型に整形
                dict_t_comn_column_group = {}
                for recode in recode_t_comn_column_group:
                    dict_t_comn_column_group[recode.get('COL_GROUP_ID')] = {
                        "pa_col_group_id": recode.get('PA_COL_GROUP_ID'),
                        "col_group_name_ja": recode.get('COL_GROUP_NAME_JA'),
                        "col_group_name_en": recode.get('COL_GROUP_NAME_EN'),
                        "full_col_group_name_ja": recode.get('FULL_COL_GROUP_NAME_JA'),
                        "full_col_group_name_en": recode.get('FULL_COL_GROUP_NAME_EN'),
                    }
            
            # 「メニュー-カラム紐付管理」にレコードを登録
            result, msg = _insert_t_comn_menu_column_link(objdbca, sheet_type, menu_uuid, dict_t_comn_column_group, dict_t_menu_column_group, recode_t_menu_column, dict_t_menu_other_link)  # noqa: E501
            if not result:
                raise Exception(msg)
            
            # 「メニュー定義-テーブル紐付管理」にレコードを登録
            result, msg = _insert_t_menu_table_link(objdbca, menu_uuid, create_table_name, create_table_name_jnl)
            if not result:
                raise Exception(msg)
        
        # ####「他メニュー連携」に対するレコード登録処理スタート
        # ####メモ：作成する項目の中で「必須」「一意制約」が両方Trueのものがあれば、レコードを登録する。
        # ####メモ：未実装。
        # 対象メニューグループ「入力用」の場合のみ実施
        # if menu_group_col_name == "MENU_GROUP_ID_INPUT":
        
        # コミット/トランザクション終了
        objdbca.db_transaction_end(True)
        
    except Exception as e:
        # ロールバック/トランザクション終了
        objdbca.db_transaction_end(False)
        
        print(e)
        
        return False
    
    return True


def _collect_menu_create_data(objdbca, menu_create_id):
    """
        メニュー作成対象の必要レコードををすべて取得する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_create_id: メニュー作成の対象となる「メニュー定義一覧」のレコードのID
        RETRUN:
            recode_t_menu_define, # 「メニュー定義一覧」から対象のレコード(1件)
            recode_t_menu_column_group, # 「カラムグループ作成情報」のレコード(全件)
            recode_t_menu_column, # 「メニュー項目作成情報」から対象のレコード(複数)
            recode_t_menu_convert, # 「メニュー(縦)作成情報」から対象のレコード(1件)
            recode_t_menu_unique_constraint, 「一意制約(複数項目)作成情報」からレコード(1件)
            recode_t_menu_role, # 「メニューロール作成情報」から対象のレコード(複数)
            recode_t_menu_other_link # 「他メニュー連携」のレコード(全件)
    """
    # テーブル/ビュー名
    t_menu_define = 'T_MENU_DEFINE'  # メニュー定義一覧
    t_menu_column_group = 'T_MENU_COLUMN_GROUP'  # カラムグループ作成情報
    t_menu_column = 'T_MENU_COLUMN'  # メニュー項目作成情報
    t_menu_convert = 'T_MENU_CONVERT'  # メニュー(縦)作成情報
    t_menu_unique_constraint = 'T_MENU_UNIQUE_CONSTRAINT'  # 一意制約(複数項目)作成情報
    t_menu_role = 'T_MENU_ROLE'  # メニューロール作成情報
    t_menu_other_link = 'T_MENU_OTHER_LINK'  # 他メニュー連携
    
    # 「メニュー定義一覧」から対象のレコードを取得
    recode_t_menu_define = objdbca.table_select(t_menu_define, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
    if not recode_t_menu_define:
        print("メニュー定義一覧に対象が無いのでエラー判定")
    recode_t_menu_define = recode_t_menu_define[0]
    
    # 「カラムグループ作成情報」から全てのレコードを取得
    recode_t_menu_column_group = objdbca.table_select(t_menu_column_group, 'WHERE DISUSE_FLAG = %s', [0])
    
    # 「メニュー項目作成情報」から対象のレコードを取得
    recode_t_menu_column = objdbca.table_select(t_menu_column, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s ORDER BY DISP_SEQ ASC', [menu_create_id, 0])  # noqa: E501
    if not recode_t_menu_column:
        print("メニュー項目作成情報に対象が無いのでエラー判定")
    
    # メニュー(縦)利用を判定
    vertical = str(recode_t_menu_define.get('VERTICAL'))
    
    recode_t_menu_convert = []
    # ####メモ：レコードの特定方法を検討。menu_create_idから特定したいが、現状column_idになっているので、テーブルの構造から考え直したほうがいい？
    # メニュー(縦)利用があれば「メニュー(縦)作成情報」から対象のレコードを取得
    # if vertical == 1:
    #     recode_t_menu_convert = objdbca.table_select(t_menu_convert, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
    #     if not recode_t_menu_column:
    #         print("メニュー(縦)作成情報に対象が無いのでエラー判定")
    
    # 「一意制約(複数項目)作成情報」から対象のレコードを取得
    recode_t_menu_unique_constraint = objdbca.table_select(t_menu_unique_constraint, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])  # noqa: E501
    recode_t_menu_unique_constraint = recode_t_menu_unique_constraint[0]
    
    # 「メニューロール作成情報」から対象のレコードを取得
    recode_t_menu_role = objdbca.table_select(t_menu_role, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
    
    # 「他メニュー連携」から全てのレコードを取得
    recode_t_menu_other_link = objdbca.table_select(t_menu_other_link, 'WHERE DISUSE_FLAG = %s', [0])
    
    return recode_t_menu_define, recode_t_menu_column_group, recode_t_menu_column, recode_t_menu_convert, recode_t_menu_unique_constraint, recode_t_menu_role, recode_t_menu_other_link  # noqa: E501


def _insert_t_comn_menu(objdbca, recode_t_menu_define, menu_group_col_name):
    """
        「メニュー管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            recode_t_menu_define: 「メニュー定義一覧」の対象のレコード
            menu_group_col_name: 対象メニューグループ名
        RETRUN:
            result, msg
    """
    # テーブル名
    t_comn_menu = 'T_COMN_MENU'
    
    try:
        # メニュー名(rest)は対象メニューグループが「代入値自動登録」「参照用」の場合は末尾に_subst, _refを結合する。
        menu_name_rest = recode_t_menu_define.get('MENU_NAME_REST')
        if menu_group_col_name == "MENU_GROUP_ID_SUBST":
            menu_name_rest = menu_name_rest + "_subst"
        elif menu_group_col_name == "MENU_GROUP_ID_REF":
            menu_name_rest = menu_name_rest + "_ref"
        
        # バリデーションチェック1: 同一のmenu_name_restが登録されている場合はエラー判定
        ret = objdbca.table_select(t_comn_menu, 'WHERE MENU_NAME_REST = %s AND DISUSE_FLAG = %s', [menu_name_rest, 0])
        if ret:
            raise Exception("同一のメニュー名(rest)のレコードがすでにあるためエラー。")
        
        # バリデーションチェック2: 同じメニューグループ内で同じmenu_name_jaかmenu_name_enが登録されている場合はエラー判定
        menu_name_ja = recode_t_menu_define.get('MENU_NAME_JA')
        menu_name_en = recode_t_menu_define.get('MENU_NAME_EN')
        target_menu_group_id = recode_t_menu_define.get(menu_group_col_name)
        ret = objdbca.table_select(t_comn_menu, 'WHERE MENU_GROUP_ID = %s AND (MENU_NAME_JA = %s OR MENU_NAME_EN = %s) AND DISUSE_FLAG = %s', [target_menu_group_id, menu_name_ja, menu_name_en, 0])  # noqa: E501
        if ret:
            raise Exception("同一のメニューグループ/メニュー名の組み合わせのレコードがすでにあるためエラー。")
        
        # 「メニュー管理」にレコードを登録
        data_list = {
            "MENU_GROUP_ID": target_menu_group_id,
            "MENU_NAME_JA": menu_name_ja,
            "MENU_NAME_EN": menu_name_en,
            "MENU_NAME_REST": menu_name_rest,
            "LOGIN_NECESSITY": "1",
            "DISP_SEQ": recode_t_menu_define.get('DISP_SEQ'),
            "AUTOFILTER_FLG": "0",
            "INITIAL_FILTER_FLG": "0",
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'MENU_ID'
        result = objdbca.table_insert(t_comn_menu, data_list, primary_key_name)
        if not result:
            raise Exception("「メニュー管理」へのレコード登録に失敗しました。")
        
    except Exception as msg:
        print(msg)
        return False, msg
    
    return result, None


def _update_t_comn_menu(objdbca, recode_t_menu_define, menu_group_col_name):
    """
        「メニュー管理」の対象レコードを更新。対象が無ければレコードを新規登録する。
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            recode_t_menu_define: 「メニュー定義一覧」の対象のレコード
            menu_group_col_name: 対象メニューグループ名
        RETRUN:
            result, msg
    """
    # テーブル名
    t_comn_menu = 'T_COMN_MENU'
    try:
        # メニュー名(rest)は対象メニューグループが「代入値自動登録」「参照用」の場合は末尾に_subst, _refを結合する。
        menu_name_rest = recode_t_menu_define.get('MENU_NAME_REST')
        if menu_group_col_name == "MENU_GROUP_ID_SUBST":
            menu_name_rest = menu_name_rest + "_subst"
        elif menu_group_col_name == "MENU_GROUP_ID_REF":
            menu_name_rest = menu_name_rest + "_ref"
        
        # 対象メニューグループIDを取得
        target_menu_group_id = recode_t_menu_define.get(menu_group_col_name)
        
        # 更新対象のレコードを特定
        ret = objdbca.table_select(t_comn_menu, 'WHERE MENU_GROUP_ID = %s AND MENU_NAME_REST = %s AND DISUSE_FLAG = %s', [target_menu_group_id, menu_name_rest, 0])  # noqa: E501
        if ret:
            menu_id = ret[0].get('MENU_ID')
            # 「メニュー管理」のレコードを更新
            data_list = {
                "MENU_ID": menu_id,
                "MENU_GROUP_ID": target_menu_group_id,
                "MENU_NAME_JA": recode_t_menu_define.get('MENU_NAME_JA'),
                "MENU_NAME_EN": recode_t_menu_define.get('MENU_NAME_EN'),
                "LOGIN_NECESSITY": "1",
                "DISP_SEQ": recode_t_menu_define.get('DISP_SEQ'),
                "AUTOFILTER_FLG": "0",
                "INITIAL_FILTER_FLG": "0",
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            result = objdbca.table_update(t_comn_menu, data_list, 'MENU_ID')
        else:
            # 更新対象が無い場合はFalseをReturnし、レコードの新規登録
            result, msg = _insert_t_comn_menu(objdbca, recode_t_menu_define, menu_group_col_name)
            if not result:
                raise Exception(msg)
        
    except Exception as msg:
        print(msg)
        return False, msg
    
    return result, None


def _insert_t_comn_role_menu_link(objdbca, menu_uuid):
    """
        「ロール-メニュー紐付管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_uuid: 対象のメニュー（「メニュー管理」のレコード）のUUID
        RETRUN:
            result, msg
    """
    # テーブル名
    t_comn_role_menu_link = 'T_COMN_ROLE_MENU_LINK'
    
    try:
        data_list = {
            "MENU_ID": menu_uuid,
            "ROLE_ID": "abc123",  # ####メモ：一時的な値
            "PRIVILEGE": 1,
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'LINK_ID'
        result = objdbca.table_insert(t_comn_role_menu_link, data_list, primary_key_name)
    
    except Exception as msg:
        print(msg)
        return False, msg
    
    return result, None


def _insert_t_comn_menu_table_link(objdbca, sheet_type, file_upload_only_flag, create_table_name, menu_uuid, recode_t_menu_define, recode_t_menu_unique_constraint, menu_group_col_name):  # noqa: E501
    """
        「メニュー-テーブル紐付管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            sheet_type: シートタイプ
            file_upload_only_flag: Trueの場合、シートタイプを「4: パラメータシート(ファイルアップロードあり)」とする
            create_table_name: 作成した対象のテーブル名
            menu_uuid: 対象のメニュー（「メニュー管理」のレコード）のUUID
            recode_t_menu_define: 「メニュー定義一覧」の対象のレコード
            recode_t_menu_unique_constraint: 「一意制約(複数項目)作成情報」の対象のレコード
            menu_group_col_name: 対象メニューグループ名
        RETRUN:
            result, msg
    """
    # テーブル名
    t_comn_menu_table_link = 'T_COMN_MENU_TABLE_LINK'
    
    try:
        # バリデーションチェック1: 同一のメニューID(MENU_ID)が登録されている場合はエラー判定
        ret = objdbca.table_select(t_comn_menu_table_link, 'WHERE MENU_ID = %s AND DISUSE_FLAG = %s', [menu_uuid, 0])
        if ret:
            raise Exception("同一のメニューIDのレコードがすでにあるためエラー。")
        
        # 対象メニューグループで変更がある値の設定
        row_insert_flag = "1"
        row_update_flag = "1"
        row_disuse_flag = "1"
        row_reuse_flag = "1"
        substitution_value_link_flag = "0"
        if menu_group_col_name == "MENU_GROUP_ID_SUBST":
            row_insert_flag = "0"
            row_update_flag = "0"
            row_disuse_flag = "0"
            row_reuse_flag = "0"
            substitution_value_link_flag = "1"
        elif menu_group_col_name == "MENU_GROUP_ID_REF":
            row_insert_flag = "0"
            row_update_flag = "0"
            row_disuse_flag = "0"
            row_reuse_flag = "0"
        
        # 一意制約(複数項目)の値を取得(対象メニューグループが「入力用」の場合のみ)
        unique_constraint = None
        if menu_group_col_name == "MENU_GROUP_ID_INPUT" and recode_t_menu_unique_constraint:
            unique_constraint = str(recode_t_menu_unique_constraint.get('UNIQUE_CONSTRAINT_ITEM'))
        
        # シートタイプが「1:パラメータシート（ホスト/オペレーションあり）」の場合は、「ホストとオペレーション」の一意制約(複数項目)を追加(対象メニューグループが「入力用」の場合のみ)
        if menu_group_col_name == "MENU_GROUP_ID_INPUT" and sheet_type == "1":
            if unique_constraint:
                tmp_unique_constraint = json.loads(unique_constraint)
                add_unique_constraint = ["operation_name", "host_name"]
                if tmp_unique_constraint:
                    tmp_unique_constraint.insert(0, add_unique_constraint)
                else:
                    tmp_unique_constraint = add_unique_constraint
                unique_constraint = json.dumps(tmp_unique_constraint)
            else:
                unique_constraint = '[["operation_name", "host_name"]]'
        
        # シートタイプが「1: パラメータシート（ホスト/オペレーションあり）」かつfile_upload_only_flagがTrueの場合、シートタイプを「4: パラメータシート（ファイルアップロードあり）」とする。
        if sheet_type == "1" and file_upload_only_flag:
            sheet_type = "4"
            
        # 「メニュー-テーブル紐付管理」にレコードを登録
        data_list = {
            "MENU_ID": menu_uuid,
            "TABLE_NAME": create_table_name,  # ####メモ：VIEWを使う場合はここを修正する。
            "VIEW_NAME": None,  # ####メモ：VIEWを使う場合はここを修正する。
            "PK_COLUMN_NAME_REST": "uuid",
            "MENU_INFO_JA": recode_t_menu_define.get('DESCRIPTION_JA'),
            "MENU_INFO_EN": recode_t_menu_define.get('DESCRIPTION_EN'),
            "SHEET_TYPE": sheet_type,
            "HISTORY_TABLE_FLAG": "1",
            "INHERIT": "0",
            "VERTICAL": recode_t_menu_define.get('VERTICAL'),
            "ROW_INSERT_FLAG": row_insert_flag,
            "ROW_UPDATE_FLAG": row_update_flag,
            "ROW_DISUSE_FLAG": row_disuse_flag,
            "ROW_REUSE_FLAG": row_reuse_flag,
            "SUBSTITUTION_VALUE_LINK_FLAG": substitution_value_link_flag,
            "UNIQUE_CONSTRAINT": unique_constraint,
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'TABLE_DEFINITION_ID'
        result = objdbca.table_insert(t_comn_menu_table_link, data_list, primary_key_name)
    
    except Exception as msg:
        print(msg)
        return False, msg
    
    return result, None


def _insert_t_comn_column_group(objdbca, target_column_group_list, dict_t_menu_column_group):
    """
        「カラムグループ管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            target_column_group_list: シートタイプ
            dict_t_menu_column_group: 作成した対象のテーブル名
        RETRUN:
            result, msg
    """
    # テーブル名
    t_comn_column_group = 'T_COMN_COLUMN_GROUP'
    
    try:
        for column_group_id in target_column_group_list:
            target_column_group_data = dict_t_menu_column_group.get(column_group_id)
            if not target_column_group_data:
                continue
            
            # 対象のカラムグループのフルカラムグループ名(ja/en)がすでに登録されている場合はスキップ。
            full_col_group_name_ja = target_column_group_data.get('full_col_group_name_ja')
            full_col_group_name_en = target_column_group_data.get('full_col_group_name_en')
            ret = objdbca.table_select(t_comn_column_group, 'WHERE (FULL_COL_GROUP_NAME_JA = %s OR FULL_COL_GROUP_NAME_EN = %s) AND DISUSE_FLAG = %s', [full_col_group_name_ja, full_col_group_name_en, 0])  # noqa: E501
            if ret:
                continue
            
            # 親カラムグループがある場合は、親カラムグループのIDを取得
            pa_target_id = None
            pa_col_group_id = target_column_group_data.get('pa_col_group_id')
            if pa_col_group_id:
                pa_column_group_data = dict_t_menu_column_group.get(pa_col_group_id)
                pa_full_col_group_name_ja = pa_column_group_data.get('full_col_group_name_ja')
                pa_full_col_group_name_en = pa_column_group_data.get('full_col_group_name_en')
                ret = objdbca.table_select(t_comn_column_group, 'WHERE (FULL_COL_GROUP_NAME_JA = %s OR FULL_COL_GROUP_NAME_EN = %s) AND DISUSE_FLAG = %s', [pa_full_col_group_name_ja, pa_full_col_group_name_en, 0])  # noqa: E501
                if not ret:
                    raise Exception("「カラムグループ管理」に対象の親カラムグループのレコードが無いためエラー")
                
                pa_target_id = ret[0].get('COL_GROUP_ID')
                                
            # 「カラムグループ管理」に登録を実行
            data_list = {
                "PA_COL_GROUP_ID": pa_target_id,
                "COL_GROUP_NAME_JA": target_column_group_data.get('col_group_name_ja'),
                "COL_GROUP_NAME_EN": target_column_group_data.get('col_group_name_en'),
                "FULL_COL_GROUP_NAME_JA": full_col_group_name_ja,
                "FULL_COL_GROUP_NAME_EN": full_col_group_name_en,
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'COL_GROUP_ID'
            objdbca.table_insert(t_comn_column_group, data_list, primary_key_name)
        
    except Exception as msg:
        print(msg)
        return False, msg
    
    return True, None


def _insert_t_comn_menu_column_link(objdbca, sheet_type, menu_uuid, dict_t_comn_column_group, dict_t_menu_column_group, recode_t_menu_column, dict_t_menu_other_link):  # noqa: E501
    """
        「メニュー-カラム紐付管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            sheet_type: シートタイプ
            menu_uuid: メニュー作成の対象となる「メニュー管理」のレコードのID
            dict_t_comn_column_group: 「カラムグループ管理」のレコードのidをkeyにしたdict
            dict_t_menu_column_group: 「カラムグループ作成情報」のレコードのidをkeyにしたdict
            recode_t_menu_column：「メニュー項目作成情報」の対象のレコード一覧
            dict_t_menu_other_link: 「他メニュー連携」のレコードのidをkeyにしたdict
        RETRUN:
            boolean, msg
    """
    try:
        # テーブル名
        t_comn_menu_column_link = 'T_COMN_MENU_COLUMN_LINK'
        
        # 表示順序用変数
        disp_seq_num = 10
        
        # 「項番」用のレコードを登録
        res_valid = _check_column_validation(objdbca, menu_uuid, "uuid")  # ####メモ：メッセージ一覧から取得する
        if not res_valid:
            raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
        
        data_list = {
            "MENU_ID": menu_uuid,
            "COLUMN_NAME_JA": "項番",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_EN": "uuid",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_REST": "uuid",  # ####メモ：メッセージ一覧から取得する
            "COL_GROUP_ID": None,
            "COLUMN_CLASS": 1,  # SingleTextColumn
            "COLUMN_DISP_SEQ": disp_seq_num,
            "REF_TABLE_NAME": None,
            "REF_PKEY_NAME": None,
            "REF_COL_NAME": None,
            "REF_SORT_CONDITIONS": None,
            "REF_MULTI_LANG": 0,  # False
            "SENSITIVE_COL_NAME": None,
            "FILE_UPLOAD_PLACE": None,
            "COL_NAME": "ROW_ID",
            "SAVE_TYPE": None,
            "AUTO_INPUT": 1,  # True
            "INPUT_ITEM": 0,  # False
            "VIEW_ITEM": 1,  # True
            "UNIQUE_ITEM": 1,  # True
            "REQUIRED_ITEM": 1,  # True
            "AUTOREG_HIDE_ITEM": 0,  # False
            "AUTOREG_ONLY_ITEM": 0,  # False
            "INITIAL_VALUE": None,
            "VALIDATE_OPTION": None,
            "BEFORE_VALIDATE_REGISTER": None,
            "AFTER_VALIDATE_REGISTER": None,
            "DESCRIPTION_JA": "自動採番のため編集不可。実行処理種別が【登録】の場合、空白のみ可。",  # ####メモ：メッセージ一覧から取得する
            "DESCRIPTION_EN": "Cannot edit because of auto-numbering. Must be blank when execution process type is [Register].",  # ####メモ：メッセージ一覧から取得する  # noqa: E501
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
        # 表示順序を加算
        disp_seq_num = int(disp_seq_num) + 10
        
        # シートタイプが「1: パラメータシート（ホスト/オペレーションあり）」の場合のみ
        if sheet_type == "1":
            # 「ホスト名」用のレコードを作成
            res_valid = _check_column_validation(objdbca, menu_uuid, "host_name")  # ####メモ：メッセージ一覧から取得する
            if not res_valid:
                raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
            
            data_list = {
                "MENU_ID": menu_uuid,
                "COLUMN_NAME_JA": "ホスト名",  # ####メモ：メッセージ一覧から取得する
                "COLUMN_NAME_EN": "Host name",  # ####メモ：メッセージ一覧から取得する
                "COLUMN_NAME_REST": "host_name",  # ####メモ：メッセージ一覧から取得する
                "COL_GROUP_ID": None,
                "COLUMN_CLASS": 7,  # IDColumn
                "COLUMN_DISP_SEQ": disp_seq_num,
                "REF_TABLE_NAME": "T_ANSC_DEVICE",
                "REF_PKEY_NAME": "SYSTEM_ID",
                "REF_COL_NAME": "HOST_NAME",
                "REF_SORT_CONDITIONS": None,
                "REF_MULTI_LANG": 0,  # False
                "SENSITIVE_COL_NAME": None,
                "FILE_UPLOAD_PLACE": None,
                "COL_NAME": "HOST_ID",
                "SAVE_TYPE": None,
                "AUTO_INPUT": 0,  # False
                "INPUT_ITEM": 1,  # True
                "VIEW_ITEM": 1,  # True
                "UNIQUE_ITEM": 0,  # False
                "REQUIRED_ITEM": 1,  # True
                "AUTOREG_HIDE_ITEM": 0,  # False
                "AUTOREG_ONLY_ITEM": 0,  # False
                "INITIAL_VALUE": None,
                "VALIDATE_OPTION": None,
                "BEFORE_VALIDATE_REGISTER": None,
                "AFTER_VALIDATE_REGISTER": None,
                "DESCRIPTION_JA": "ホストを選択",  # ####メモ：メッセージ一覧から取得する
                "DESCRIPTION_EN": "Select host",  # ####メモ：メッセージ一覧から取得する
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'COLUMN_DEFINITION_ID'
            objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
            
            # 表示順序を加算
            disp_seq_num = int(disp_seq_num) + 10
            
            # 「オペレーション名」用のレコードを作成
            res_valid = _check_column_validation(objdbca, menu_uuid, "operation_name")  # ####メモ：メッセージ一覧から取得する
            if not res_valid:
                raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
            
            data_list = {
                "MENU_ID": menu_uuid,
                "COLUMN_NAME_JA": "オペレーション名",  # ####メモ：メッセージ一覧から取得する
                "COLUMN_NAME_EN": "Operation name",  # ####メモ：メッセージ一覧から取得する
                "COLUMN_NAME_REST": "operation_name",  # ####メモ：メッセージ一覧から取得する
                "COL_GROUP_ID": "0000001",  # カラムグループ「オペレーション」
                "COLUMN_CLASS": 7,  # IDColumn
                "COLUMN_DISP_SEQ": disp_seq_num,
                "REF_TABLE_NAME": "V_COMN_OPERATION",
                "REF_PKEY_NAME": "OPERATION_ID",
                "REF_COL_NAME": "OPERATION_DATE_NAME",
                "REF_SORT_CONDITIONS": None,
                "REF_MULTI_LANG": 0,  # False
                "SENSITIVE_COL_NAME": None,
                "FILE_UPLOAD_PLACE": None,
                "COL_NAME": "OPERATION_ID",
                "SAVE_TYPE": None,
                "AUTO_INPUT": 0,  # False
                "INPUT_ITEM": 1,  # True
                "VIEW_ITEM": 1,  # True
                "UNIQUE_ITEM": 0,  # False
                "REQUIRED_ITEM": 1,  # True
                "AUTOREG_HIDE_ITEM": 0,  # False
                "AUTOREG_ONLY_ITEM": 0,  # False
                "INITIAL_VALUE": None,
                "VALIDATE_OPTION": None,
                "BEFORE_VALIDATE_REGISTER": None,
                "AFTER_VALIDATE_REGISTER": None,
                "DESCRIPTION_JA": "オペレーションを選択",  # ####メモ：メッセージ一覧から取得する
                "DESCRIPTION_EN": "Select operation",  # ####メモ：メッセージ一覧から取得する
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'COLUMN_DEFINITION_ID'
            objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
            
            # 表示順序を加算
            disp_seq_num = int(disp_seq_num) + 10
            
            # 「代入順序」用のレコードを作成
            # ####メモ：本来だったら縦メニューがある場合しか必要ないので、縦利用の場合に「INPUT_ITEM」「VIEW_ITEM」などをTrue/Falseどちらかするなど、分岐が必要。
            res_valid = _check_column_validation(objdbca, menu_uuid, "input_order")  # ####メモ：メッセージ一覧から取得する
            if not res_valid:
                raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
            
            data_list = {
                "MENU_ID": menu_uuid,
                "COLUMN_NAME_JA": "代入順序",  # ####メモ：メッセージ一覧から取得する
                "COLUMN_NAME_EN": "Input order",  # ####メモ：メッセージ一覧から取得する
                "COLUMN_NAME_REST": "input_order",  # ####メモ：メッセージ一覧から取得する
                "COL_GROUP_ID": None,
                "COLUMN_CLASS": 3,  # NumColumn
                "COLUMN_DISP_SEQ": disp_seq_num,
                "REF_TABLE_NAME": None,
                "REF_PKEY_NAME": None,
                "REF_COL_NAME": None,
                "REF_SORT_CONDITIONS": None,
                "REF_MULTI_LANG": 0,  # False
                "SENSITIVE_COL_NAME": None,
                "FILE_UPLOAD_PLACE": None,
                "COL_NAME": "INPUT_ORDER",
                "SAVE_TYPE": None,
                "AUTO_INPUT": 0,  # False
                "INPUT_ITEM": 0,  # False
                "VIEW_ITEM": 0,  # False
                "UNIQUE_ITEM": 0,  # False
                "REQUIRED_ITEM": 0,  # False
                "AUTOREG_HIDE_ITEM": 0,  # False
                "AUTOREG_ONLY_ITEM": 0,  # False
                "INITIAL_VALUE": None,
                "VALIDATE_OPTION": None,
                "BEFORE_VALIDATE_REGISTER": None,
                "AFTER_VALIDATE_REGISTER": None,
                "DESCRIPTION_JA": "メニューの縦メニューから横メニューに変換する際に、左から昇順で入力されます。",  # ####メモ：メッセージ一覧から取得する
                "DESCRIPTION_EN": "When converting from the vertical menu to the horizontal menu, items will be arranged in ascending order from left to right.",  # ####メモ：メッセージ一覧から取得する  # noqa: E501
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'COLUMN_DEFINITION_ID'
            objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
            
            # 表示順序を加算
            disp_seq_num = int(disp_seq_num) + 10
        
        # 「メニュー作成機能で作成した項目」の対象の数だけループスタート
        for recode in recode_t_menu_column:
            column_class = str(recode.get('COLUMN_CLASS'))
            
            # 初期値に登録する値を生成
            initial_value = _create_initial_value(recode)
            
            # バリデーションに登録する値を生成
            validate_option = _create_validate_option(recode)
            
            # IDColumn用の値
            ref_table_name = None
            ref_pkey_name = None
            ref_col_name = None
            ref_sort_conditions = None
            ref_multi_lang = 0
            
            # カラムクラスが「プルダウン選択」の場合、「他メニュー連携」のレコードからIDColumnに必要なデータを取得し変数に格納
            if column_class == "7":
                other_menu_link_id = recode.get('OTHER_MENU_LINK_ID')
                target_other_menu_link_recode = dict_t_menu_other_link.get(other_menu_link_id)
                ref_table_name = target_other_menu_link_recode.get('REF_TABLE_NAME')
                ref_pkey_name = target_other_menu_link_recode.get('REF_PKEY_NAME')
                ref_col_name = target_other_menu_link_recode.get('REF_COL_NAME')
                ref_sort_conditions = target_other_menu_link_recode.get('REF_SORT_CONDITIONS')
                ref_multi_lang = target_other_menu_link_recode.get('REF_MULTI_LANG')
            
            # 「カラムグループ作成情報」のIDから同じフルカラムグループ名の対象を「カラムグループ管理」から探しIDを指定
            col_group_id = None
            tmp_col_group_id = recode.get('CREATE_COL_GROUP_ID')
            target_t_menu_column_group = dict_t_menu_column_group.get(tmp_col_group_id)
            if target_t_menu_column_group:
                t_full_col_group_name_ja = target_t_menu_column_group.get('full_col_group_name_ja')
                t_full_col_group_name_en = target_t_menu_column_group.get('full_col_group_name_en')
                for key_id, target_t_comn_column_group in dict_t_comn_column_group.items():
                    c_full_col_group_name_ja = target_t_comn_column_group.get('full_col_group_name_ja')
                    c_full_col_group_name_en = target_t_comn_column_group.get('full_col_group_name_en')
                    # フルカラムグループ名が一致している対象のカラムグループ管理IDを指定
                    if (t_full_col_group_name_ja == c_full_col_group_name_ja) or (t_full_col_group_name_en == c_full_col_group_name_en):
                        col_group_id = key_id
                        break
            
            # 「メニュー作成機能で作成した項目」用のレコードを作成
            column_name_rest = recode.get('COLUMN_NAME_REST')
            res_valid = _check_column_validation(objdbca, menu_uuid, column_name_rest)
            if not res_valid:
                raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
            
            data_list = {
                "MENU_ID": menu_uuid,
                "COLUMN_NAME_JA": recode.get('COLUMN_NAME_JA'),
                "COLUMN_NAME_EN": recode.get('COLUMN_NAME_EN'),
                "COLUMN_NAME_REST": column_name_rest,
                "COL_GROUP_ID": col_group_id,
                "COLUMN_CLASS": column_class,
                "COLUMN_DISP_SEQ": disp_seq_num,
                "REF_TABLE_NAME": ref_table_name,
                "REF_PKEY_NAME": ref_pkey_name,
                "REF_COL_NAME": ref_col_name,
                "REF_SORT_CONDITIONS": ref_sort_conditions,
                "REF_MULTI_LANG": ref_multi_lang,
                "SENSITIVE_COL_NAME": None,
                "FILE_UPLOAD_PLACE": None,
                "COL_NAME": "DATA_JSON",
                "SAVE_TYPE": "JSON",
                "AUTO_INPUT": 0,  # False
                "INPUT_ITEM": 1,  # True
                "VIEW_ITEM": 1,  # True
                "UNIQUE_ITEM": recode.get('UNIQUED'),
                "REQUIRED_ITEM": recode.get('REQUIRED'),
                "AUTOREG_HIDE_ITEM": 0,  # False
                "AUTOREG_ONLY_ITEM": 0,  # False
                "INITIAL_VALUE": initial_value,
                "VALIDATE_OPTION": validate_option,
                "BEFORE_VALIDATE_REGISTER": None,
                "AFTER_VALIDATE_REGISTER": None,
                "DESCRIPTION_JA": recode.get('DESCRIPTION_JA'),
                "DESCRIPTION_EN": recode.get('DESCRIPTION_EN'),
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'COLUMN_DEFINITION_ID'
            objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
            
            # 表示順序を加算
            disp_seq_num = int(disp_seq_num) + 10
        
        # 「備考」用のレコードを作成
        res_valid = _check_column_validation(objdbca, menu_uuid, "remarks")  # ####メモ：メッセージ一覧から取得する
        if not res_valid:
            raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
        
        data_list = {
            "MENU_ID": menu_uuid,
            "COLUMN_NAME_JA": "備考",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_EN": "Remarks",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_REST": "remarks",  # ####メモ：メッセージ一覧から取得する
            "COL_GROUP_ID": None,
            "COLUMN_CLASS": 12,  # NoteColumn
            "COLUMN_DISP_SEQ": disp_seq_num,
            "REF_TABLE_NAME": None,
            "REF_PKEY_NAME": None,
            "REF_COL_NAME": None,
            "REF_SORT_CONDITIONS": None,
            "REF_MULTI_LANG": 0,  # False
            "SENSITIVE_COL_NAME": None,
            "FILE_UPLOAD_PLACE": None,
            "COL_NAME": "NOTE",
            "SAVE_TYPE": None,
            "AUTO_INPUT": 0,  # False
            "INPUT_ITEM": 1,  # True
            "VIEW_ITEM": 1,  # True
            "UNIQUE_ITEM": 0,  # False
            "REQUIRED_ITEM": 0,  # False
            "AUTOREG_HIDE_ITEM": 0,  # False
            "AUTOREG_ONLY_ITEM": 0,  # False
            "INITIAL_VALUE": None,
            "VALIDATE_OPTION": None,
            "BEFORE_VALIDATE_REGISTER": None,
            "AFTER_VALIDATE_REGISTER": None,
            "DESCRIPTION_JA": "自由記述欄。レコードの廃止・復活時にも記載可能。",  # ####メモ：メッセージ一覧から取得する
            "DESCRIPTION_EN": "Comments section. Can comment when removing or res...",  # ####メモ：メッセージ一覧から取得する
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
        # 表示順序を加算
        disp_seq_num = int(disp_seq_num) + 10
        
        # 「廃止フラグ」用のレコードを作成
        res_valid = _check_column_validation(objdbca, menu_uuid, "discard")  # ####メモ：メッセージ一覧から取得する
        if not res_valid:
            raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
        
        data_list = {
            "MENU_ID": menu_uuid,
            "COLUMN_NAME_JA": "廃止フラグ",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_EN": "Discard",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_REST": "discard",  # ####メモ：メッセージ一覧から取得する
            "COL_GROUP_ID": None,
            "COLUMN_CLASS": 1,  # SingleTextColumn
            "COLUMN_DISP_SEQ": disp_seq_num,
            "REF_TABLE_NAME": None,
            "REF_PKEY_NAME": None,
            "REF_COL_NAME": None,
            "REF_SORT_CONDITIONS": None,
            "REF_MULTI_LANG": 0,  # False
            "SENSITIVE_COL_NAME": None,
            "FILE_UPLOAD_PLACE": None,
            "COL_NAME": "DISUSE_FLAG",
            "SAVE_TYPE": None,
            "AUTO_INPUT": 1,  # True
            "INPUT_ITEM": 0,  # False
            "VIEW_ITEM": 1,  # True
            "UNIQUE_ITEM": 0,  # False
            "REQUIRED_ITEM": 1,  # True
            "AUTOREG_HIDE_ITEM": 0,  # False
            "AUTOREG_ONLY_ITEM": 0,  # False
            "INITIAL_VALUE": None,
            "VALIDATE_OPTION": None,
            "BEFORE_VALIDATE_REGISTER": None,
            "AFTER_VALIDATE_REGISTER": None,
            "DESCRIPTION_JA": "廃止フラグ。復活以外のオペレーションは不可",  # ####メモ：メッセージ一覧から取得する
            "DESCRIPTION_EN": "Discard flag. Cannot do operation other than resto...",  # ####メモ：メッセージ一覧から取得する
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
        # 表示順序を加算
        disp_seq_num = int(disp_seq_num) + 10
        
        # 「最終更新日時」用のレコードを作成
        res_valid = _check_column_validation(objdbca, menu_uuid, "last_update_date_time")  # ####メモ：メッセージ一覧から取得する
        if not res_valid:
            raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
        
        data_list = {
            "MENU_ID": menu_uuid,
            "COLUMN_NAME_JA": "最終更新日時",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_EN": "Last update date/time",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_REST": "last_update_date_time",  # ####メモ：メッセージ一覧から取得する
            "COL_GROUP_ID": None,
            "COLUMN_CLASS": 13,  # LastUpdateDateColumn
            "COLUMN_DISP_SEQ": disp_seq_num,
            "REF_TABLE_NAME": None,
            "REF_PKEY_NAME": None,
            "REF_COL_NAME": None,
            "REF_SORT_CONDITIONS": None,
            "REF_MULTI_LANG": 0,  # False
            "SENSITIVE_COL_NAME": None,
            "FILE_UPLOAD_PLACE": None,
            "COL_NAME": "LAST_UPDATE_TIMESTAMP",
            "SAVE_TYPE": None,
            "AUTO_INPUT": 1,  # True
            "INPUT_ITEM": 0,  # False
            "VIEW_ITEM": 1,  # True
            "UNIQUE_ITEM": 0,  # False
            "REQUIRED_ITEM": 1,  # True
            "AUTOREG_HIDE_ITEM": 0,  # False
            "AUTOREG_ONLY_ITEM": 0,  # False
            "INITIAL_VALUE": None,
            "VALIDATE_OPTION": None,
            "BEFORE_VALIDATE_REGISTER": None,
            "AFTER_VALIDATE_REGISTER": None,
            "DESCRIPTION_JA": "レコードの最終更新日。自動登録のため編集不可。",  # ####メモ：メッセージ一覧から取得する
            "DESCRIPTION_EN": "Last update date of record. Cannot edit because of...",  # ####メモ：メッセージ一覧から取得する
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
        # 表示順序を加算
        disp_seq_num = int(disp_seq_num) + 10
        
        # 「最終更新者」用のレコードを作成
        res_valid = _check_column_validation(objdbca, menu_uuid, "last_updated_user")  # ####メモ：メッセージ一覧から取得する
        if not res_valid:
            raise Exception("「メニュー-カラム紐付管理」に同じメニューとカラム名(rest)の組み合わせが既に存在している。")
        
        data_list = {
            "MENU_ID": menu_uuid,
            "COLUMN_NAME_JA": "最終更新者",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_EN": "Last updated by",  # ####メモ：メッセージ一覧から取得する
            "COLUMN_NAME_REST": "last_updated_user",  # ####メモ：メッセージ一覧から取得する
            "COL_GROUP_ID": None,
            "COLUMN_CLASS": 14,  # LastUpdateUserColumn
            "COLUMN_DISP_SEQ": disp_seq_num,
            "REF_TABLE_NAME": None,
            "REF_PKEY_NAME": None,
            "REF_COL_NAME": None,
            "REF_SORT_CONDITIONS": None,
            "REF_MULTI_LANG": 0,  # False
            "SENSITIVE_COL_NAME": None,
            "FILE_UPLOAD_PLACE": None,
            "COL_NAME": "LAST_UPDATE_USER",
            "SAVE_TYPE": None,
            "AUTO_INPUT": 1,  # True
            "INPUT_ITEM": 0,  # False
            "VIEW_ITEM": 1,  # True
            "UNIQUE_ITEM": 0,  # False
            "REQUIRED_ITEM": 1,  # True
            "AUTOREG_HIDE_ITEM": 0,  # False
            "AUTOREG_ONLY_ITEM": 0,  # False
            "INITIAL_VALUE": None,
            "VALIDATE_OPTION": None,
            "BEFORE_VALIDATE_REGISTER": None,
            "AFTER_VALIDATE_REGISTER": None,
            "DESCRIPTION_JA": "更新者。ログインユーザのIDが自動的に登録される。編集不可。",  # ####メモ：メッセージ一覧から取得する
            "DESCRIPTION_EN": "Updated by. Login user ID is automatically registe...",  # ####メモ：メッセージ一覧から取得する
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
    except Exception as msg:
        print(msg)
                
        return False, msg
    
    return True, None


def _insert_t_menu_table_link(objdbca, menu_uuid, create_table_name, create_table_name_jnl):
    """
        「メニュー定義-テーブル紐付管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_uuid: 対象のメニュー（「メニュー管理」のレコード）のUUID
            create_table_name: 作成した対象のテーブル名
            create_table_name_jnl: 作成した対象の履歴用テーブル名
        RETRUN:
            result, msg
    """
    # テーブル名
    t_menu_table_link = 'T_MENU_TABLE_LINK'
    
    try:
        data_list = {
            "MENU_ID": menu_uuid,
            "TABLE_NAME": create_table_name,
            "KEY_COL_NAME": "ROW_ID",
            "TABLE_NAME_JNL": create_table_name_jnl,
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'MENU_TABLE_LINK_ID'
        result = objdbca.table_insert(t_menu_table_link, data_list, primary_key_name)
        
    except Exception as msg:
        print(msg)
        return False, msg
    
    return result, None


def _create_validate_option(recode):
    """
        「メニュー-カラム紐付管理」メニューのテーブルにレコードを追加する際のvalidate_optionの値を生成する。
        ARGS:
            recode: 「メニュー項目作成情報」のレコード
        RETRUN:
            validate_option
    """
    validate_option = None
    tmp_validate_option = {}
    column_class = str(recode.get('COLUMN_CLASS'))
    
    # カラムクラスに応じて処理を分岐
    if column_class == "1":  # SingleTextColumn
        single_max_length = str(recode.get('SINGLE_MAX_LENGTH'))
        single_preg_match = str(recode.get('SINGLE_PREG_MATCH'))
        tmp_validate_option['min_length'] = "0"
        tmp_validate_option['max_length'] = single_max_length
        if single_preg_match:
            tmp_validate_option['preg_match'] = single_preg_match
        
    elif column_class == "2":  # MultiTextColumn
        multi_max_length = str(recode.get('MULTI_MAX_LENGTH'))
        multi_preg_match = str(recode.get('MULTI_PREG_MATCH'))
        tmp_validate_option['min_length'] = "0"
        tmp_validate_option['max_length'] = multi_max_length
        if multi_preg_match:
            tmp_validate_option['preg_match'] = multi_preg_match
        
    elif column_class == "3":  # NumColumn
        num_min = str(recode.get('NUM_MIN'))
        num_max = str(recode.get('NUM_MAX'))
        if num_min:
            tmp_validate_option["int_min"] = num_min
        if num_max:
            tmp_validate_option["int_max"] = num_max
        
    elif column_class == "4":  # FloatColumn
        float_min = str(recode.get('FLOAT_MIN'))
        float_max = str(recode.get('FLOAT_MAX'))
        float_digit = str(recode.get('FLOAT_DIGIT'))
        if float_min:
            tmp_validate_option["float_min"] = float_min
        if float_max:
            tmp_validate_option["float_max"] = float_max
        if float_digit:
            tmp_validate_option["float_digit"] = float_digit
        else:
            tmp_validate_option["float_digit"] = "14"  # 桁数の指定が無い場合「14」を固定値とする。
        
    elif column_class == "8":  # PasswordColumn
        password_max_length = str(recode.get('PASSWORD_MAX_LENGTH'))
        tmp_validate_option['min_length'] = "0"
        tmp_validate_option['max_length'] = password_max_length
    elif column_class == "9":  # FileUploadColumn
        upload_max_size = str(recode.get('FILE_UPLOAD_MAX_SIZE'))
        if upload_max_size:
            tmp_validate_option["upload_max_size"] = upload_max_size
        
    elif column_class == "10":  # HostInsideLinkTextColumn
        link_max_length = str(recode.get('LINK_MAX_LENGTH'))
        tmp_validate_option['min_length'] = "0"
        tmp_validate_option['max_length'] = link_max_length
    
    # tmp_validate_optionをjson形式に変換
    if tmp_validate_option:
        validate_option = json.dumps(tmp_validate_option)
    
    return validate_option


def _create_initial_value(recode):
    """
        「メニュー-カラム紐付管理」メニューのテーブルにレコードを追加する際のinitial_valueの値を生成する。
        ARGS:
            recode: 「メニュー項目作成情報」のレコード
        RETRUN:
            initial_value
    """
    column_class = str(recode.get('COLUMN_CLASS'))
    
    # カラムクラスに応じて処理を分岐
    initial_value = None
    if column_class == "1":  # SingleTextColumn
        initial_value = recode.get('SINGLE_DEFAULT_VALUE')
    elif column_class == "2":  # MultiTextColumn
        initial_value = recode.get('MULTI_DEFAULT_VALUE')
    elif column_class == "3":  # NumColumn
        initial_value = recode.get('NUM_DEFAULT_VALUE')
    elif column_class == "4":  # FloatColumn
        initial_value = recode.get('FLOAT_DEFAULT_VALUE')
    elif column_class == "5":  # DateTimeColumn
        initial_value = recode.get('DATETIME_DEFAULT_VALUE')
    elif column_class == "6":  # DateColumn
        initial_value = recode.get('DATE_DEFAULT_VALUE')
    elif column_class == "7":  # IDColumn
        initial_value = recode.get('OTHER_MENU_LINK_DEFAULT_VALUE')
    elif column_class == "10":  # HostInsideLinkTextColumn
        initial_value = recode.get('LINK_DEFAULT_VALUE')
    
    # 「空白」の場合もデータベース上にNullを登録させるためNoneを挿入
    if not initial_value:
        initial_value = None
    
    return initial_value


def _check_column_validation(objdbca, menu_uuid, column_name_rest):
    """
        「メニュー-カラム紐付管理」メニューのテーブルにレコードを追加する際に、「MENU_ID」と「COLUMN_NAME_REST」で同じ組み合わせがあるかどうかのチェックをする。
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_uuid: メニュー作成の対象となる「メニュー管理」のレコードのID
            column_name_rest: カラム名(rest)
        RETRUN:
            boolean
    """
    # テーブル名
    t_comn_menu_column_link = 'T_COMN_MENU_COLUMN_LINK'
    
    # 「メニュー-カラム紐付管理」に同じメニューIDとカラム名(rest)のレコードが存在する場合はFalseをreturnする。
    ret = objdbca.table_select(t_comn_menu_column_link, 'WHERE MENU_ID = %s AND COLUMN_NAME_REST = %s AND DISUSE_FLAG = %s', [menu_uuid, column_name_rest, 0])  # noqa: E501
    if ret:
        return False
    
    return True


def _format_column_group_data(recode_t_menu_column_group, recode_t_menu_column):
    """
        カラムグループ登録の処理に必要な形式(idをkeyにしたdict型)にフォーマット
        ARGS:
            recode_t_menu_column_group: 「カラムグループ作成情報」のレコード一覧
            recode_t_menu_column: 「メニュー項目作成情報」のレコード一覧
        RETRUN:
            dict_t_menu_column_group: 「カラムグループ作成情報」のレコードのidをkeyにしたdict型に整形
            target_column_group_list: 使用されているカラムグループIDの親をたどり、最終的に使用されるすべてのカラムグループIDのlist
            
    """
    # 「カラムグループ作成情報」のレコードのidをkeyにしたdict型に整形
    dict_t_menu_column_group = {}
    for recode in recode_t_menu_column_group:
        dict_t_menu_column_group[recode.get('CREATE_COL_GROUP_ID')] = {
            "pa_col_group_id": recode.get('PA_COL_GROUP_ID'),
            "col_group_name_ja": recode.get('COL_GROUP_NAME_JA'),
            "col_group_name_en": recode.get('COL_GROUP_NAME_EN'),
            "full_col_group_name_ja": recode.get('FULL_COL_GROUP_NAME_JA'),
            "full_col_group_name_en": recode.get('FULL_COL_GROUP_NAME_EN'),
        }
    
    # 「メニュー項目作成情報」のレコードから、使用されているカラムグループのIDを抽出
    tmp_target_column_group_list = []
    for recode in recode_t_menu_column:
        target_id = recode.get('CREATE_COL_GROUP_ID')
        # 対象のカラムグループIDをlistに追加
        if target_id:
            tmp_target_column_group_list.append(target_id)
    
    # 重複したIDをマージ
    tmp_target_column_group_list = list(dict.fromkeys(tmp_target_column_group_list))
    
    # 使用されているカラムグループIDの親をたどり、最終的に使用されるすべてのカラムグループIDをlistに格納
    target_column_group_list = []
    for column_group_id in tmp_target_column_group_list:
        end_flag = False
        while not end_flag:
            target = dict_t_menu_column_group.get(column_group_id)
            
            # 自分自身のIDをlistの先頭に格納
            target_column_group_list.insert(0, column_group_id)
            if target:
                pa_col_group_id = target.get('pa_col_group_id')
            else:
                # ####メモ：カラムグループ管理の構成に不具合があった場合のエラー
                raise Exception("親カラムグループのデータが無いため異常終了")
            
            if pa_col_group_id:
                # 親のIDを対象のIDにしてループ継続
                column_group_id = pa_col_group_id
            else:
                # 親が無いためループ終了
                end_flag = True
    
    # 重複したIDをマージ
    target_column_group_list = list(dict.fromkeys(target_column_group_list))
    
    return dict_t_menu_column_group, target_column_group_list


def _format_other_link(recode_t_menu_other_link):
    """
        「他メニュー連携」を利用する処理に必要な形式(idをkeyにしたdict型)にフォーマット
        ARGS:
            recode_t_menu_column_group: 「カラムグループ作成情報」のレコード一覧
            recode_t_menu_column: 「メニュー項目作成情報」のレコード一覧
        RETRUN:
            dict_t_menu_other_link: 「他メニュー連携」のレコードのidをkeyにしたdict型に整形
            
    """
    # 「カラムグループ作成情報」のレコードのidをkeyにしたdict型に整形
    dict_t_menu_other_link = {}
    for recode in recode_t_menu_other_link:
        dict_t_menu_other_link[recode.get('LINK_ID')] = recode
    
    return dict_t_menu_other_link


def _disuse_menu_create_recode(objdbca, recode_t_menu_define):
    """
        「初期化」「編集」実行時に、対象のメニューに関連するレコードを廃止する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            recode_t_menu_define: 「メニュー定義一覧」の対象のレコード
        RETRUN:
            result, msg
            
    """
    # テーブル名
    t_comn_menu = 'T_COMN_MENU'
    t_comn_role_menu_link = 'T_COMN_ROLE_MENU_LINK'
    t_comn_menu_table_link = 'T_COMN_MENU_TABLE_LINK'
    t_comn_menu_column_link = 'T_COMN_MENU_COLUMN_LINK'
    t_menu_table_link = 'T_MENU_TABLE_LINK'
    t_menu_other_link = 'T_MENU_OTHER_LINK'
    
    try:
        print("廃止処理スタート")
        # 対象の「メニュー定義一覧」のメニュー名(rest)を取得
        menu_name_rest = recode_t_menu_define.get('MENU_NAME_REST')
        menu_name_rest_subst = menu_name_rest + '_subst'
        menu_name_rest_ref = menu_name_rest + '_ref'
        menu_name_rest_list = [menu_name_rest, menu_name_rest_subst, menu_name_rest_ref]
        
        # 「メニュー管理」から対象のレコードを特定し、listに格納
        target_menu_id_list = []
        for name in menu_name_rest_list:
            ret = objdbca.table_select(t_comn_menu, 'WHERE MENU_NAME_REST = %s AND DISUSE_FLAG = %s', [name, 0])
            if ret:
                target_menu_id_list.append(ret[0].get('MENU_ID'))
        
        # 対象のメニューIDに紐づいたレコードを廃止
        for menu_id in target_menu_id_list:
            # 「ロール-メニュー紐付管理」にて対象のレコードを廃止
            data = {
                'MENU_ID': menu_id,
                'DISUSE_FLAG': "1"
            }
            objdbca.table_update(t_comn_role_menu_link, data, "MENU_ID")
            
            # 「メニュー-テーブル紐付管理」にて対象のレコードを廃止
            data = {
                'MENU_ID': menu_id,
                'DISUSE_FLAG': "1"
            }
            objdbca.table_update(t_comn_menu_table_link, data, "MENU_ID")
            
            # 「メニュー-カラム紐付管理」にて対象のレコードを廃止
            data = {
                'MENU_ID': menu_id,
                'DISUSE_FLAG': "1"
            }
            objdbca.table_update(t_comn_menu_column_link, data, "MENU_ID")
            
            # 「メニュー定義-テーブル紐付管理」にて対象のレコードを廃止
            data = {
                'MENU_ID': menu_id,
                'DISUSE_FLAG': "1"
            }
            objdbca.table_update(t_menu_table_link, data, "MENU_ID")
        
        # 「他メニュー連携」にて対象のレコードを廃止
        # ####メモ：未実装。「メニューグループ」「メニュー」「項目名」「テーブル名」「主キー」「カラム名」が完全一致のレコードを廃止する想定。
        
    except Exception as msg:
        print(msg)
        return False, msg
    
    return True, None


def _disuse_t_comn_menu(objdbca, recode_t_menu_define, target_menu_group_list):
    """
        利用していないメニューグループのメニューを廃止する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            recode_t_menu_define: 「メニュー定義一覧」の対象のレコード
            target_menu_group_list: 対象メニューグループのカラム名一覧
        RETRUN:
            result, msg
            
    """
    # テーブル名
    t_comn_menu = 'T_COMN_MENU'
    
    try:
        # メニュー名(rest)は対象メニューグループが「代入値自動登録」「参照用」の場合は末尾に_subst, _refを結合する。
        menu_name_rest = recode_t_menu_define.get('MENU_NAME_REST')
        menu_name_rest_subst = menu_name_rest + "_subst"
        menu_name_rest_ref = menu_name_rest + "_ref"
        target_menu_name_rest_list = [menu_name_rest, menu_name_rest_subst, menu_name_rest_ref]
        
        # 「メニュー定義一覧」の対象メニューグループ
        menu_group_id_input = recode_t_menu_define.get('MENU_GROUP_ID_INPUT')
        menu_group_id_subst = recode_t_menu_define.get('MENU_GROUP_ID_SUBST')
        menu_group_id_ref = recode_t_menu_define.get('MENU_GROUP_ID_REF')
        target_menu_group_id_list = [menu_group_id_input, menu_group_id_subst, menu_group_id_ref]
        
        # 「メニュー管理」から対象のメニュー名(rest)のレコードを取得
        ret = objdbca.table_select(t_comn_menu, 'WHERE MENU_NAME_REST IN (%s, %s, %s) AND DISUSE_FLAG = %s', [menu_name_rest, menu_name_rest_subst, menu_name_rest_ref, 0])  # noqa: E501
        for recode in ret:
            # 対象のメニュー名(rest)および対象メニューグループが一致するかをチェック
            c_menu_group_id = recode.get('MENU_GROUP_ID')
            c_menu_name_rest = recode.get('MENU_NAME_REST')
            if (c_menu_name_rest in target_menu_name_rest_list) and (c_menu_group_id in target_menu_group_id_list):
                continue
            else:
                # 一致が無い場合、利用しないメニューであるためレコードを廃止する
                menu_id = recode.get('MENU_ID')
                data = {
                    'MENU_ID': menu_id,
                    'DISUSE_FLAG': "1"
                }
                objdbca.table_update(t_comn_menu, data, "MENU_ID")
        
    except Exception as msg:
        print(msg)
        return False, msg
    
    return True, None


def _check_file_upload_column(recode_t_menu_column):
    """
        作成する項目がファイルアップロードカラムのみの場合Trueを返却
        ARGS:
            recode_t_menu_column: 「メニュー項目作成情報」の対象のレコード一覧
        RETRUN:
            boolean
            
    """
    file_upload_only_flag = False
    
    # カラムクラスが「9: ファイルアップロード」のみの場合、flagをTrueにする。
    for recode in recode_t_menu_column:
        
        column_class_id = str(recode.get('COLUMN_CLASS'))
        if not column_class_id == "9":
            file_upload_only_flag = False
            break
        
        file_upload_only_flag = True
        
    return file_upload_only_flag
