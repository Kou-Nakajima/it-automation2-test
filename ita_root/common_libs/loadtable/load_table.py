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

import sys
import datetime
import textwrap
import json
import importlib
import traceback

from flask import g
from common_libs.column import *  # noqa: F403
from common_libs.common import *  # noqa: F403


# 定数
# 処理実行種別
CMD_REGISTER = 'Register'
CMD_UPDATE = 'Update'
CMD_RESTORE = 'Restore'
CMD_DISCARD = 'Discard'

# メッセージ種別
MSG_LEVEL_DEBUG = 'DEBUG'
MSG_LEVEL_INFO = 'INFO'
MSG_LEVEL_WARNING = 'WARNING'
MSG_LEVEL_ERROR = 'ERROR'
MSG_LEVEL_CRITICAL = ' CRITICAL'
MSG_CODE = 'CODE'

# 共通REST項目名
REST_KEY_DISCARD = 'discard'
REST_KEY_LAST_UPDATE_TIME = 'last_update_date_time'
REST_KEY_LAST_UPDATE_USER = 'last_updated_user'

# 共通REST項目名(履歴)
REST_KEY_JNL_SEQ_NO = 'journal_id'
REST_KEY_LAST_JNL_REG_DATETIME = 'journal_datetime'
REST_KEY_LAST_JNL_ACTION_CLASS = 'journal_action'

# 共通項目名(履歴)
COLNAME_JNL_SEQ_NO = 'JOURNAL_SEQ_NO'
COLNAME_JNL_REG_DATETIME = 'JOURNAL_REG_DATETIME'
COLNAME_JNL_ACTION_CLASS = 'JOURNAL_ACTION_CLASS'

# objtableキー
MENUINFO = 'MENUINFO'
COLINFO = 'COLINFO'
LIST = 'LIST'

# 紐付関連カラム名
COLNAME_MENU_ID = 'MENU_ID'
COLNAME_TABLE_NAME = 'TABLE_NAME'
COLNAME_ROW_INSERT_FLAG = 'ROW_INSERT_FLAG'
COLNAME_ROW_UPDATE_FLAG = 'ROW_UPDATE_FLAG'
COLNAME_ROW_DISUSE_FLAG = 'ROW_DISUSE_FLAG'
COLNAME_ROW_REUSE_FLAG = 'ROW_REUSE_FLAG'
COLNAME_SHEET_TYPE = 'SHEET_TYPE'

COLNAME_SORT_KEY = 'SORT_KEY'
COLNAME_COL_NAME = 'COL_NAME'
COLNAME_COLUMN_CLASS_NAME = 'COLUMN_CLASS_NAME'
COLNAME_LOCK_TABLE = 'LOCK_TABLE'
COLNAME_COLUMN_NAME_REST = 'COLUMN_NAME_REST'
COLNAME_REQUIRED_ITEM = 'REQUIRED_ITEM'
COLNAME_INPUT_ITEM = 'INPUT_ITEM'
COLNAME_VIEW_ITEM = 'VIEW_ITEM'
COLNAME_AUTO_INPUT = 'AUTO_INPUT'
COLNAME_UNIQUE_CONSTRAINT = 'UNIQUE_CONSTRAINT'
COLNAME_BEFORE_VALIDATE_REGISTER = 'BEFORE_VALIDATE_REGISTER'
COLNAME_AFTER_VALIDATE_REGISTER = 'AFTER_VALIDATE_REGISTER'
COLNAME_COLUMN_DISP_SEQ = 'COLUMN_DISP_SEQ'
COLNAME_SAVE_TYPE = 'SAVE_TYPE'

# maintenance/filter 構造キー
REST_PARAMETER_KEYNAME = 'parameter'
REST_FILE_KEYNAME = 'file'

SEARCH_MODE_NOMAL = 'NORMAL'
SEARCH_MODE_LIST = 'LIST'
SEARCH_MODE_RANGE = 'RANGE'

REGISTER_DEFAULT_MENU = ['0', '1', '2', '3', '4']
REGISTER_SET_PRYMARY_MENU = ['14']


class loadTable():
    """
    load_table

        共通
            get_menu_info: メニューIDから関連情報全取得
        REST
            filter:   一覧データ取得、検索条件による絞り込み
            maintenance:   登録、更新(更新、廃止、復活)処理
            maintenance_all:   登録、更新(更新、廃止、復活)の複合処理

    """

    def __init__(self, objdbca='', menu=''):
        # コンストラクタ
        # メニューID
        self.menu = menu

        # エラーメッセージ集約用
        self.message = {
            MSG_LEVEL_DEBUG: {},
            MSG_LEVEL_INFO: {},
            MSG_LEVEL_WARNING: {},
            MSG_LEVEL_ERROR: {},
            MSG_LEVEL_CRITICAL: {},
            MSG_CODE: '',
        }
        # レコード操作結果
        self.exec_result = []
        
        # DB接続
        self.objdbca = objdbca

        # 環境情報
        self.lang = g.LANGUAGE

        # DBのカラム、PK
        self.primary_key = ''
        self.column_list = ''
        
        # メニュー関連情報
        self.objtable = {}
        if self.menu is not None:
            self.objtable = self.get_menu_info()

        # メニュー内で使用可能なrestkye
        self.restkey_list = self.get_restkey_list()

        # 廃止、最終更新日時、最終更新者
        self.base_cols_val = {
            REST_KEY_DISCARD: 0,
            REST_KEY_LAST_UPDATE_TIME: None,
            REST_KEY_LAST_UPDATE_USER: 1,
        }
        
        # 処理件数:種別毎
        self.exec_count = {
            CMD_REGISTER: 0,
            CMD_UPDATE: 0,
            CMD_RESTORE: 0,
            CMD_DISCARD: 0,
        }
        # 履歴共通カラム
        self.jnl_colname = {
            COLNAME_JNL_SEQ_NO: REST_KEY_JNL_SEQ_NO,
            COLNAME_JNL_REG_DATETIME: REST_KEY_LAST_JNL_REG_DATETIME,
            COLNAME_JNL_ACTION_CLASS: REST_KEY_LAST_JNL_ACTION_CLASS,
        }

    # message設定
    def reset_message(self):
        """
            エラーレベルでメッセージを設定
            ARGS:
                self.message
        """
        self.message = {
            MSG_LEVEL_DEBUG: {},
            MSG_LEVEL_INFO: {},
            MSG_LEVEL_WARNING: {},
            MSG_LEVEL_ERROR: {},
            MSG_LEVEL_CRITICAL: {},
            MSG_CODE: '',
        }
            
    # message設定
    def set_message(self, message, target='__line__', level='', status_code=''):
        """
            エラーレベルでメッセージを設定
            ARGS:
                self.message
        """
        if level in self.message:
            self.message[level].setdefault(target, [])
            self.message[level][target].append(message)
        else:
            self.message[MSG_LEVEL_ERROR].setdefault(target, [])
            self.message[MSG_LEVEL_ERROR][target].append(message)
        
        if len(status_code) > 0:
            self.message[MSG_CODE] = status_code

    # message取得
    def get_message(self, level=''):
        """
            メッセージを取得
            ARGS:
                level:メッセージレベル
            RETRUN:
                self.message
        """
        if len(level) == 0:
            message = self.message
        elif level in self.message:
            message = self.message[level]
        else:
            message = self.message
        return message

    # レコード操作実行データ保存
    def set_exec_result(self, result_data):
        """
            レコード操作結果保存
            ARGS:
                self.exec_result
        """
        self.exec_result.append(result_data)

    # 実行データ取得
    def get_exec_result(self):
        """
            レコード操作結果取得
            ARGS:
            RETRUN:
                self.exec_result
        """
        return self.exec_result
    
    # message数取得
    def get_message_count(self, level=''):
        """
            レベルでメッセージ数を取得
            ARGS:
                level:メッセージレベル
            RETRUN:
                self.message
        """
        result = False
        if len(level) != 0:
            if level in self.message:
                result = len(self.message[level])
        return result

    # 処理件数
    def set_exec_count_up(self, cmd_type):
        """
            処理件数をカウントアップ
            ARGS:
                cmd_type
        """
        self.exec_count[cmd_type] += 1

    # 処理件数取得
    def get_exec_count(self):
        """
            処理件数を取得
            ARGS:
            RETRUN:
                self.exec_count
        """
        return self.exec_count

    # 全処理件数取得
    def get_exec_count_all(self):
        """
            全処理件数を取得
            ARGS:
            RETRUN:
                self.exec_count
        """
        count = 0
        for tmp_keys, tmp_cnt in self.get_exec_count().items():
            count = count + tmp_cnt
        return count

    # メニューIDから関連情報全取得
    def get_menu_info(self):
        """
            メニュー情報取得
            ARGS:
            RETRUN:
                True / エラーメッセージ
        """
        menu_info = {}
        cols_info = {}
        list_info = {}

        menu_id = None
        # メニュー情報
        try:
            query_str = textwrap.dedent("""
                SELECT * FROM `T_COMN_MENU_TABLE_LINK` `TAB_A`
                LEFT JOIN `T_COMN_MENU` `TAB_B` ON ( `TAB_A`.`MENU_ID` = `TAB_B`.`MENU_ID` )
                WHERE `TAB_B`.`MENU_NAME_REST` = %s
                AND `TAB_A`.`DISUSE_FLAG` <> 1
                AND `TAB_B`.`DISUSE_FLAG` <> 1
            """).format(menu=self.menu).strip()
            tmp_menu_info = self.objdbca.sql_execute(query_str, [self.menu])
            if len(tmp_menu_info) == 0:
                status_code = '401-00003'
                msg_args = self.menu
                msg = g.appmsg.get_api_message(status_code, [msg_args])
                raise Exception(status_code, msg)
        except Exception:
            return False

        for tmp_menu in tmp_menu_info:
            menu_info = tmp_menu
            menu_id = tmp_menu.get(COLNAME_MENU_ID)

        # カラム情報情報
        try:
            query_str = textwrap.dedent("""
                SELECT
                    `TAB_A`.*,
                    `TAB_B`.`COLUMN_CLASS_NAME` AS `COLUMN_CLASS_NAME`
                FROM `T_COMN_MENU_COLUMN_LINK` `TAB_A`
                LEFT JOIN `T_COMN_COLUMN_CLASS` `TAB_B` ON ( `TAB_A`.`COLUMN_CLASS` = `TAB_B`.`COLUMN_CLASS_ID` )
                WHERE `MENU_ID` = '{menu_id}'
                AND `TAB_A`.`DISUSE_FLAG` <> 1
                AND `TAB_B`.`DISUSE_FLAG` <> 1
                """).format(menu_id=menu_id).strip()
            tmp_cols_info = self.objdbca.sql_execute(query_str)
            if len(tmp_cols_info) == 0:
                status_code = '401-00003'
                msg_args = self.menu
                msg = g.appmsg.get_api_message(status_code, [msg_args])
                raise Exception(status_code, msg)
        except Exception:
            return False

        try:
            cols_info = {}
            list_info = {}
            for tmp_col_info in tmp_cols_info:
                rest_name = tmp_col_info.get(COLNAME_COLUMN_NAME_REST)
                cols_info.setdefault(rest_name, tmp_col_info)
                
                # 参照先テーブル情報
                ref_table_name = tmp_col_info.get('REF_TABLE_NAME')
                ref_pkey_name = tmp_col_info.get('REF_PKEY_NAME')
                ref_col_name = tmp_col_info.get('REF_COL_NAME')
                ref_multi_lang = tmp_col_info.get('REF_MULTI_LANG')
                ref_sort_conditions = tmp_col_info.get('REF_SORT_CONDITIONS')

                if ref_table_name is not None:
                    if ref_multi_lang == "1":
                        user_env = self.get_lang().upper()
                        ref_col_name = "{}_{}".format(ref_col_name, user_env)

                    if ref_sort_conditions is None:
                        str_order_by = ''
                    else:
                        str_order_by = ''

                    query_str = textwrap.dedent("""
                        SELECT * FROM `{table_name}`
                        WHERE `DISUSE_FLAG` <> 1
                        {order_by}
                    """).format(table_name=ref_table_name, order_by=str_order_by).strip()
                    tmp_rows = self.objdbca.sql_execute(query_str)

                    tmp_list = {}
                    for tmp_row in tmp_rows:
                        tmp_id = tmp_row.get(ref_pkey_name)
                        tmp_nm = tmp_row.get(ref_col_name)
                        tmp_list.setdefault(tmp_id, tmp_nm)

                    list_info.setdefault(rest_name, tmp_list)
        except Exception:
            return False

        try:
            table_name = menu_info.get(COLNAME_TABLE_NAME)
            column_list, primary_key_list = self.objdbca.table_columns_get(table_name)
            self.set_column_list(column_list)
            self.set_primary_key(primary_key_list[0])

        except Exception:
            return False

        result_data = {
            MENUINFO: menu_info,
            COLINFO: cols_info,
            LIST: list_info
        }

        return result_data

    # column_listの設定,取得
    def set_column_list(self, column_list):
        """
            column_listの設定
            ARGS:
                column_list
        """
        self.column_list = column_list

    def get_column_list(self):
        """
            column_listの取得
            RETUEN:
                self.column_list
        """
        return self.column_list

    # primary_keyの設定,取得
    def set_primary_key(self, primary_key):
        """
            column_listの設定
            ARGS:
                primary_key
        """
        self.primary_key = primary_key

    def get_primary_key(self):
        """
            primary_keyの取得
            RETUEN:
                self.primary_key
        """
        return self.primary_key

    def get_lang(self):
        """
            言語情報を取得
            RETRUN:
                string
        """
        return self.lang

    def get_objtable(self):
        """
            テーブルデータを設定
            RETRUN:
                self.objtable
        """
        return self.objtable

    def get_unique_constraint(self):
        """
            組み合わせ一意制約取得
            RETRUN:
                {}
        """
        try:
            result = self.objtable.get(MENUINFO).get(COLNAME_UNIQUE_CONSTRAINT)
        except Exception:
            result = []
        return result

    def get_menu_id(self):
        """
            メニューID取得
            RETRUN:
                {}
        """
        try:
            result = self.objtable.get(MENUINFO).get(COLNAME_MENU_ID)
        except Exception:
            result = ''
        return result

    def get_menu_before_validate_register(self):
        """
            レコード操作前処理設定取得(メニュー)
            RETRUN:
                {}
        """
        try:
            result = self.objtable.get(MENUINFO).get(COLNAME_BEFORE_VALIDATE_REGISTER)
        except Exception:
            result = None
        return result

    def get_menu_after_validate_register(self):
        """
            レコード操作後処理設定取得(メニュー)
            RETRUN:
                {}
        """
        try:
            result = self.objtable.get(MENUINFO).get(COLNAME_AFTER_VALIDATE_REGISTER)
        except Exception:
            result = None
        return result

    def get_objcols(self):
        """
            全カラム設定を取得
            RETRUN:
                {}
        """
        return self.objtable.get(COLINFO)

    def get_objcol(self, rest_key):
        """
            単一カラム設定を取得
            RETRUN:
                {}
        """
        try:
            result = self.get_objcols().get(rest_key)
        except Exception:
            result = None
        return result
    
    def get_save_type(self, rest_key):
        """
            単一カラムのsave_typeを取得
            RETRUN:
                {}
        """
        try:
            result = self.get_objcol(rest_key).get(COLNAME_SAVE_TYPE)
        except Exception:
            result = None
        return result
    
    def get_table_name(self):
        """
            テーブル名を取得
            RETRUN:
                string
        """
        try:
            result = self.get_objtable().get(MENUINFO).get(COLNAME_TABLE_NAME)
        except Exception:
            result = None
        return result
    
    def get_table_name_jnl(self):
        """
            テーブル名を取得
            RETRUN:
                string
        """
        try:
            result = "{}_JNL".format(self.get_objtable().get(MENUINFO).get(COLNAME_TABLE_NAME))
        except Exception:
            result = None
        return result

    def get_sort_key(self):
        """
            ソートキーを取得
            RETRUN:
                {} or [] ?
        """
        try:
            result = self.get_objtable().get(MENUINFO).get(COLNAME_SORT_KEY)
        except Exception:
            result = None
        return result

    def get_sheet_type(self):
        """
            シートタイプを取得
            RETRUN:
                {} or [] ?
        """
        try:
            result = self.get_objtable().get(MENUINFO).get(COLNAME_SHEET_TYPE)
        except Exception:
            result = 0
        return result

    def get_col_name(self, rest_key):
        """
            カラム名を取得
            RETRUN:
                self.col_name
        """
        try:
            result = self.get_objcol(rest_key).get(COLNAME_COL_NAME)
        except Exception:
            result = None
        return result
    
    def get_col_class_name(self, rest_key):
        """
            カラムクラス設定を取得
            RETRUN:
                {}
        """

        try:
            result = self.get_objcol(rest_key).get(COLNAME_COLUMN_CLASS_NAME)
        except Exception:
            result = None
        return result
    
    def is_columnclass(self, rest_key):
        """
            カラムクラスの確認
            ARGS:
                rest_key:REST用の項目名
            RETRUN:
                True / False
        """
        retBool = True
        tmp_objcolumn = None
        try:
            objcol = self.get_objcol(rest_key)

            if objcol is not None:
                tmp_objcolumn = objcol.get('objcolumn')

            if tmp_objcolumn is None:
                retBool = False
        except Exception:
            retBool = False

        return retBool

    def set_columnclass(self, rest_key, cmd_type=''):
        """
            カラムクラス設定
            ARGS:
                rest_key:REST用の項目名
                cmd_type:実行種別
            RETRUN:
                obj
        """
        
        try:
            col_class_name = self.get_col_class_name(rest_key)
            if col_class_name is None:
                col_class_name = 'TextColumn'
            eval_class_str = "{}(self.objdbca,self.objtable,rest_key,cmd_type)".format(col_class_name)
            objcolumn = eval(eval_class_str)
        except Exception:
            col_class_name = 'TextColumn'
            eval_class_str = "{}(self.objdbca,self.objtable,rest_key,cmd_type)".format(col_class_name)
            objcolumn = eval(eval_class_str)

        # objcolumnを設定
        if rest_key in self.objtable[COLINFO]:
            self.objtable[COLINFO].setdefault(rest_key, None)
            self.objtable[COLINFO][rest_key].setdefault('objcolumn', objcolumn)

    def get_columnclass(self, rest_key, cmd_type=''):
        """
            カラムクラス呼び出し
            ARGS:
                rest_key:REST用の項目名
            RETRUN:
                obj
        """
        try:
            # objcolumnの有無
            if self.is_columnclass(rest_key) is True:
                objcol = self.get_objcol(rest_key)
                objcolumn = objcol.get('objcolumn')
                objcolumn.set_cmd_type(cmd_type)
            else:
                # objcolumnの設定
                self.set_columnclass(rest_key, cmd_type)
                objcol = self.get_objcol(rest_key)
                objcolumn = objcol.get('objcolumn')
                if self.is_columnclass(rest_key) is False:
                    col_class_name = 'TextColumn'
                    eval_class_str = "{}(self.objdbca,self.objtable,rest_key,cmd_type)".format(col_class_name)
                    objcolumn = eval(eval_class_str)
        except Exception:
            col_class_name = 'TextColumn'
            eval_class_str = "{}(self.objdbca,self.objtable,rest_key,cmd_type)".format(col_class_name)
            objcolumn = eval(eval_class_str)

        return objcolumn
    
    def get_locktable(self):
        """
            テーブルデータを設定
            RETRUN:
                self.objtable
        """
        return self.get_objtable().get(MENUINFO).get(COLNAME_LOCK_TABLE)

    def get_restkey_list(self):
        """
            rest_key list
            RETRUN:
                []
        """
        sortlist = []
        try:
            tmp_sort = sorted(
                self.get_objcols().items(),
                key=lambda x: (
                    x[1][COLNAME_COLUMN_DISP_SEQ]
                )
            )
            for x in tmp_sort:
                sortlist.append(x[1].get(COLNAME_COLUMN_NAME_REST))
        except Exception:
            pass

        return sortlist

    def chk_restkey(self, rest_key):
        if rest_key in self.get_restkey_list():
            return True
        else:
            return False

    def get_json_cols_base(self):
        json_data_base = {}
        for rest_key, objcol in self.get_objcols().items():
            save_type = self.get_save_type(rest_key)
            if save_type == 'JSON':
                json_data_base.setdefault(rest_key, None)
        return json_data_base

    def get_required_restkey_list(self):
        """
            required list
            RETRUN:
                []
        """
        required_restkey_list = []
        for rest_key in self.get_restkey_list():
            required_item = self.get_objcol(rest_key).get(COLNAME_REQUIRED_ITEM)
            input_item = self.get_objcol(rest_key).get(COLNAME_INPUT_ITEM)
            auto_input = self.get_objcol(rest_key).get(COLNAME_AUTO_INPUT)
            if required_item == '1' and input_item == '1' and auto_input != '1':
                required_restkey_list.append(rest_key)

        return required_restkey_list
    
    def get_rest_key(self, col_name):
        """
            rest_key list
            ARGS:
                col_name:カラム名
            RETRUN:
                []
        """
        result = ''
        for rest_key, objcol in self.get_objcols().items():
            tmp_col_name = objcol.get(COLNAME_COL_NAME)
            if col_name == tmp_col_name:
                result = rest_key
                break
            elif col_name in self.jnl_colname:
                result = self.jnl_colname.get(col_name)
                break

        return result

    def get_maintenance_uuid(self, uuid):
        """
            対象の最終更新履歴を取得
            ARGS:
                uuid:pk
            RETRUN:
                []
        """
        result = ''
        table_name = self.get_table_name_jnl()
        column_list, primary_key_list = self.objdbca.table_columns_get(self.get_table_name())
        primary_key = primary_key_list[0]
        query_str = textwrap.dedent("""
            SELECT * FROM `{table_name}`
            WHERE {primary_key} = %s
            ORDER BY LAST_UPDATE_TIMESTAMP DESC
            LIMIT 1
        """).format(table_name=table_name, primary_key=primary_key).strip()
        result = self.objdbca.sql_execute(query_str, [uuid])

        return result

    def get_target_jnl_uuids(self, uuid):
        """
            対象の履歴一括取得
            ARGS:
                uuid:pk
            RETRUN:
                []
        """
        result = []
        table_name = self.get_table_name_jnl()
        column_list, primary_key_list = self.objdbca.table_columns_get(self.get_table_name())
        primary_key = primary_key_list[0]
        query_str = textwrap.dedent("""
            SELECT * FROM `{table_name}`
            WHERE {primary_key} = %s
            ORDER BY LAST_UPDATE_TIMESTAMP DESC
        """).format(table_name=table_name, primary_key=primary_key).strip()
        tmp_result = self.objdbca.sql_execute(query_str, [uuid])
        for row in tmp_result:
            result.append(row)
        return result

    def get_target_rows(self, uuid):
        """
            対象のレコード取得
            get target row data
            RETRUN:
                []
        """
        try:
            result = []
            table_name = self.get_table_name()
            column_list = self.get_column_list()
            primary_key = self.get_primary_key()
            query_str = textwrap.dedent("""
                SELECT * FROM `{table_name}`
                WHERE `{primary_key}` = %s
                ORDER BY `LAST_UPDATE_TIMESTAMP` DESC
                LIMIT 1
            """).format(table_name=table_name, primary_key=primary_key).strip()
            result = self.objdbca.sql_execute(query_str, [uuid])
        except Exception:
            result = []

        return result
    
    # [filter]:メニューのレコード取得
    def rest_filter(self, parameter, mode='nomal'):
        """
            RESTAPI[filter]:メニューのレコード取得
            ARGS:
                parameter:検索条件
                mode
                    nomal:本体 / jnl:履歴 / jnl_all:履歴 /
                    excel:本体Excel用 / excel_jnl:履歴Excel用 / excel_jnl_all:全履歴Excel用 /
                    count:件数 / count_jnl:履歴件数 / count_jnl_all:全履歴件数
            RETRUN:
                status_code, result, msg,
        """

        status_code = '000-00000'  # 成功
        msg = ''

        search_mode_list = [
            SEARCH_MODE_NOMAL,
            SEARCH_MODE_LIST,
            SEARCH_MODE_RANGE
        ]

        result_list = []
        filter_querys = []
        try:
            # テーブル情報（カラム、PK取得）
            column_list = self.get_column_list()
            primary_key = self.get_primary_key()
            # テーブル本体
            if mode in ['nomal', 'excel', 'count']:
                table_name = self.get_table_name()
                # parameter check
                if isinstance(parameter, dict):
                    for search_key, search_confs in parameter.items():
                        if len(search_confs) > 0:
                            for search_mode, search_conf in search_confs.items():
                                if search_mode in search_mode_list:
                                    if search_key in self.get_restkey_list():
                                        objcolumn = self.get_columnclass(search_key)
                                        filter_querys.append(objcolumn.get_filter_query(search_mode, search_conf))

                #  全件
                where_str = ''
                bind_value_list = []
                conjunction = "where"
                # where生成
                if len(filter_querys) > 0:
                    for filter_query in filter_querys:
                        if filter_query.get('where') is not None:
                            if len(where_str) != 0:
                                conjunction = 'and'
                            tmp_where_str = ' {} {}'.format(conjunction, filter_query.get('where'))
                            bindkeys = filter_query.get('bindkey')
                            if isinstance(bindkeys, str):
                                bindkey = bindkeys
                                tmp_where_str = tmp_where_str.replace(bindkey, '%s')
                                bind_value_list.append(filter_query.get('bindvalue').get(bindkey))
                            elif isinstance(bindkeys, list):
                                for bindkey in bindkeys:
                                    tmp_where_str = tmp_where_str.replace(bindkey, '%s')
                                    bind_value_list.append(filter_query.get('bindvalue').get(bindkey))
                            where_str = where_str + tmp_where_str

                sort_key = self.get_sort_key()
                if sort_key is not None:
                    str_orderby = ''
                    where_str = where_str + str_orderby
            elif mode in ['jnl', 'excel_jnl', 'count_jnl', 'jnl_all', 'excel_jnl_all', 'jnl_count_all']:
                # 履歴テーブル
                where_str = ''
                bind_value_list = []
                table_name = self.get_table_name()
                table_name = self.get_table_name_jnl()
                
                if mode not in ['jnl_all', 'excel_jnl_all', 'jnl_count_all']:
                    tmp_jnl_conf = parameter.get('JNL')
                    if tmp_jnl_conf is not None:
                        bindvalue = tmp_jnl_conf
                        bind_value_list = [bindvalue]
                    else:
                        bindvalue = None

                    if bindvalue is None or isinstance(bindvalue, str) is False:
                        status_code = '200-00102'
                        log_msg_args = []
                        api_msg_args = []
                        # raise AppException(status_code, msg_ags)
                        raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

                target_uuid_key = self.get_rest_key(primary_key)
                
                if mode not in ['jnl_all', 'excel_jnl_all', 'jnl_count_all']:
                    where_str = textwrap.dedent("""
                        where `{col_name}` IN ( %s )
                        ORDER BY `JOURNAL_REG_DATETIME` DESC
                    """).format(col_name=target_uuid_key).strip()
                else:
                    where_str = textwrap.dedent("""
                        ORDER BY `JOURNAL_REG_DATETIME` DESC
                    """).format(col_name=target_uuid_key).strip()

                sort_key = self.get_sort_key()
                if sort_key is not None:
                    str_orderby = ''
                    where_str = where_str + str_orderby

            if mode in ['nomal', 'excel', 'jnl', 'excel_jnl', 'jnl_all', 'excel_jnl_all']:
                # データ取得
                tmp_result = self.objdbca.table_select(table_name, where_str, bind_value_list)

                # RESTパラメータへキー変換
                for rows in tmp_result:
                    target_uuid = rows.get(primary_key)
                    target_uuid_jnl = rows.get(COLNAME_JNL_SEQ_NO)
                    rest_parameter, rest_file = self.convert_colname_restkey(rows, target_uuid, target_uuid_jnl, mode)
                    tmp_data = {}
                    tmp_data.setdefault(REST_PARAMETER_KEYNAME, rest_parameter)
                    if mode != 'excel' or mode != 'excel_jnl' or mode != 'excel_jnl_all':
                        tmp_data.setdefault(REST_FILE_KEYNAME, rest_file)
                    result_list.append(tmp_data)
            elif mode in ['count', 'count_jnl', 'jnl_count_all']:
                # 件数取得
                tmp_result = self.objdbca.table_count(table_name, where_str, bind_value_list)
                result_list = tmp_result

        except Exception:
            status_code = '999-99999'
            type_, value, traceback_ = sys.exc_info()
            msg = ['{}'.format(traceback.format_exception(type_, value, traceback_))]
        finally:
            result = result_list
        return status_code, result, msg,

    # [maintenance]:メニューのレコード操作
    def rest_maintenance(self, parameters, target_uuid=''):
        """
            RESTAPI[filter]:メニューのレコード操作
            ARGS:
                parameters:パラメータ
                cmd_type: 登録/更新/廃止/復活
            RETRUN:
                status_code, result, msg,
        """
        result_data = []
        result = {
            "result": '',
            "data": {},
            "message": ''
        }
        tmp_data = None
        err_result = {}
        err_all = {}
        
        status_code = '000-00000'  # 成功
        msg = ''
        
        #  登録/更新/廃止/復活 処理
        try:
            # if cmd_type is None:
            cmd_type = parameters.get('type')
            # トランザクション開始
            self.objdbca.db_transaction_start()

            # 対象メニューのテーブルと「ロック対象テーブル」を昇順でロック
            locktable_list = self.get_locktable()
            if locktable_list is not None:
                tmp_result = self.objdbca.table_lock([locktable_list])
            else:
                tmp_result = self.objdbca.table_lock([self.get_table_name()])
            # maintenance呼び出し
            tmp_result = self.exec_maintenance(parameters, target_uuid, cmd_type)

            # 実行結果、一時保存
            result_data.append(tmp_result[1])
            if self.get_message_count(MSG_LEVEL_ERROR) != 0:
                err_result.setdefault(0, self.get_message(MSG_LEVEL_ERROR))
            
            if tmp_result[0] is True:
                # コミット  トランザクション終了
                self.objdbca.db_transaction_end(True)
                tmp_data = self.get_exec_count()
                result = tmp_data
            else:
                # ロールバック トランザクション終了
                self.objdbca.db_transaction_end(False)
                # 想定内エラーの切り戻し処理
                list_exec_result = self.get_exec_result()
                for tmp_exec_result in list_exec_result:
                    entry_parameter = tmp_exec_result.get('parameter')
                    self.exec_restore_action(entry_parameter, tmp_exec_result)

                status_code = '200-00201'
                err_msg_count_flg = 0
                for eno, errs_info in err_result.items():
                    tmp_errs = {}
                    for err_key, err_info in errs_info.items():
                        for err_megs in err_info:
                            if len(err_info) == 1 and len(errs_info) == 1:
                                status_code = err_megs.get('status_code')
                                msg = err_megs.get('msg_args')
                                err_msg_count_flg = 1
                                if msg == '' or status_code == '':
                                    status_code = '200-00201'
                                    err_msg_count_flg = 0
                            else:
                                status_code = '200-00201'
                                err_msg_count_flg = 0
                            tmp_errs.setdefault(err_key, [])
                            tmp_errs[err_key].append(err_megs.get('msg'))
                    err_all[eno] = tmp_errs.copy()

                if err_msg_count_flg == 0:
                    msg = json.dumps(err_all, ensure_ascii=False)
        except Exception:
            result = {}
            # ロールバック トランザクション終了
            self.objdbca.db_transaction_end(False)
            type_, value, traceback_ = sys.exc_info()
            msg = ['{}'.format(traceback.format_exception(type_, value, traceback_))]
            print(msg)
            status_code = "200-00220"
            log_msg_args = []
            api_msg_args = []
            raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405

        return status_code, result, msg,
    
    # [maintenance]:メニューのレコード登録
    def rest_maintenance_all(self, list_parameters):
        """
            RESTAPI[filter]:メニューのレコード取得
            ARGS:
                parameters:パラメータ
                mode: 登録/更新/廃止/復活
            RETRUN:
                status_code, result, msg,
        """

        status_code = '000-00000'  # 成功
        msg = ''
        
        result_data = []
        result = {
            "result": '',
            "data": {},
            "message": ''
        }
        tmp_result = {}
        tmp_data = None
        err_result = {}
        err_all = {}
        try:
            # トランザクション開始
            self.objdbca.db_transaction_start()

            # 対象メニューのテーブルと「ロック対象テーブル」を昇順でロック
            locktable_list = self.get_locktable()
            if locktable_list is not None:
                tmp_result = self.objdbca.table_lock([locktable_list])
            else:
                tmp_result = self.objdbca.table_lock([self.get_table_name()])

            for tmp_parameters in list_parameters:
                eno = list_parameters.index(tmp_parameters)
                cmd_type = tmp_parameters.get("type")
                
                parameters = tmp_parameters

                # テーブル情報（カラム、PK取得）
                column_list = self.get_column_list()
                primary_key = self.get_primary_key()
                target_uuid_key = self.get_rest_key(primary_key)
                if REST_PARAMETER_KEYNAME in parameters:
                    target_uuid = parameters.get(REST_PARAMETER_KEYNAME).get(target_uuid_key)
                else:
                    target_uuid = ''

                # maintenance呼び出し
                tmp_result = self.exec_maintenance(parameters, target_uuid, cmd_type)

                # 実行結果、一時保存
                result_data.append(tmp_result[1])
                if self.get_message_count(MSG_LEVEL_ERROR) != 0:
                    err_result.setdefault(eno, self.get_message(MSG_LEVEL_ERROR))
                # メッセージ初期化
                self.reset_message()
            # エラーなし
            if len(err_result) == 0:
                # コミット
                self.objdbca.db_transaction_end(True)
                tmp_data = self.get_exec_count()
            elif len(err_result) > 0:
                # ロールバック トランザクション終了
                self.objdbca.db_transaction_end(False)
                # 想定内エラーの切り戻し処理
                list_exec_result = self.get_exec_result()
                for tmp_exec_result in list_exec_result:
                    entry_parameter = tmp_exec_result.get('parameter')
                    self.exec_restore_action(entry_parameter, tmp_exec_result)

                status_code = '200-00201'
                err_msg_count_flg = 0
                for eno, errs_info in err_result.items():
                    tmp_errs = {}
                    for err_key, err_info in errs_info.items():
                        for err_megs in err_info:
                            tmp_errs.setdefault(err_key, [])
                            tmp_errs[err_key].append(err_megs.get('msg'))
                    err_all[eno] = tmp_errs.copy()

                if err_msg_count_flg == 0:
                    msg = json.dumps(err_all, ensure_ascii=False)

        except Exception:
            # ロールバック トランザクション終了
            self.objdbca.db_transaction_end(False)
            type_, value, traceback_ = sys.exc_info()
            msg = ['{}'.format(traceback.format_exception(type_, value, traceback_))]
            print(msg)
            status_code = "200-00220"
            log_msg_args = []
            api_msg_args = []
            raise AppException(status_code, log_msg_args, api_msg_args)  # noqa: F405
        
        result = tmp_data

        return status_code, result, msg,

    # [maintenance]:メニューのレコード操作
    def exec_maintenance(self, parameters, target_uuid='', cmd_type=''):
        """
            RESTAPI[filter]:メニューのレコード操作
            ARGS:
                parameters:パラメータ
                cmd_type: 登録/更新/廃止/復活
            RETRUN:
                retBool, result or msg
        """
        retBool = True
        result = {}
        #  登録/更新(廃止/復活) 処理
        try:

            column_list = self.get_column_list()
            primary_key = self.get_primary_key()
            sheet_type = self.get_sheet_type()

            # 各カラム単位の基本処理（前）、個別処理（前）を実施
            # REST用キーのパラメータ、ファイル(base64)
            entry_parameter = parameters.get(REST_PARAMETER_KEYNAME)
            entry_file = parameters.get(REST_FILE_KEYNAME)
            if entry_file is None:
                entry_file = {}
            if target_uuid is None:
                target_uuid = ''

            # 実行種別簡易判定、補完 (target_uuid空:登録,他:更新)
            if target_uuid == '':
                cmd_type = CMD_REGISTER
            else:
                cmd_type = CMD_UPDATE
            # 実行種別簡易判定、補完 (typeにて指定時)
            if 'type' in parameters:
                cmd_type = parameters.get('type')
            # 実行種別簡易判定、補完 (パラメータ内にPK無し:登録,有:更新)
            target_uuid_key = self.get_rest_key(primary_key)

            if cmd_type in [CMD_REGISTER, CMD_UPDATE, CMD_DISCARD, CMD_RESTORE]:
                # テーブル情報（カラム、PK取得）
                column_list, primary_key_list = self.objdbca.table_columns_get(self.get_table_name())
                target_uuid_key = self.get_rest_key(primary_key)
                target_jnls = []
                current_row = {}
                current_parametr = {}
                current_file = {}
                
                # 更新時
                if cmd_type != CMD_REGISTER:
                    tmp_rows = self.get_target_rows(target_uuid)
                    
                    if len(tmp_rows) != 1:
                        status_code = '200-00205'
                        msg_args = [target_uuid]
                        msg = g.appmsg.get_api_message(status_code, msg_args)
                        dict_msg = {
                            'status_code': status_code,
                            'msg_args': msg_args,
                            'msg': msg,
                        }
                        self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
                    else:
                        current_row = tmp_rows[0]
                        target_uuid = current_row.get(primary_key)
                        target_uuid_jnl = current_row.get(COLNAME_JNL_SEQ_NO)
                        current_parametr, current_file = self.convert_colname_restkey(current_row, target_uuid, '', 'input')
                        # 更新系の追い越し判定
                        self.chk_lastupdatetime(target_uuid, current_parametr, entry_parameter)
                        # 更新系処理の場合、廃止フラグから処理種別判定、変更
                        cmd_type = self.convert_cmd_type(cmd_type, target_uuid, current_row, entry_parameter)
                        # 履歴の一括取得
                        target_jnls = self.get_target_jnl_uuids(target_uuid)

                # 処理種別の権限確認(メッセージ集約せずに、400系エラーを返却)
                exec_authority = self.check_authority_cmd(cmd_type)
                if exec_authority[0] is not True:
                    return exec_authority
                # 不要パラメータの除外
                entry_parameter = self.exclusion_parameter(cmd_type, entry_parameter)
                # 必須項目チェック
                self.chk_required(cmd_type, entry_parameter)

                # 登録時、primary_key指定時の重複チェック
                exec_chk_primay_val = self.chk_primay_val(entry_parameter, target_uuid_key, target_uuid, cmd_type)
                if exec_chk_primay_val is True:
                    if cmd_type == CMD_REGISTER:
                        if target_uuid_key in entry_parameter:
                            tmp_uuid_val = entry_parameter[target_uuid_key]
                            if tmp_uuid_val == '' or tmp_uuid_val is None:
                                del entry_parameter[target_uuid_key]

                # PK 埋め込み table_insert table_update用
                if cmd_type != CMD_REGISTER and target_uuid != '':
                    # 更新系処理時 uuid 埋め込み
                    target_uuid_key = self.get_rest_key(primary_key)
                    entry_parameter[target_uuid_key] = target_uuid
                # 各カラム単位の基本処理（前）、個別処理（前）を実施
                for rest_key in list(entry_parameter.keys()):
                    rest_val = entry_parameter.get(rest_key)
                    if rest_key in self.restkey_list:
                        target_col_option = {
                            'uuid': target_uuid,
                            'uuid_jnl': '',
                            'cmd_type': cmd_type,
                            'rest_key_name': rest_key,
                            'col_name': self.get_col_name(rest_key),
                            'file_name': '',
                            'file_data': '',
                            'entry_parameter': {
                                'parameter': entry_parameter,
                                'file': entry_file,
                            },
                            'current_parameter': {
                                'parameter': current_parametr,
                                'file': current_file,
                            }
                        }
                        # ファイル有無
                        if entry_file is not None:
                            if rest_key in entry_file:
                                target_col_option['file_name'] = rest_val
                                target_col_option['file_data'] = entry_file.get(rest_key)

                        # カラムクラス呼び出し
                        objcolumn = self.get_columnclass(rest_key, cmd_type)

                        # カラムクラス毎の処理:レコード操作前 + カラム毎の個別処理:レコード操作前
                        tmp_exec = objcolumn.before_iud_action(rest_val, target_col_option)
                        if tmp_exec[0] is not True:
                            dict_msg = {
                                'status_code': '',
                                'msg_args': '',
                                'msg': tmp_exec[1],
                            }
                            self.set_message(dict_msg, rest_key, MSG_LEVEL_ERROR)
                        else:
                            target_col_option = tmp_exec[3]
                            entry_parameter = target_col_option.get('entry_parameter').get('parameter')
                            entry_file = target_col_option.get('entry_parameter').get('file')
                            rest_val = entry_parameter.get(rest_key)
                            # entry_file[rest_key] = target_col_option.get('file_data')

                            if rest_val is not None:
                                # VALUE 変換処理不要ならVALUE変更無し
                                tmp_exec = objcolumn.convert_value_input(rest_val)
                                if tmp_exec[0] is True:
                                    entry_parameter[rest_key] = tmp_exec[2]
                                else:
                                    dict_msg = {
                                        'status_code': '',
                                        'msg_args': '',
                                        'msg': tmp_exec[1],
                                    }
                                    self.set_message(dict_msg, rest_key, MSG_LEVEL_ERROR)

                # メニュー共通処理:レコード操作前 組み合わせ一意制約
                self.exec_unique_constraint(entry_parameter, target_uuid)

                # メニュー、カラム個別処理:レコード操作前
                target_menu_option = {
                    'uuid': target_uuid,
                    'uuid_jnl': '',
                    'cmd_type': cmd_type,
                    'rest_key_name': '',
                    'col_name': '',
                    'file_data': '',
                    'entry_parameter': {
                        'parameter': entry_parameter,
                        'file': entry_file,
                    },
                    'current_parameter': {
                        'parameter': current_parametr,
                        'file': current_file,
                    }
                }
                tmp_exec = self.exec_menu_before_validate(target_menu_option)

                if tmp_exec[0] is not True:
                    dict_msg = {
                        'status_code': '',
                        'msg_args': '',
                        'msg': tmp_exec[1],
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
                else:
                    target_menu_option = tmp_exec[2]
                    entry_parameter = target_menu_option.get('entry_parameter').get('parameter')
                    entry_file = target_menu_option.get('entry_parameter').get('file')

                # レコード操作前エラー確認
                if self.get_message_count(MSG_LEVEL_ERROR) > 0:
                    retBool = False
                    status_code = '200-00201'
                    msg = self.get_message(MSG_LEVEL_ERROR)
                    return retBool, status_code, msg

                base_cols_val = self.base_cols_val.copy()
                
                # 廃止の設定
                if cmd_type == CMD_DISCARD:
                    base_cols_val[REST_KEY_DISCARD] = 1
                else:
                    base_cols_val[REST_KEY_DISCARD] = 0

                entry_parameter.update(base_cols_val)

                for rest_key in list(entry_parameter.keys()):
                    if self.chk_restkey(rest_key) is not True:
                        status_code = '200-00209'
                        msg_args = [rest_key]
                        msg = g.appmsg.get_api_message(status_code, msg_args)
                        dict_msg = {
                            'status_code': status_code,
                            'msg_args': msg_args,
                            'msg': msg,
                        }
                        self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
                        return retBool, status_code, msg
                # rest_key → カラム名に変換
                colname_parameter = self.convert_restkey_colname(entry_parameter, current_row)
                # 登録・更新処理
                if cmd_type == CMD_REGISTER:
                    result = self.objdbca.table_insert(self.get_table_name(), colname_parameter, primary_key)
                elif cmd_type == CMD_UPDATE:
                    result = self.objdbca.table_update(self.get_table_name(), colname_parameter, primary_key)
                elif cmd_type == CMD_DISCARD:
                    result = self.objdbca.table_update(self.get_table_name(), colname_parameter, primary_key)
                elif cmd_type == CMD_RESTORE:
                    result = self.objdbca.table_update(self.get_table_name(), colname_parameter, primary_key)

                result_uuid = ''
                result_uuid_jnl = ''
                if result is False:
                    dict_msg = {
                        'status_code': '',
                        'msg_args': '',
                        'msg': result,
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
                else:
                    result_uuid = result[0].get(primary_key_list[0])
                    result_uuid_jnl = self.get_maintenance_uuid(result_uuid)[0].get(COLNAME_JNL_SEQ_NO)
                    temp_rows = {primary_key_list[0]: result[0].get(primary_key_list[0])}
                    tmp_result = self.convert_colname_restkey(temp_rows)
                    result = tmp_result[0]

                # レコード操作後エラー確認
                if self.get_message_count(MSG_LEVEL_ERROR) > 0:
                    retBool = False
                    status_code = '200-00201'
                    msg = self.get_message(MSG_LEVEL_ERROR)
                    return retBool, status_code, msg

                # 各カラム単位の基本処理（後）、個別処理（後）を実施
                for rest_key, rest_val in entry_parameter.items():
                    # カラムクラス呼び出し
                    objcolumn = self.get_columnclass(rest_key, cmd_type)
                    
                    target_col_option = {}
                    target_col_option.setdefault("uuid", result_uuid)
                    target_col_option.setdefault("uuid_jnl", result_uuid_jnl)
                    target_col_option.setdefault("cmd_type", cmd_type)
                    target_col_option.setdefault("rest_key_name", rest_key)
                    target_col_option.setdefault("col_name", self.get_col_name(rest_key))
                    # ファイル有無
                    if entry_file is not None:
                        if rest_key in entry_file:
                            target_col_option.setdefault("file_data", entry_file.get(rest_key))
                    # カラムクラス毎の処理:レコード操作後 ,カラム毎の個別処理:レコード操作後
                    tmp_exec = objcolumn.after_iud_action(rest_val, target_col_option)
                    if tmp_exec[0] is not True:
                        dict_msg = {
                            'status_code': '',
                            'msg_args': '',
                            'msg': tmp_exec[1],
                        }
                        self.set_message(dict_msg, rest_key, MSG_LEVEL_ERROR)
                        
                # テーブル単位の個別処理後を実行
                # メニュー、カラム個別処理:レコード操作後
                target_menu_option['uuid_jnl'] = result_uuid_jnl
                target_menu_option['entry_parameter']['parameter'] = entry_parameter
                target_menu_option['entry_parameter']['file'] = entry_file

                tmp_exec = self.exec_menu_after_validate(target_menu_option)
                if tmp_exec[0] is not True:
                    dict_msg = {
                        'status_code': '',
                        'msg_args': '',
                        'msg': tmp_exec[1],
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
                else:
                    target_menu_option = tmp_exec[2]
                    entry_parameter = target_menu_option.get('entry_parameter').get('parameter')
                    entry_file = target_menu_option.get('entry_parameter').get('file')

                # 実行結果を保存
                target_result_info = {}
                target_result_info.setdefault("uuid", result_uuid)
                target_result_info.setdefault("uuid_jnl", result_uuid_jnl)
                target_result_info.setdefault("parameter", entry_parameter)
                target_result_info.setdefault("target_jnls", target_jnls)
                self.set_exec_result(target_result_info)
                
                # レコード操作後エラー確認
                if self.get_message_count(MSG_LEVEL_ERROR) > 0:
                    retBool = False
                    status_code = '200-00201'
                    msg = self.get_message(MSG_LEVEL_ERROR)
                    return retBool, status_code, msg

                # 実行種別件数カウントアップ
                self.set_exec_count_up(cmd_type)

            else:
                # 実行種別エラー
                retBool = False
                status_code = '200-00210'
                msg_args = [cmd_type]
                msg = g.appmsg.get_api_message(status_code, msg_args)
                dict_msg = {
                    'status_code': status_code,
                    'msg_args': msg_args,
                    'msg': msg,
                }
                self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)

        except Exception:
            retBool = False
            status_code = '999-99999'
            type_, value, traceback_ = sys.exc_info()
            msg_args = ['{}'.format(traceback.format_exception(type_, value, traceback_))]
            msg = g.appmsg.get_api_message(status_code, msg_args)
            print(msg)
            dict_msg = {
                'status_code': status_code,
                'msg_args': msg_args,
                'msg': msg,
            }
            if self.get_message_count(MSG_CODE) == 0:
                self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR, status_code)

        return retBool, result

    # []:RESTパラメータのキー変換
    def convert_restkey_colname(self, parameter, rows):
        """
            []::RESTパラメータのキー変換
            ARGS:
                parameter:パラメータ
                rows: 現在のDB上の値
            RETRUN:
                {}
        """
        result = {}
        json_data = {}
        json_data_colname = ''
        json_cols_base = self.get_json_cols_base()
        # RESTパラメータのキー→DBカラム名に変更
        for restkey, restval in parameter.items():
            colname = self.get_col_name(restkey)
            save_type = self.get_save_type(restkey)
            if save_type == 'JSON':
                json_data_colname = colname
                json_data.setdefault(restkey, restval)
            if colname is not None:
                result.setdefault(colname, restval)
        if len(json_data_colname) > 0:
            # 更新時の未入力項目補完
            if json_data_colname in rows:
                try:
                    base_json_data = json.loads(rows.get(json_data_colname))
                    base_json_data.update(json_data)
                except Exception:
                    base_json_data = {}
            else:
                base_json_data = json_data
            json_cols_base.update(base_json_data)
            result[json_data_colname] = json.dumps(json_cols_base, ensure_ascii=False)

        return result

    def convert_colname_restkey(self, rows, target_uuid='', target_uuid_jnl='', mode='normal'):
        """
            []::RESTパラメータへキー変換
            ARGS:
                parameter:パラメータ
                mode: normal/input/excel/excel_jnl
            RETRUN:
                {}
        """
        rest_parameter = {}
        rest_file = {}
        for col_name, col_val in rows.items():
            # メニュー作成パラメータDATA_JSON構造
            if col_name == 'DATA_JSON':
                try:
                    json_rows = json.loads(col_val)
                except Exception:
                    json_rows = col_val
                for jsonkey, jsonval in json_rows.items():
                    rest_parameter.setdefault(jsonkey, jsonval)
                    if mode not in ['excel', 'excel_jnl']:
                        if self.get_col_class_name(jsonkey) == 'FileUploadColumn':
                            objcolumn = self.get_columnclass(jsonkey)
                            # ファイル取得＋64変換
                            file_data = objcolumn.get_file_data(jsonval, target_uuid, target_uuid_jnl)
                            rest_file.setdefault(jsonkey, file_data)
            else:
                rest_key = self.get_rest_key(col_name)
                view_item = self.get_objcol(rest_key)

                if view_item is not None:
                    view_item = view_item.get(COLNAME_VIEW_ITEM)
                else:
                    view_item = "1"
    
                auto_input_item = self.get_objcol(rest_key)
                if auto_input_item is not None:
                    auto_input_item = auto_input_item.get(COLNAME_AUTO_INPUT)
                else:
                    auto_input_item = "0"

                if len(rest_key) > 0:

                    if isinstance(col_val, datetime.datetime):
                        col_val = '{}'.format(col_val.strftime('%Y/%m/%d %H:%M:%S.%f'))
                    objcolumn = self.get_columnclass(rest_key)

                    # ID → VALUE 変換処理不要ならVALUE変更無し
                    tmp_exec = objcolumn.convert_value_output(col_val)
                    if tmp_exec[0] is True:
                        col_val = tmp_exec[2]

                    # 内部処理用
                    if mode in ['input']:
                        if self.get_col_class_name(rest_key) in ['PasswordColumn', 'SensitiveSingleTextColumn', 'SensitiveMultiTextColumn']:
                            objcolumn = self.get_columnclass(rest_key)
                            col_val = util.ky_decrypt(col_val)    # noqa: F405

                    if mode in ['input']:
                        rest_parameter.setdefault(rest_key, col_val)
                    else:
                        if view_item == '1' or auto_input_item == '1':
                            rest_parameter.setdefault(rest_key, col_val)

                    if mode not in ['excel', 'excel_jnl']:
                        if self.get_col_class_name(rest_key) == 'FileUploadColumn':
                            objcolumn = self.get_columnclass(rest_key)
                            # ファイル取得＋64変換
                            file_data = objcolumn.get_file_data(col_val, target_uuid, target_uuid_jnl)
                            rest_file.setdefault(rest_key, file_data)

        return rest_parameter, rest_file

    # []:組み合わせ一意制約の実施
    def exec_unique_constraint(self, parameter, target_uuid):
        """
            []::組み合わせ一意制約の実施
            ARGS:
                parameter:パラメータ
                target_uuid:対象pk(uuid)
            RETRUN:
                {}
        """
        msg = ''
        # 組み合わせ一意設定取得
        unique_constraint = self.get_unique_constraint()
        if unique_constraint is not None:
            column_list, primary_key_list = self.objdbca.table_columns_get(self.get_table_name())
            tmp_constraint = json.loads(unique_constraint)
            # 組み合わせ一意検索用Where句生成
            for tmp_uq in tmp_constraint:
                bind_value_list = []
                where_str = ''
                dict_bind_kv = {}
                for tmp_constraint_key in tmp_uq:
                    conjunction = 'where'
                    if len(where_str) != 0:
                        conjunction = 'and'
                    objcol = self.get_objcol(tmp_constraint_key)
                    # カラム名,rest_name_keyか判定
                    if tmp_constraint_key in column_list:
                        tmp_where_str = " `{}` = %s ".format(tmp_constraint_key)
                        where_str = where_str + ' {} {}'.format(conjunction, tmp_where_str)
                        val = parameter.get(self.get_rest_key(tmp_constraint_key))
                        bind_value_list.append(val)
                        objcolumn = self.get_columnclass(self.get_rest_key(tmp_constraint_key))
                        tmp_bool, tmp_msg, output_val = objcolumn.convert_value_output(val)
                        dict_bind_kv.setdefault(self.get_rest_key(tmp_constraint_key), output_val)
                    else:
                        objcol = self.get_objcol(tmp_constraint_key)
                        if objcol is not None:
                            seve_type = self.get_save_type(tmp_constraint_key)
                            if seve_type == 'JSON':
                                where_str = where_str + conjunction + ' JSON_UNQUOTE(JSON_EXTRACT(`{}`,"$.{}")) = %s '.format(
                                    self.get_col_name(tmp_constraint_key),
                                    tmp_constraint_key,
                                )
                                val = parameter.get(tmp_constraint_key)
                                bind_value_list.append(val)
                                objcolumn = self.get_columnclass(tmp_constraint_key)
                                tmp_bool, tmp_msg, output_val = objcolumn.convert_value_output(val)
                                dict_bind_kv.setdefault(tmp_constraint_key, output_val)
                            else:
                                tmp_constraint_col_name = self.get_col_name(tmp_constraint_key)
                                tmp_where_str = " `{}` = %s ".format(tmp_constraint_col_name)
                                where_str = where_str + ' {} {}'.format(conjunction, tmp_where_str)
                                val = parameter.get(tmp_constraint_key)
                                bind_value_list.append(val)
                                objcolumn = self.get_columnclass(tmp_constraint_key)
                                tmp_bool, tmp_msg, output_val = objcolumn.convert_value_output(val)
                                dict_bind_kv.setdefault(tmp_constraint_key, output_val)
                # 更新時自身をIDを除外
                if target_uuid is not None:
                    if len(target_uuid) != 0:
                        where_str = where_str + " and `{}` <> %s ".format(primary_key_list[0])
                        bind_value_list.append(target_uuid)

                table_count = self.objdbca.table_select(self.get_table_name(), where_str, bind_value_list)
                if len(table_count) != 0:
                    list_uuids = []
                    for table_count_rows in table_count:
                        list_uuids.append(table_count_rows.get(primary_key_list[0]))
                    
                    status_code = '200-00204'
                    msg_args = [str(dict_bind_kv), str(list_uuids)]
                    msg = g.appmsg.get_api_message(status_code, msg_args)
                    dict_msg = {
                        'status_code': status_code,
                        'msg_args': msg_args,
                        'msg': msg,
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)

    # []:PK指定時の重複チェックの実施
    def chk_primay_val(self, entry_parameter, target_uuid_key, primary_val, cmd_type):
        """
            PK指定時の重複チェックの実施(登録時PK指定時のみ)
            ARGS:
                entry_parameter:パラメータ
                target_uuid_key: PKのrest_name
                primary_val:値
                cmd_type: 実行種別
            RETRUN:
                bool
        """
        
        retBool = True
        msg = ''
        if cmd_type == CMD_REGISTER:
            if primary_val is None or primary_val == '':
                primary_val = entry_parameter.get(target_uuid_key)

            if primary_val is not None:
                where_str = " where  `{}` = %s ".format(self.get_primary_key())
                bind_value_list = [primary_val]
                table_count = self.objdbca.table_select(self.get_table_name(), where_str, bind_value_list)
                if len(table_count) != 0:
                    retBool = False
                    status_code = '200-00219'
                    msg_args = [cmd_type, target_uuid_key, primary_val]
                    msg = g.appmsg.get_api_message(status_code, msg_args)
                    dict_msg = {
                        'status_code': status_code,
                        'msg_args': msg_args,
                        'msg': msg,
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
        return retBool

    # []: レコード操作前処理の実施(メニュー)
    def exec_menu_before_validate(self, target_option):
        """
            []::レコード操作前処理の実施(メニュー)
            ARGS:
                parameter:パラメータ
            RETRUN:
                {}
        """
        retBool = True
        msg = ''
        exec_config = self.get_menu_before_validate_register()
        # parameter = target_option.get('parameter')
        # file = target_option.get('file')
        external_validate_path = 'common_libs.validate.valid_{}'.format(self.get_menu_id())
        if exec_config is not None:
            if exec_config is not None:
                exec_func = importlib.import_module(external_validate_path)  # noqa: F841
                eval_str = 'exec_func.{}(self.objdbca, self.objtable, target_option)'.format(exec_config)
                tmp_exec = eval(eval_str)

                if tmp_exec[0] is not True:
                    retBool = False
                    msg = tmp_exec[1]
                else:
                    target_option = tmp_exec[2]

        return retBool, msg, target_option,

    # []:レコード操作後処理の実施(メニュー)
    def exec_menu_after_validate(self, target_option):
        """
            []::レコード操作後処理の実施(メニュー)
            ARGS:
                parameter:パラメータ
            RETRUN:
                {}
        """
        retBool = True
        msg = ''
        exec_config = self.get_menu_after_validate_register()
        # parameter = target_option.get('parameter')
        # file = target_option.get('file')
        external_validate_path = 'common_libs.validate.valid_{}'.format(self.get_menu_id())
        if exec_config is not None:
            if exec_config is not None:
                exec_func = importlib.import_module(external_validate_path)  # noqa: F841
                eval_str = 'exec_func.{}(self.objdbca, self.objtable, target_option)'.format(exec_config)
                tmp_exec = eval(eval_str)
                if tmp_exec[0] is not True:
                    retBool = False
                    msg = tmp_exec[1]
                else:
                    target_option = tmp_exec[2]

        return retBool, msg, target_option,

    # []:想定内エラーの切り戻し処理
    def exec_restore_action(self, entry_parameter, target_option):
        """
            []:::想定内エラーの切り戻し処理
            ARGS:
                parameter:パラメータ
            RETRUN:
                {}
        """
        retBool = True
        msg = ''
        # 各カラム単位の基本処理（後）、個別処理（後）を実施
        for rest_key, rest_val in entry_parameter.items():
            # カラムクラス呼び出し
            objcolumn = self.get_columnclass(rest_key)
            # カラムクラス毎の処理:レコード操作後 ,カラム毎の個別処理:レコード操作後
            tmp_exec = objcolumn.after_iud_restore_action(rest_val, target_option)
            if tmp_exec[0] is not True:
                pass
        return retBool, msg,

    def check_authority_cmd(self, cmd_type=''):
        """
            実行種別権限チェック
            ARGS:
                cmd_type:実行種別
            RETRUN:
                retBool, msg,
        """
        retBool = True
        status_code = ''
        msg_args = ''
        if cmd_type != '':
            menuinfo = self.get_objtable().get(MENUINFO)
            authority_val = ''
            if cmd_type == CMD_REGISTER:
                authority_val = menuinfo.get(COLNAME_ROW_INSERT_FLAG)
            elif cmd_type == CMD_UPDATE:
                authority_val = menuinfo.get(COLNAME_ROW_UPDATE_FLAG)
            elif cmd_type == CMD_DISCARD:
                authority_val = menuinfo.get(COLNAME_ROW_DISUSE_FLAG)
            elif cmd_type == CMD_RESTORE:
                authority_val = menuinfo.get(COLNAME_ROW_REUSE_FLAG)
            
            # authority_val = "2"
            if authority_val != "1":
                retBool = False
                status_code = '401-00002'
                msg_args = [cmd_type, menuinfo.get('MENU_NAME_REST')]
                msg = g.appmsg.get_api_message(status_code, msg_args)
                dict_msg = {
                    'status_code': status_code,
                    'msg_args': msg_args,
                    'msg': msg,
                }
                self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)

        return retBool, status_code, msg_args,

    def chk_lastupdatetime(self, target_uuid, current_parameter, entry_parameter):
        """
            更新系の追い越し判定
            ARGS:
                current_parameter:現状の最終更新日時
                lastupdatetime_parameter:パラメータ内の最終更新日時
        """
        try:
            lastupdatetime_current = current_parameter.get('last_update_date_time')
            lastupdatetime_parameter = entry_parameter.get('last_update_date_time')
            if lastupdatetime_parameter is None:
                status_code = '200-00211'
                msg_args = [lastupdatetime_parameter]
                msg = g.appmsg.get_api_message(status_code, msg_args)
                dict_msg = {
                    'status_code': status_code,
                    'msg_args': msg_args,
                    'msg': msg,
                }
                self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
            else:
                lastupdatetime_current = lastupdatetime_current.replace('-', '/')
                lastupdatetime_parameter = lastupdatetime_parameter.replace('-', '/')
                lastupdatetime_current = datetime.datetime.strptime(lastupdatetime_current, '%Y/%m/%d %H:%M:%S.%f')
                lastupdatetime_parameter = datetime.datetime.strptime(lastupdatetime_parameter, '%Y/%m/%d %H:%M:%S.%f')
                
                # 更新系の追い越し判定
                if lastupdatetime_current != lastupdatetime_parameter:
                    # if (lastupdatetime_current < lastupdatetime_parameter) is False:
                    status_code = '200-00203'
                    msg_args = [target_uuid]
                    msg = g.appmsg.get_api_message(status_code, msg_args)
                    dict_msg = {
                        'status_code': status_code,
                        'msg_args': msg_args,
                        'msg': msg,
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
        except ValueError as msg_args:
            status_code = '200-00211'
            msg_args = [lastupdatetime_parameter]
            msg = g.appmsg.get_api_message(status_code, msg_args)
            dict_msg = {
                'status_code': status_code,
                'msg_args': msg_args,
                'msg': msg,
            }
            self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
            
    def convert_cmd_type(self, cmd_type, target_uuid, row_data, entry_parameter):
        """
            廃止フラグによる、処理種別判定
            ARGS:
                row_data:DB上の値
                entry_parameter:パラメータの値
            RETRUN:
                cmd_type
        """
        
        # 廃止フラグによる、処理種別判定
        if "discard" in entry_parameter:
            tmp_discard = entry_parameter.get(REST_KEY_DISCARD)
            discard_key = self.get_col_name(REST_KEY_DISCARD)
            discard_row = row_data.get(discard_key)
            discard_parameter = entry_parameter.get(REST_KEY_DISCARD)

            if discard_row is not None and discard_parameter is not None:
                if tmp_discard in ['1', 1]:
                    cmd_type = CMD_DISCARD
                elif tmp_discard in ['0', 0] and discard_row in ['1', 1]:
                    cmd_type = CMD_RESTORE
                else:
                    cmd_type = CMD_UPDATE

                # 廃止→廃止の場合エラー
                if cmd_type == CMD_DISCARD and discard_row in ['1', 1] and discard_parameter in ['1', 1]:
                    status_code = '200-00206'
                    msg_args = [target_uuid]
                    msg = g.appmsg.get_api_message(status_code, msg_args)
                    dict_msg = {
                        'status_code': status_code,
                        'msg_args': msg_args,
                        'msg': msg,
                    }
                    self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
            
        return cmd_type

    def exclusion_parameter(self, cmd_type, parameter):
        """
            不要項目の除外
            ARGS:
                cmd_type:実行種別
                parameter:パラメータ
            RETRUN:
                parameter
        """
        # テーブル情報（カラム、PK取得）
        column_list, primary_key_list = self.objdbca.table_columns_get(self.get_table_name())
        # 入力項目 PK以外除外
        err_keys = []
        for tmp_keys in list(parameter.keys()):
            if self.chk_restkey(tmp_keys) is True:
                objcol = self.get_objcol(tmp_keys)
                if objcol is not None:
                    input_item = objcol.get(COLNAME_INPUT_ITEM)
                    tmp_col_name = self.get_col_name(tmp_keys)
                    if input_item != '1':
                        if tmp_col_name not in column_list:
                            del parameter[tmp_keys]

                    # 最終更新者を除外
                    if tmp_col_name == 'LAST_UPDATE_USER':
                        del parameter[tmp_keys]

                    # 登録時最終更新日時を除外
                    if cmd_type == CMD_REGISTER:
                        if tmp_col_name == 'LAST_UPDATE_TIMESTAMP':
                            del parameter[tmp_keys]

                    if cmd_type == CMD_DISCARD:
                        if tmp_col_name not in primary_key_list:
                            # 廃止時に備考の更新は例外で可
                            if tmp_col_name != 'NOTE':
                                del parameter[tmp_keys]
                    self.set_columnclass(tmp_keys, cmd_type)
                else:
                    del parameter[tmp_keys]
                    err_keys.append(tmp_keys)
            else:
                del parameter[tmp_keys]
                err_keys.append(tmp_keys)

        # 不正なキーがある場合エラー
        if len(err_keys) != 0:
            err_keys = ",".join(map(str, err_keys))
            status_code = '200-00212'
            msg_args = [err_keys]
            msg = g.appmsg.get_api_message(status_code, msg_args)
            dict_msg = {
                'status_code': status_code,
                'msg_args': msg_args,
                'msg': msg,
            }
            self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
        return parameter

    def chk_required(self, cmd_type, parameter):
        """
            必須項目数チェック
            ARGS:
                cmd_type:実行種別
                parameter:パラメータ
        """
        status_code = ''
        msg = ''
        # required 簡易チェック
        if cmd_type == CMD_REGISTER:
            required_restkey_list = self.get_required_restkey_list()
            if len(required_restkey_list) <= len(parameter):
                for required_restkey in required_restkey_list:
                    if required_restkey not in parameter:
                        status_code = '200-00207'
                        msg_args = [required_restkey]
                        msg = g.appmsg.get_api_message(status_code, [msg_args])
            else:
                status_code = '200-00207'
                msg_args = [",".join(required_restkey_list)]
                msg = g.appmsg.get_api_message(status_code, [msg_args])

        if status_code != '':
            dict_msg = {
                'status_code': status_code,
                'msg_args': msg_args,
                'msg': msg,
            }
            self.set_message(dict_msg, '__line__', MSG_LEVEL_ERROR)
