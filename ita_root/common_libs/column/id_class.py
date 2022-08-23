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
            msg_args = [self.get_rest_key_name(), table_name, val]
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
                msg_args = [self.get_rest_key_name(), table_name, val]
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

    # [filter] SQL生成用のwhere句
    def get_filter_query(self, search_mode, search_conf):
        """
            SQL生成用のwhere句関連
            ARGS:
                search_mode: 検索種別[LIST/NOMAL/RANGE]
                search_conf: 検索条件
            RETRUN:
                {"bindkey":XXX,bindvalue :{ XXX: val },where: string }
        """

        result = {}
        tmp_conf = []
        listno = 0
        bindkeys = []
        bindvalues = {}
        str_where = ''
        conjunction = ''
        master_where = "WHERE `DISUSE_FLAG` = '0' "
        save_type = self.get_save_type()
        user_env = g.LANGUAGE.upper()

        # 連携先のテーブルが言語別のカラムを持つか判定
        ref_malti_lang = self.get_objcol().get("REF_MULTI_LANG")
        if ref_malti_lang == '1':
            ref_col_name = "{}_{}".format(self.get_objcol().get("REF_COL_NAME"), user_env)
        else:
            ref_col_name = "{}".format(self.get_objcol().get("REF_COL_NAME"))

        ref_pkey_name = "{}".format(self.get_objcol().get("REF_PKEY_NAME"))
        ref_table_name = self.get_objcol().get("REF_TABLE_NAME")

        if search_mode == "LIST":

            if len(search_conf) > 0:
                tmp_where = ",".join(["%s"] * len(search_conf))
                master_where = (master_where + "AND `{}` IN (" + tmp_where + ")").format(ref_col_name)

            return_values = self.objdbca.table_select(ref_table_name, master_where, search_conf)

            if len(return_values) > 0:
                for return_value in return_values:
                    tmp_conf.append(return_value.get(ref_pkey_name))
            else:
                tmp_conf.append("NOT FOUND")

        if search_mode == "NORMAL":
            if len(search_conf) > 0:
                master_where = (master_where + "AND `{}` LIKE %s").format(ref_col_name)

            return_values = self.objdbca.table_select(ref_table_name, master_where, ['%' + search_conf + '%'])

            if len(return_values) > 0:
                for return_value in return_values:
                    tmp_conf.append(return_value.get(ref_pkey_name))
            else:
                tmp_conf.append("NOT FOUND")

        if search_mode in ["LIST", "NORMAL"]:
            if save_type == 'JSON':
                for bindvalue in tmp_conf:

                    if len(str_where) != 0:
                        conjunction = 'or'
                    str_where = str_where + ' ' + conjunction + ' JSON_CONTAINS(`{}`, \'"{}"\', "$.{}")'.format(
                        self.get_col_name(),
                        bindvalue,
                        self.get_rest_key_name()
                    )
                if len(str_where) != 0:
                    str_where = '(' + str_where + ')'
            else:
                for bindvalue in tmp_conf:

                    bindkey = "__{}__{}".format(self.get_col_name(), listno)
                    bindkeys.append(bindkey)
                    bindvalues.setdefault(bindkey, bindvalue)
                    listno = +1

                bindkey = "{}".format(",".join(map(str, bindkeys)))
                str_where = " `{col_name}` IN ( {bindkey} ) ".format(
                    col_name=self.get_col_name(),
                    bindkey=bindkey
                )

        result.setdefault("bindkey", bindkeys)
        result.setdefault("bindvalue", bindvalues)
        result.setdefault("where", str_where)

        return result
