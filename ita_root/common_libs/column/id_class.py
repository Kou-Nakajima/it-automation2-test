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

import os
import sys
from flask import g

# import column_class
from .column_class import Column

"""
カラムクラス個別処理(Id)
"""


class IDColumn(Column):
    """
    テキスト系クラス共通処理
    """
    def __init__(self, objdbca, objtable, rest_key_name, cmd_type):
        # カラムクラス名
        self.class_name = self.__class__.__name__
        # メッセージ
        self.message = ''
        # バリデーション閾値
        self.dict_valid = {}
        # テーブル情報
        self.objtable = objtable

        # テーブル名
        table_name = ''
        objmenu = objtable.get('MENUINFO')
        if objmenu is not None:
            table_name = objmenu.get('TABLE_NAME')
        self.table_name = table_name

        # カラム名
        col_name = ''
        objcols = objtable.get('COLINFO')
        if objcols is not None:
            objcol = objcols.get(rest_key_name)
            if objcol is not None:
                col_name = objcol.get('COL_NAME')

        self.col_name = col_name
        
        # rest用項目名
        self.rest_key_name = rest_key_name

        self.db_qm = "'"

        self.objdbca = objdbca
        
        self.cmd_type = cmd_type
        
    def check_basic_valid(self, val, option={}):
        """
            バリデーション処理(カラムクラス毎)
            ARGS:
                val:値
                option:オプション
            RETRUN:
                ( True / False , メッセージ )
        """
        retBool = True
        user_env = g.LANGUAGE.upper()
        table_name = self.get_objcol().get("REF_TABLE_NAME")
        
        # 連携先のテーブルが言語別のカラムを持つか判定
        ref_malti_lang = self.get_objcol().get("REF_MULTI_LANG")
        if ref_malti_lang == '1':
            ref_col_name = "{}_{}".format(self.get_objcol().get("REF_COL_NAME"), user_env)
        else:
            ref_col_name = "{}".format(self.get_objcol().get("REF_COL_NAME"))

        where_str = "WHERE {} = %s".format(ref_col_name)
        bind_value_list = [val]
        
        return_values = self.objdbca.table_select(table_name, where_str, bind_value_list)
        
        # 返却値が存在するか確認
        if len(return_values) == 0:
            retBool = False
            status_code = '499-00218'
            msg_args = [self.get_rest_key_name(),table_name, val]
            msg = g.appmsg.get_api_message(status_code, msg_args)
            return retBool, msg
        
        return retBool,

    # [load_table] 値を入力用の値へ変換
    def convert_value_input(self, val=''):
        """
            値を入力用の値へ変換
            ARGS:
                val:値
            RETRUN:
                retBool, msg, val
        """
        retBool = True
        msg = ''
        if val is not None:
            try:
                user_env = g.LANGUAGE.upper()
                table_name = self.get_objcol().get("REF_TABLE_NAME")
                
                # 連携先のテーブルが言語別のカラムを持つか判定
                ref_malti_lang = self.get_objcol().get("REF_MULTI_LANG")
                if ref_malti_lang == '1':
                    ref_col_name = "{}_{}".format(self.get_objcol().get("REF_COL_NAME"), user_env)
                else:
                    ref_col_name = "{}".format(self.get_objcol().get("REF_COL_NAME"))
                where_str = "WHERE {} = %s".format(ref_col_name)
                bind_value_list = [val]
                return_values = self.objdbca.table_select(table_name, where_str, bind_value_list)
                if len(return_values) == 1:
                    ref_pkey_name = "{}".format(self.get_objcol().get("REF_PKEY_NAME"))
                    val = return_values[0].get(ref_pkey_name)
                else:
                    raise Exception('')
            except Exception as e:
                retBool = False
                status_code = '499-00218'
                msg_args = [self.get_rest_key_name(),table_name, val]
                msg = g.appmsg.get_api_message(status_code, msg_args)

        return retBool, msg, val,

    # [load_table] 値を出力用の値へ変換
    def convert_value_output(self, val=''):
        """
            値を出力用の値へ変換
            ARGS:
                val:値
            RETRUN:
                retBool, msg, val
        """

        retBool = True
        msg = ''
        
        if val is not None:
            try:
                user_env = g.LANGUAGE.upper()
                table_name = self.get_objcol().get("REF_TABLE_NAME")
                where_str = "WHERE {} = %s".format(self.get_objcol().get("REF_PKEY_NAME"))
                bind_value_list = [val]
                return_values = self.objdbca.table_select(table_name, where_str, bind_value_list)
                if len(return_values) == 1:
                    # 連携先のテーブルが言語別のカラムを持つか判定
                    ref_malti_lang = self.get_objcol().get("REF_MULTI_LANG")
                    if ref_malti_lang == '1':
                        ref_col_name = "{}_{}".format(self.get_objcol().get("REF_COL_NAME"), user_env)
                    else:
                        ref_col_name = "{}".format(self.get_objcol().get("REF_COL_NAME"))
                    val = return_values[0].get(ref_col_name)

                else:
                    raise Exception()
            except Exception as e:
                status_code = 'MSG-00001'
                msg_args = [val]
                val = g.appmsg.get_api_message(status_code, msg_args)
                
        return retBool, msg, val,
