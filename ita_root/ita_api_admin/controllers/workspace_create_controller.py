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
controller
workspace_create
"""
# import connexion
from flask import g
import os
import re
import json
import shutil

from common_libs.api import api_filter, check_request_body_key
from common_libs.common.exception import AppException
from common_libs.common.dbconnect import *  # noqa: F403
from common_libs.common.util import ky_encrypt


@api_filter
def workspace_create(organization_id, workspace_id, body=None):  # noqa: E501
    """workspace_create

    Workspaceを作成する # noqa: E501

    :param organization_id: organizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str
    :param body:
    :type body: dict | bytes

    :rtype: InlineResponse200
    """
    role_id = check_request_body_key(body, 'role_id')

    org_db = DBConnectOrg(organization_id)  # noqa: F405
    connect_info = org_db.get_wsdb_connect_info(workspace_id)
    if connect_info:
        return '', "ALREADY EXISTS"

    # make storage directory for workspace
    strage_path = os.environ.get('STORAGEPATH')
    workspace_dir = strage_path + "/".join([organization_id, workspace_id]) + "/"
    print(workspace_dir)
    if not os.path.isdir(workspace_dir):
        os.makedirs(workspace_dir)
    else:
        return '', "ALREADY EXISTS"

    dir_list = [
        ['driver'],
        ['driver', 'ansible'],
        ['driver', 'ansible', 'legacy'],
        ['driver', 'ansible', 'pioneer'],
        ['driver', 'ansible', 'legacy_role'],
        ['driver', 'ansible', 'git_repositories'],
        ['driver', 'conductor'],
        ['driver', 'terraform'],
        ['uploadfiles'],
    ]
    for dir in dir_list:
        abs_dir = workspace_dir + "/".join(dir)
        if not os.path.isdir(abs_dir):
            os.makedirs(abs_dir)

    # set initial material
    with open('files/config.json', 'r') as material_conf_json:
        material_conf = json.load(material_conf_json)
        for menu_id, file_info_list in material_conf.items():
            for file_info in file_info_list:
                for file, copy_cfg in file_info.items():
                    org_file = os.environ.get('PYTHONPATH') + "/".join(["files", menu_id, file])
                    old_file_path = workspace_dir + "uploadfiles/" + menu_id + copy_cfg[0]
                    file_path = workspace_dir + "uploadfiles/" + menu_id + copy_cfg[1]

                    if not os.path.isdir(old_file_path):
                        os.makedirs(old_file_path)

                    shutil.copy(org_file, old_file_path + file)
                    os.symlink(old_file_path + file, file_path + file)

    # register workspace-db connect infomation
    user_name, user_password = org_db.userinfo_generate("WS")
    ws_db_name = user_name
    connect_info = org_db.get_connect_info()
    try:
        data = {
            'WORKSPACE_ID': workspace_id,
            'DB_HOST': connect_info['DB_HOST'],
            'DB_PORT': int(connect_info['DB_PORT']),
            'DB_USER': user_name,
            'DB_PASSWORD': ky_encrypt(user_password),
            'DB_DATADBASE': ws_db_name,
            'DISUSE_FLAG': 0,
            'LAST_UPDATE_USER': g.get('USER_ID')
        }
        org_db.db_transaction_start()
        org_db.table_insert("T_COMN_WORKSPACE_DB_INFO", data, "PRIMARY_KEY")

        org_db.db_commit()
    except Exception as e:
        org_db.db_rollback()
        raise Exception(e)

    org_root_db = DBConnectOrgRoot(organization_id)  # noqa: F405
    # create workspace-databse
    org_root_db.database_create(ws_db_name)
    # create workspace-user and grant user privileges
    org_root_db.user_create(user_name, user_password, ws_db_name)
    # print(user_name, user_password)
    org_root_db.db_disconnect()

    # connect workspace-db
    ws_db = DBConnectWs(workspace_id, organization_id)  # noqa: F405
    # create table of workspace-db
    ws_db.sqlfile_execute("sql/workspace.sql")

    # insert initial data of workspace-db
    with open("sql/workspace_master.sql", "r") as f:
        sql_list = f.read().split(";\n")
        for sql in sql_list:
            sql = sql.replace('__ROLE_ID__', role_id)
            if re.fullmatch(r'[\s\n\r]*', sql) is None:
                ws_db.sql_execute(sql)

    return '',


@api_filter
def workspace_delete(organization_id, workspace_id):  # noqa: E501
    """workspace_delete

    Workspaceを削除する # noqa: E501

    :param organization_id: organizationID
    :type organization_id: str
    :param workspace_id: WorkspaceID
    :type workspace_id: str

    :rtype: InlineResponse200
    """
    # get organization_id
    g.ORGANIZATION_ID = organization_id

    org_db = DBConnectOrg(organization_id)  # noqa: F405
    connect_info = org_db.get_wsdb_connect_info(workspace_id)
    if connect_info is False:
        return '', "ALREADY DELETED"

    strage_path = os.environ.get('STORAGEPATH')
    workspace_dir = strage_path + "/".join([organization_id, workspace_id]) + "/"
    print(workspace_dir)
    if os.path.isdir(workspace_dir):
        shutil.rmtree(workspace_dir)
    else:
        return '', "ALREADY DELETED"

    # drop ws-db and ws-db-user
    org_root_db = DBConnectOrgRoot(organization_id)  # noqa: F405
    org_root_db.database_drop(connect_info['DB_DATADBASE'])
    org_root_db.user_drop(connect_info['DB_USER'])
    org_root_db.db_disconnect()

    # disuse ws-db connect infomation
    data = {
        'PRIMARY_KEY': connect_info['PRIMARY_KEY'],
        'DISUSE_FLAG': 1
    }
    try:
        org_db.db_transaction_start()
        org_db.table_update("T_COMN_WORKSPACE_DB_INFO", data, "PRIMARY_KEY")
        org_db.db_commit()
    except AppException:
        org_db.db_rollback()

    return '',
