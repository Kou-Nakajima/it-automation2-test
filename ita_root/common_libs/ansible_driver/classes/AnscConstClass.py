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

"""
  ansibleドライバーに必要な定数定義モジュール
"""


class AnscConst:
    """
      ansibleドライバーに必要な定数定義クラス
    """
    # ドライバ識別子
    DF_LEGACY_DRIVER_ID = "L"
    DF_LEGACY_ROLE_DRIVER_ID = "R"
    DF_PIONEER_DRIVER_ID = "P"

    # ユーザーホスト変数名の先頭文字
    # DF_HOST_VAR_HED                     = "VAR_"
    DF_HOST_VAR_HED = ""      # 2系からVAR_はなし

    # テンプレートファイル変数名の先頭文字
    DF_HOST_TPF_HED = "TPF_"
    # copyファイル変数名の先頭文字
    DF_HOST_CPF_HED = "CPF_"
    # グローバル変数名の先頭文字
    DF_HOST_GBL_HED = "GBL_"
    # テンプレートファイルからグローバル変数を取り出す場合の区分
    DF_HOST_TEMP_GBL_HED = "TEMP_GBL_"

    # Towerノードタイプ
    DF_EXECUTE_NODE = "execute_node"   # ISOLATED・実行ノード
    DF_CONTROL_NODE = "control_nide"   # ハイブリット・制御ノード

    DF_SCP_CONDUCTOR_ITA_PATH = "SCP_CONDUCTOR_ITA_PATH"
    DF_SCP_CONDUCTOR_TOWER_PATH = "SCP_CONDUCTOR_TOWER_PATH"
    DF_SCP_SYMPHONY_ITA_PATH = "SCP_SYMPHONY_ITA_PATH"
    DF_SCP_SYMPHONY_TOWER_PATH = "SCP_SYMPHONY_TOWER_PATH"
    DF_SCP_OUT_ITA_PATH = "SCP_OUT_ITA_PATH"
    DF_SCP_OUT_TOWER_PATH = "SCP_OUT_TOWER_PATH"
    DF_SCP_TMP_ITA_PATH = "SCP_TMP_ITA_PATH"
    DF_SCP_TMP_TOWER_PATH = "SCP_TMP_TOWER_PATH"
    DF_SCP_IN_PARAMATERS_ITA_PATH = "SCP_IN_PARAMATERS_ITA_PATH"
    DF_SCP_IN_PARAMATERS_TOWER_PATH = "SCP_IN_PARAMATERS_TOWER_PATH"
    DF_SCP_IN_PARAMATERS_FILE_ITA_PATH = "SCP_IN_PARAMATERS_FILE_ITA_PATH"
    DF_SCP_IN_PARAMATERS_FILE_TOWER_PATH = "SCP_IN_PARAMATERS_FILE_TOWER_PATH"
    DF_GITREPO_OUT_PATH = "GITREPO_OUT_PATH"
    DF_GITREPO_TMP_PATH = "GITREPO_TMP_PATH"
    DF_GITREPO_SYMPHONY_PATH = "GITREPO_SYMPHONY_PATH"
    DF_GITREPO_CONDUCTOR_PATH = "GITREPO_CONDUCTOR_PATH"

    # AnsibleTower処理区分
    DF_EXECUTION_FUNCTION = '1'
    DF_CHECKCONDITION_FUNCTION = '2'
    DF_DELETERESOURCE_FUNCTION = '3'
    DF_RESULTFILETRANSFER_FUNCTION = '4'

    # B_ANS_TWR_JOBTP_PROPERTY->PROPERTY_TYPE
    DF_JobTemplateKeyValueProperty = "1"
    DF_JobTemplateVerbosityProperty = "2"
    DF_JobTemplatebooleanTrueProperty = "3"
    DF_JobTemplateExtraVarsProperty = "4"

    # 変数定義場所 setVariableDefineLocationの種別
    DF_DEF_VARS = "DEFAULT_VARS"          # role　default変数定義
    DF_TEMP_VARS = "TEMPLART_VARS"        # テンプレート管理　変数定義
    DF_README_VARS = "ITAREADME_VARS"     # ITA_readme

    # 変数タイプ
    DF_VAR_TYPE_VAR = "VAR"
    DF_VAR_TYPE_GBL = "GBL"
    DF_VAR_TYPE_TPF = "TPF"

    # 具体値 SENSITIVE設定値
    DF_SENSITIVE_OFF = "0"    # False
    DF_SENSITIVE_ON = "1"     # True
    
    # 機器一覧 認証方式(LOGIN_AUTH_TYPE)
    DF_LOGIN_AUTH_TYPE_KEY = '1'         # 鍵認証(パスフレーズなし)
    DF_LOGIN_AUTH_TYPE_PW = '2'          # パスワード認証
    DF_LOGIN_AUTH_TYPE_KEY_EXCH = '3'    # 認証方式:鍵認証(鍵交換済み)
    DF_LOGIN_AUTH_TYPE_KEY_PP_USE = '4'  # 認証方式:鍵認証(パスフレーズあり)
    DF_LOGIN_AUTH_TYPE_PW_WINRM = '5'    # 認証方式:パスワード認証(winrm)

    # 正規表記でエスケープが必要な文字 $ ( ) * + - / ? ^ { | }
    # 親変数で許容する文字: xxx_[0-9a-zA-Z_]　  GBL/TPF
    VAR_parent_VarName = "/^(\s*)[0-9a-zA-Z_]*(\s*)$/"      # 通常の変数
    GBL_parent_VarName = "/^(\s*)GBL_[0-9a-zA-Z_]*(\s*)$/"  # グローバル変数
    TPF_parent_VarName = "/^(\s*)TPF_[0-9a-zA-Z_]*(\s*)$/"  # テンプレート変数
    
    # 実行エンジン
    DF_EXEC_MODE_ANSIBLE = '1'    # Ansibleで実行
    DF_EXEC_MODE_AAC = '2'        # ansible automation controllerで実行

    # 機器一覧 AACホスト一覧  認証方式(LOGIN_AUTH_TYPE)
    DF_LOGIN_AUTH_TYPE_KEY = '1'         # 鍵認証(パスフレーズなし)
    DF_LOGIN_AUTH_TYPE_PW = '2'          # パスワード認証
    DF_LOGIN_AUTH_TYPE_KEY_EXCH = '3'    # 認証方式:鍵認証(鍵交換済み)
    DF_LOGIN_AUTH_TYPE_KEY_PP_USE = '4'  # 認証方式:鍵認証(パスフレーズあり)
    DF_LOGIN_AUTH_TYPE_PW_WINRM = '5'    # 認証方式:パスワード認証(winrm)

    # 変数タイプ
    DF_VARS_ATTR_STD = '1'       # 一般変数
    DF_VARS_ATTR_LIST = '2'      # 複数具体値
    DF_VARS_ATTR_STRUCT = '3'    # 多段変数

    ############################################################
    # 変数定義の変数名定義判定配列
    # parant  :親変数名として利用可否
    #           True:利用可能
    #           False:利用不可
    # member  :メンバー変数名として利用可否
    #           True:利用可能
    #           False:利用不可
    # pattern:親変数名として許可する正規表記
    #   メンバー変数名定義の正規表記
    #   許容文字は、英数字と!#$%&()*+,-/;<=>?@^_`{|}~ "':\
    #   許容しない記号   . [ ] 合計3文字
    ############################################################
    DF_VarName_pattenAry = {}
    DF_VarName_pattenAry[DF_DEF_VARS] = []
    DF_VarName_pattenAry[DF_TEMP_VARS] = []
    DF_VarName_pattenAry[DF_README_VARS] = []
    # default変数定義ファイル変数定義用
    DF_VarName_pattenAry[DF_DEF_VARS].append({'parent': True, 'type': DF_VAR_TYPE_VAR, 'pattern': VAR_parent_VarName})
    DF_VarName_pattenAry[DF_DEF_VARS].append({'parent': False, 'type': DF_VAR_TYPE_GBL, 'pattern': GBL_parent_VarName})
    # テンプレート管理変数定義用
    DF_VarName_pattenAry[DF_TEMP_VARS].append({'parent': True, 'type': DF_VAR_TYPE_VAR, 'pattern': VAR_parent_VarName})
    DF_VarName_pattenAry[DF_TEMP_VARS].append({'parent': True, 'type': DF_VAR_TYPE_GBL, 'pattern': GBL_parent_VarName})
    # ITA-Readme変数定義用
    DF_VarName_pattenAry[DF_README_VARS].append({'parent': True, 'type': DF_VAR_TYPE_VAR, 'pattern': VAR_parent_VarName})
    DF_VarName_pattenAry[DF_README_VARS].append({'parent': False, 'type': DF_VAR_TYPE_GBL, 'pattern': GBL_parent_VarName})

    # Tower Project Path
    DF_TowerProjectPath = "/var/lib/awx/projects"
    # Tower Exastro専用 Project Path
    DF_TowerExastroProjectPath = "/var/lib/exastro"

    LC_RUN_MODE_STD = "0"      # 標準
    LC_RUN_MODE_VARFILE = "1"  # 変数定義ファイルの構造チェック
    
    # ステータス定義(DBの値と同期させること)
    NOT_YET = 1          # 未実行
    PREPARE = 2          # 準備中
    PROCESSING = 3       # 実行中
    PROCESS_DELAYED = 4  # 実行中(遅延)
    COMPLETE = 5         # 完了
    FAILURE = 6          # 完了(異常)
    EXCEPTION = 7        # 想定外エラー
    SCRAM = 8            # 緊急停止
    RESERVE = 9          # 未実行(予約中)
    RESERVE_CANCEL = 10  # 予約取消

    DRY_RUN = 2  # 実行モード(ドライラン=チェック)

    # WINRM接続ポート デフォルト値
    LC_WINRM_PORT = 5985

    TOWER_VER35 = 1        # Towerバージョン3.5(以下)
    TOWER_VER36 = 2        # Towerバージョン3.6(以上)
    
