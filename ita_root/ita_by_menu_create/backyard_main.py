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
    # その後、次の対象（メニュー作成履歴の「未実行」レコード）で処理を続けたいので、「menu_create_exec_XXX」系の関数の中でそっちに飛ばすようにする。
    
    # テーブル/ビュー名
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
        hitory_id = str(recode.get('HISTORY_ID'))
        menu_create_id = str(recode.get('MENU_CREATE_ID'))
        create_type = str(recode.get('CREATE_TYPE'))
        primary_key_name = 'HISTORY_ID'
        
        # ステータスを「実行中」に更新
        objdbca.db_transaction_start()
        data_list = {
            "HISTORY_ID": hitory_id,
            "STATUS_ID": 2,  # 実行中
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        ret = objdbca.table_update(t_menu_create_history, data_list, primary_key_name)
        if ret:
            objdbca.db_transaction_end(True)
        else:
            # ####メモ：ステータスの更新ができない異常終了
            # ####メモ：ログにステータスの更新に失敗した旨を出したい。
            return False
        
        # create_typeに応じたレコード登録/更新処理を実行
        if create_type == "1":  # 新規作成
            res = menu_create_exec_new(objdbca, menu_create_id)
        
        elif create_type == "2":  # 初期化
            res = menu_create_exec_initialize(objdbca, menu_create_id)
        
        elif create_type == "3":  # 編集
            res = menu_create_exec_edit(objdbca, menu_create_id)
        
        # 最終更新ステータスを指定(3: 完了, 4: 完了(異常))
        objdbca.db_transaction_start()
        status_id = 3 if res else 4
        data_list = {
            "HISTORY_ID": hitory_id,
            "STATUS_ID": status_id,
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        ret = objdbca.table_update(t_menu_create_history, data_list, primary_key_name)
        if ret:
            objdbca.db_transaction_end(True)
        else:
            # ####メモ：ステータスの更新ができない異常終了
            # ####メモ：ログにステータスの更新に失敗した旨を出したい。
            return False
    
    # 処理を終了
    print("メイン処理終了")
    return True


def menu_create_exec_new(objdbca, menu_create_id):
    """
        メニュー作成実行(新規作成)
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_create_id: メニュー作成の対象となる「メニュー定義一覧」のレコードのID
        RETRUN:
            
    """
    print("新規作成を実行")
    
    # ####メモ：処理の流れ
    # 1. 「メニュー定義一覧」から対象のレコード(1件)を取得 ★
    # 2. 「カラムグループ作成情報」からレコード(全件)を取得 ★
    # 3. 「メニュー項目作成情報」から対象のレコード(複数)を取得 ★
    # 4. 「メニュー(縦)作成情報」から対象のレコード(1件)を取得 ★
    # 5. 「一意制約(複数項目)作成情報」からレコード(1件)を取得 ★
    # 6. 「メニューロール作成情報」から対象のレコード(複数)を取得
    # ------ここまで共通でいいかも-----
    # 7. テーブル名を生成 ★
    # 8. 作成するメニューのテーブルを生成 ★
    # 9. 処理に必要なデータを作成 ★
    # 10. トランザクション開始 ★
    # 11. 「メニュー管理」にレコードを登録 ★
    # 12. 「ロール-メニュー紐付管理」にレコードを登録
    # 13. 「メニュー-テーブル紐付管理」にレコードを登録 ★
    # 14. 「カラムグループ管理」にレコードを登録 ★
    # 15. 「メニュー-カラム紐付管理」にレコードを登録 ★
    # 16. 「メニュー定義-テーブル紐付け管理」にレコードを登録 ★
    # 17. 「他メニュー連携」にレコードを登録
    # 18. 「メニュー作成履歴」のステータスを更新 ★
    # 19. トランザクション終了 ★
    
    # テーブル/ビュー名
    t_comn_menu = 'T_COMN_MENU'
    t_comn_menu_group = 'T_COMN_MENU_GROUP'
    t_comn_column_group = 'T_COMN_COLUMN_GROUP'
    t_comn_menu_table_link = 'T_COMN_MENU_TABLE_LINK'
    t_comn_role_menu_link = 'T_COMN_ROLE_MENU_LINK'
    t_menu_table_link = 'T_MENU_TABLE_LINK'
    
    try:
        # メニュー作成用の各テーブルからレコードを取得
        recode_t_menu_define, recode_t_menu_column_group, recode_t_menu_column, recode_t_menu_convert, recode_t_menu_unique_constraint, recode_t_menu_role \
            = _collect_menu_create_data(objdbca, menu_create_id)  # noqa: E501
        
        # テーブル名を生成
        create_table_name = 'T_CMDB_' + str(menu_create_id)
        create_table_name_jnl = 'T_CMDB_' + str(menu_create_id) + '_JNL'
        
        # シートタイプを取得
        sheet_type = str(recode_t_menu_define.get('SHEET_TYPE'))
        
        # メニュー作成対象のテーブルを作成
        if sheet_type == "1":
            sql_file_path = "./sql/parameter_sheet_cmdb.sql"  # ####メモ：ファイルの格納先ディレクトリとかは定数で管理したほうがいいかも。
        elif sheet_type == "2":
            sql_file_path = "./sql/data_sheet_cmdb.sql"  # ####メモ：ファイルの格納先ディレクトリとかは定数で管理したほうがいいかも。
        
        with open(sql_file_path, "r") as f:
            file = f.read()
            file = file.replace('____CMDB_TABLE_NAME____', create_table_name)
            file = file.replace('____CMDB_TABLE_NAME_JNL_____', create_table_name_jnl)
            sql_list = file.split(";\n")
            for sql in sql_list:
                if re.fullmatch(r'[\s\n\r]*', sql) is None:
                    objdbca.sql_execute(sql)
        
        # シートタイプによるループパターン(対象メニューリスト)を設定
        if sheet_type == "1":
            print("シートタイプは：パラメータシート(ホスト/オペレーションあり)")
            target_menu_group_list = ['MENU_GROUP_ID_INPUT', 'MENU_GROUP_ID_SUBST', 'MENU_GROUP_ID_REF']
        elif sheet_type == "2":
            print("シートタイプは：データシート")
            target_menu_group_list = ['MENU_GROUP_ID_INPUT']
        else:
            print("シートタイプが不正")
            return False
        
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
                    raise Exception("親カラムグループのデータが無いため異常終了")
                
                if pa_col_group_id:
                    # 親のIDを対象のIDにしてループ継続
                    column_group_id = pa_col_group_id
                else:
                    # 親が無いためループ終了
                    end_flag = True
        
        # 重複したIDをマージ
        target_column_group_list = list(dict.fromkeys(target_column_group_list))
        
        # メニューグループ一覧を取得
        recode_t_comn_menu_group = objdbca.table_select(t_comn_menu_group, 'WHERE DISUSE_FLAG = %s', [0])
        menu_group_list = {}
        for recode in recode_t_comn_menu_group:
            menu_group_list[recode.get('MENU_GROUP_ID')] = {'menu_group_name_ja': recode.get('MENU_GROUP_NAME_JA'),
                                                            'menu_group_name_en': recode.get('MENU_GROUP_NAME_EN')}
        
        # トランザクション開始
        objdbca.db_transaction_start()
        
        # 対象メニューグループ分だけ処理をループ
        for menu_group_col_name in target_menu_group_list:
            # ####「メニュー管理」に対するレコード登録処理スタート
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
            ret = objdbca.table_insert(t_comn_menu, data_list, primary_key_name)
            if not ret:
                raise Exception("「メニュー管理」へのレコード登録に失敗しました。")
            
            # 「メニュー管理」に登録したレコードのuuidを取得
            menu_uuid = ret[0].get('MENU_ID')
            
            # ####「ロール-メニュー紐付管理」に対するレコード登録処理スタート
            # ####メモ：未実装。一時的な対処として、仮のレコードを登録する。
            data_list = {
                "MENU_ID": menu_uuid,
                "ROLE_ID": "abc123",  # ####メモ：一時的な値
                "PRIVILEGE": 1,
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'LINK_ID'
            ret = objdbca.table_insert(t_comn_role_menu_link, data_list, primary_key_name)
            if not ret:
                raise Exception("「ロール-メニュー紐付管理」へのレコード登録に失敗しました。")
            
            # ####「メニュー-テーブル紐付管理」に対するレコード登録処理スタート
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
                    tmp_unique_constraint.insert(0, add_unique_constraint)
                    unique_constraint = json.dumps(tmp_unique_constraint)
                else:
                    unique_constraint = '[["operation_name", "host_name"]]'
            
            # 「メニュー-テーブル紐付管理」にレコードを登録
            data_list = {
                "MENU_ID": menu_uuid,
                "TABLE_NAME": create_table_name,  # ####メモ：VIEWを使う場合はここを修正する。
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
            ret = objdbca.table_insert(t_comn_menu_table_link, data_list, primary_key_name)
            
            # ####「カラムグループ管理」に対するレコード登録処理スタート
            # 対象メニューグループ「入力用」の場合のみ実施
            if menu_group_col_name == "MENU_GROUP_ID_INPUT":
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
                    ret = objdbca.table_insert(t_comn_column_group, data_list, primary_key_name)
            
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
            
            # ####「メニュー-カラム紐付管理」に対するレコード登録処理スタート
            # ####メモ：とりあえず「パラメータシート」の場合のみ。「データシート」は構造が変わるため修正が必要。
            # ####メモ：戻り値にエラー時のmsg入れるようにしたが、適当なのであとで確認。
            result, msg = _insert_t_comn_menu_column_link(objdbca, menu_uuid, dict_t_comn_column_group, dict_t_menu_column_group, recode_t_menu_column)  # noqa: E501
            if not result:
                raise Exception(msg)
            
            # ####「メニュー定義-テーブル紐付管理」に対するレコード登録処理スタート
            data_list = {
                "MENU_ID": menu_uuid,
                "TABLE_NAME": create_table_name,
                "KEY_COL_NAME": "ROW_ID",
                "TABLE_NAME_JNL": create_table_name_jnl,
                "DISUSE_FLAG": "0",
                "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
            }
            primary_key_name = 'MENU_TABLE_LINK_ID'
            ret = objdbca.table_insert(t_menu_table_link, data_list, primary_key_name)
        
        # ####「他メニュー連携」に対するレコード登録処理スタート
        # ####メモ：作成する項目の中で「必須」「一意制約」が両方Trueのものがあれば、レコードを登録する。
        # ####メモ：未実装。
        
        # コミット/トランザクション終了
        objdbca.db_transaction_end(True)
        
    except Exception as e:
        # ロールバック/トランザクション終了
        objdbca.db_transaction_end(False)
        
        print(e)
        
        return False
    
    return True


def menu_create_exec_initialize(objdbca, menu_create_id):
    """
        メニュー作成実行(初期化)
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_create_id: メニュー作成の対象となる「メニュー定義一覧」のレコードのID
        RETRUN:
            
    """
    # ####メモ： 対象メニューグループが変わった場合、元の対象メニューグループで使われていたメニューを廃止する処理がいる。
    print("初期化を実行")
    
    return True


def menu_create_exec_edit(objdbca, menu_create_id):
    """
        メニュー作成実行(編集)
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_create_id: メニュー作成の対象となる「メニュー定義一覧」のレコードのID
        RETRUN:
            
    """
    # ####メモ： 対象メニューグループが変わった場合、元の対象メニューグループで使われていたメニューを廃止する処理がいる。
    print("編集を実行")
    
    return True


def _collect_menu_create_data(objdbca, menu_create_id):
    """
        メニュー作成対象の必要レコードををすべて取得する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_create_id: メニュー作成の対象となる「メニュー定義一覧」のレコードのID
        RETRUN:
            
    """
    # 1. 「メニュー定義一覧」から対象のレコード(1件)を取得
    # 2. 「カラムグループ作成情報」からレコード(全件)を取得
    # 3. 「メニュー項目作成情報」から対象のレコード(複数)を取得
    # 4. 「メニュー(縦)作成情報」から対象のレコード(1件)を取得
    # 5. 「一意制約(複数項目)作成情報」からレコード(1件)を取得
    # 6. 「メニューロール作成情報」から対象のレコード(複数)を取得
    
    # テーブル/ビュー名
    t_menu_define = 'T_MENU_DEFINE'  # メニュー定義一覧
    t_menu_column_group = 'T_MENU_COLUMN_GROUP'  # カラムグループ作成情報
    t_menu_column = 'T_MENU_COLUMN'  # メニュー項目作成情報
    t_menu_convert = 'T_MENU_CONVERT'  # メニュー(縦)作成情報
    t_menu_unique_constraint = 'T_MENU_UNIQUE_CONSTRAINT'  # 一意制約(複数項目)作成情報
    t_menu_role = 'T_MENU_ROLE'  # メニューロール作成情報
    
    # 「メニュー定義一覧」から対象のレコードを取得
    recode_t_menu_define = objdbca.table_select(t_menu_define, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
    if not recode_t_menu_define:
        print("メニュー定義一覧に対象が無いのでエラー判定")
    recode_t_menu_define = recode_t_menu_define[0]
    
    # 「カラムグループ作成情報」から全てのレコードを取得
    recode_t_menu_column_group = objdbca.table_select(t_menu_column_group, 'WHERE DISUSE_FLAG = %s', [0])
    
    # 「メニュー項目作成情報」から対象のレコードを取得
    recode_t_menu_column = objdbca.table_select(t_menu_column, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
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
    
    # 「一意制約(複数項目)作成情報」か対象のレコードを取得
    recode_t_menu_unique_constraint = objdbca.table_select(t_menu_unique_constraint, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])  # noqa: E501
    recode_t_menu_unique_constraint = recode_t_menu_unique_constraint[0]
    
    # 「メニューロール作成情報」か対象のレコードを取得
    recode_t_menu_role = objdbca.table_select(t_menu_role, 'WHERE MENU_CREATE_ID = %s AND DISUSE_FLAG = %s', [menu_create_id, 0])
    
    return recode_t_menu_define, recode_t_menu_column_group, recode_t_menu_column, recode_t_menu_convert, recode_t_menu_unique_constraint, recode_t_menu_role  # noqa: E501


def _insert_t_comn_menu_column_link(objdbca, menu_uuid, dict_t_comn_column_group, dict_t_menu_column_group, recode_t_menu_column):
    """
        「メニュー-カラム紐付管理」メニューのテーブルにレコードを追加する
        ARGS:
            objdbca: DB接クラス DBConnectWs()
            menu_uuid: メニュー作成の対象となる「メニュー管理」のレコードのID
            dict_t_comn_column_group: 「カラムグループ管理」のレコードのidをkeyにしたdict
            dict_t_menu_column_group: 「カラムグループ作成情報」のレコードのidをkeyにしたdict
            recode_t_menu_column：「メニュー項目作成情報」の対象のレコード一覧
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
            "DESCRIPTION_EN": "Cannot edit because of auto-numbering. Must be blank when execution process type is [Register].",  # ####メモ：メッセージ一覧から取得する
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
        # 表示順序を加算
        disp_seq_num = int(disp_seq_num) + 10
        
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
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
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
            "COL_GROUP_ID": "5010101",  # カラムグループ「オペレーション」####メモ：現状同一の名前のカラムグループが存在するため、変更の可能性高い
            "COLUMN_CLASS": 7,  # IDColumn
            "COLUMN_DISP_SEQ": disp_seq_num,
            "REF_TABLE_NAME": "T_COMN_OPERATION",
            "REF_PKEY_NAME": "OPERATION_ID",
            "REF_COL_NAME": "OPERATION_NAME",
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
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
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
            "DESCRIPTION_EN": "When converting from the vertical menu to the horizontal menu, items will be arranged in ascending order from left to right.",  # ####メモ：メッセージ一覧から取得する
            "DISUSE_FLAG": "0",
            "LAST_UPDATE_USER": "9999"  # ####メモ：メニュー作成機能バックヤード用ユーザを用意してそのIDを採用する。
        }
        primary_key_name = 'COLUMN_DEFINITION_ID'
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
        # 表示順序を加算
        disp_seq_num = int(disp_seq_num) + 10
        
        # 「メニュー作成機能で作成した項目」の対象の数だけループスタート
        for recode in recode_t_menu_column:
            column_class = recode.get('COLUMN_CLASS')
            
            # 初期値に登録する値を生成
            initial_value = _create_initial_value(recode)
            
            # バリデーションに登録する値を生成
            validate_option = _create_validate_option(recode)
            
            # ####メモ：「プルダウン選択」の場合が未実装。カラムクラスが7(IDColumn)の場合「REF_TABLE_NAME」などは「他メニュー連携」メニューのテーブルから値を取ってくる必要がある。
            ref_table_name = None
            ref_pkey_name = None
            ref_col_name = None
            ref_sort_conditions = None
            ref_multi_lang = 0
            
            # 「カラムグループ作成情報」のIDから同じフルカラムグループ名の対象を「カラムグループ管理」から探しIDを指定
            col_group_id = None
            tmp_col_group_id = recode.get('CREATE_COL_GROUP_ID')
            target_t_menu_column_group = dict_t_menu_column_group.get(tmp_col_group_id)
            if target_t_menu_column_group:
                t_full_col_group_name_ja = target_t_menu_column_group.get('full_col_group_name_ja')
                t_full_col_group_name_en = target_t_menu_column_group.get('full_col_group_name_en')
                for key_id, target_t_comn_column_group in dict_t_menu_column_group.items():
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
            ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
            
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
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
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
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
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
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
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
        ret = objdbca.table_insert(t_comn_menu_column_link, data_list, primary_key_name)
        
    except Exception as msg:
        print(msg)
                
        return False, msg
    
    return True, None


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
