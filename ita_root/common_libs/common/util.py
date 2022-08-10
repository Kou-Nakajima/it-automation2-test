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
共通関数 module
"""
import secrets
import string
import base64
import codecs
from pathlib import Path
import datetime
import re
import os
from flask import g


def ky_encrypt(lcstr):
    """
    Encode a string

    Arguments:
        lcstr: Encoding target value
    Returns:
        Encoded string
    """
    # BASE64でエンコード
    tmp_str = base64.b64encode(lcstr.encode())
    # rot13でエンコード
    return codecs.encode(tmp_str.decode(), "rot_13")


def ky_decrypt(lcstr):
    """
    Decode a string

    Arguments:
        lcstr: Decoding target value
    Returns:
        Decoded string
    """
    # rot13でデコード
    tmp_str = codecs.decode(lcstr, "rot_13")
    # base64でデコード
    return base64.b64decode(tmp_str.encode()).decode()


def ky_file_encrypt(src_file, dest_file):
    """
    Encode a file

    Arguments:
        src_file: Encoding target file
        dest_file: Encoded file
    Returns:
        is success:(bool)
    """
    try:
        # ファイルオープン
        fsrc = open(src_file)
        
        # ファイル読み込み
        lcstr = Path(src_file).read_text(encoding="utf-8")
        
        # エンコード関数呼び出し
        enc_data = ky_encrypt(lcstr)
        
        # ファイル書き込み
        Path(dest_file).write_text(enc_data, encoding="utf-8")
    except Exception:
        return False
    finally:
        # ファイルクローズ
        fsrc.close()
    
    return True


def ky_file_decrypt(src_file, dest_file):
    """
    Decode a file

    Arguments:
        src_file: Decoding target file
        dest_file: Decoded file
    Returns:
        is success:(bool)
    """
    try:
        # ファイルオープン
        fsrc = open(src_file)
        
        # ファイル読み込み
        lcstr = Path(src_file).read_text(encoding="utf-8")
        
        # デコード関数呼び出し
        enc_data = ky_decrypt(lcstr)
        
        # ファイル書き込み
        Path(dest_file).write_text(enc_data, encoding="utf-8")
    except Exception:
        return False
    finally:
        # ファイルクローズ
        fsrc.close()
    
    return True


def generate_secrets(length=16, punctuation=''):
    """
    generate secrets

    Arguments:
        length: secrets length
        punctuation: symbol used
    Returns:
        (str)secrets value
    """
    # string.ascii_letters - alfabet lower and upper
    # string.digits - number
    # string.punctuation - symbol  !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
    pass_chars = string.ascii_letters + string.digits + punctuation
    secrets_val = ''.join(secrets.choice(pass_chars) for x in range(length))

    return secrets_val


def get_timestamp(is_utc=True):
    """
    get timestamp

    Returns:
        2022-07-01 07:36:24.551751
    """
    return datetime.datetime.now()


def get_iso_datetime(is_utc=True):
    """
    get timestamp for api response format

    Args:
        is_utc (bool):

    Returns:
        2022-08-02T10:26:18.809Z
    """
    timestamp = datetime.datetime.now()
    if timestamp.strftime('%z') == "":
        return timestamp.isoformat(timespec='milliseconds') + "Z"
    else:
        return timestamp.isoformat(timespec='milliseconds')


def arrange_stacktrace_format(t):
    """
    stacktrace

    Arguments:
        t: return traceback.format_exc()
    Returns:
        (str)
    """
    retStr = ""

    exception_block_arr = t.split('Traceback (most recent call last):\n')
    # exception_block = exception_block_arr[1]  # most deep exception called
    exception_block_index = 0
    for exception_block in exception_block_arr:
        exception_block = re.sub(r'\n\nDuring handling of the above exception, another exception occurred:\n\n', '', exception_block.strip())
        if exception_block[0:4] != 'File':
            continue

        retStr = retStr + "\n{} : exception block".format(exception_block_index)
        exception_block_index = exception_block_index + 1

        trace_block_arr = re.split('File', exception_block)
        for trace_block in trace_block_arr:
            row_arr = re.split('\n', str(trace_block.strip()))
            row_index = 0
            row_str = ""
            length = len(row_arr) - 1
            if length == 0:
                continue

            for row in row_arr:

                if row_index == 0:
                    row_str = "\n -> " + row
                elif row_index == 1:
                    row_str = row_str + ", " + row.strip()
                    retStr = retStr + row_str
                elif row_index == 2:
                    retStr = retStr + "\n " + row.strip()

                row_index = row_index + 1

    return retStr


def file_encode(file_path):
    """
    Encode a file to base64

    Arguments:
        file_path: Encoding target filepath
    Returns:
        Encoded string
    """
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return False


def get_upload_file_path(workspace_id, menu_id, uuid, column_name_rest, file_name, uuid_jnl):
    """
    Get filepath

    Arguments:
        workspace_id: workspace_id
        menu_id: menu_id
        uuid: uuid
        column_name_rest: column_name_rest
        file_name: Target file name
        uuid_jnl: uuid_jnl
    Returns:
        filepath
    """
    organization_id = g.get("ORGANIZATION_ID")
    file_path = "/storage/{}/{}/uploadfiles/{}/{}/{}/{}".format(organization_id, workspace_id, menu_id, column_name_rest, uuid, file_name)
    old_file_path = ""
    if uuid_jnl is not None:
        if len(uuid_jnl) > 0:
            old_file_path = "/storage/{}/{}/uploadfiles/{}/{}/{}/old/{}/{}".format(organization_id, workspace_id, menu_id, column_name_rest, uuid, uuid_jnl, file_name)  # noqa: E501

    return {"file_path": file_path, "old_file_path": old_file_path}


def get_upload_file_path_specify(workspace_id, place, uuid, file_name, uuid_jnl):
    """
    Get filepath

    Arguments:
        workspace_id: workspace_id
        place: Target file place
        uuid: uuid
        file_name: Target file name
        uuid_jnl: uuid_jnl
    Returns:
        filepath
    """
    organization_id = g.get("ORGANIZATION_ID")
    file_path = "/storage/{}/{}{}/{}/{}".format(organization_id, workspace_id, place, uuid, file_name)
    old_file_path = ""
    if uuid_jnl is not None:
        if len(uuid_jnl) > 0:
            old_file_path = "/storage/{}/{}{}/{}/old/{}/{}".format(organization_id, workspace_id, place, uuid, uuid_jnl, file_name)  # noqa: E501

    return {"file_path": file_path, "old_file_path": old_file_path}


def upload_file(file_path, text):
    """
    Upload a file

    Arguments:
        file_path: Target filepath
        text: file text
    Returns:
        is success:(bool)
    """
    path = os.path.dirname(file_path)

    if type(text) is bytes:
        text = base64.b64decode(text.encode()).decode()
    
    if isinstance(text, str):
        text = base64.b64decode(text.encode())

    if not os.path.isdir(path):
        os.makedirs(path)

    try:
        with open(file_path, "bx") as f:
            f.write(text)
    except Exception:
        return False

    return True


def encrypt_upload_file(file_path, text):
    """
    Encode and upload file

    Arguments:
        file_path: Target filepath
        text: file text
    Returns:
        is success:(bool)
    """
    text = ky_encrypt(text)
    path = os.path.dirname(file_path)

    if not os.path.isdir(path):
        os.makedirs(path)

    if isinstance(text, str):
        text = base64.b64decode(text.encode())

    try:
        with open(file_path, "bx") as f:
            f.write(text)
    except Exception:
        return False

    return True


if __name__ == '__main__':
    # print(generate_secrets())
    pass
