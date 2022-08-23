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

from flask import g
from common_libs.common.dbconnect import DBConnectWs
import re
import json


class ConductorCommonLibs():
    config_data = {}
    conductor_data = {}
    node_datas = {}
    edge_datas = {}

    _node_id_list = []

    _node_type_list = []

    _node_connect_point_condition = {
        'start': {
            'in': [],
            'out': ['movement', 'call', 'parallel-branch']
        },
        'end': {
            'in': ['movement', 'call', 'conditional-branch', 'merge', 'pause', 'status-file-branch'],
            'out': []
        },
        'call': {
            'in': ['start', 'movement', 'call', 'parallel-branch', 'conditional-branch', 'merge', 'pause', 'status-file-branch'],
            'out': ['end', 'movement', 'call', 'parallel-branch', 'conditional-branch', 'merge', 'pause', 'status-file-branch']
        },
        'movement': {
            'in': ['start', 'movement', 'call', 'parallel-branch', 'conditional-branch', 'merge', 'pause', 'status-file-branch'],
            'out': ['end', 'movement', 'call', 'parallel-branch', 'conditional-branch', 'merge', 'pause', 'status-file-branch']
        },
        'parallel-branch': {
            'in': ['start', 'movement', 'call', 'conditional-branch', 'merge', 'pause', 'status-file-branch'],
            'out': ['movement', 'call']
        },
        'conditional-branch': {
            'in': ['movement', 'call'],
            'out': ['end', 'movement', 'call', 'parallel-branch', 'pause']
        },
        'merge': {
            'in': ['movement', 'call', 'pause'],
            'out': ['end', 'movement', 'call', 'parallel-branch', 'pause']
        },
        'pause': {
            'in': ['movement', 'call', 'parallel-branch', 'merge', 'status-file-branch'],
            'out': ['end', 'movement', 'call', 'parallel-branch', 'pause']
        },
        'status-file-branch': {
            'in': ['movement', 'call'],
            'out': ['end', 'movement', 'call', 'parallel-branch', 'pause']
        },
    }

    _node_end_type_list = []

    _terminal_type_list = ['in', 'out']

    _node_status_list = []

    _orchestra_id_list = []

    _node_call_datas = {}

    __db = None

    def __init__(self, wsdb_istc=None):
        if not wsdb_istc:
            wsdb_istc = DBConnectWs(g.get('WORKSPACE_ID'))  # noqa: F405
        self.__db = wsdb_istc

        # set master list
        data_list = wsdb_istc.table_select('T_COMN_CONDUCTOR_NODE', 'WHERE `DISUSE_FLAG`=0')
        for data in data_list:
            self._node_type_list.append(data['NODE_TYPE_ID'])
        # print(self._node_type_list)

        # 正常終了、異常終了、警告終了のみ許容
        data_list = wsdb_istc.table_select('T_COMN_CONDUCTOR_STATUS', 'WHERE `DISUSE_FLAG`=0 and `STATUS_NAME_JA` like "%終了"')
        for data in data_list:
            self._node_end_type_list.append(data['STATUS_ID'])
        # print(self._node_end_type_list)

        data_list = wsdb_istc.table_select('T_COMN_CONDUCTOR_NODE_STATUS', 'WHERE `DISUSE_FLAG`=0')
        for data in data_list:
            self._node_status_list.append(data['STATUS_ID'])
        # print(self._node_status_list)

        data_list = wsdb_istc.table_select('T_COMN_ORCHESTRA', 'WHERE `DISUSE_FLAG`=0')
        for data in data_list:
            self._orchestra_id_list.append(data['ORCHESTRA_ID'])
        # print(self._orchestra_id_list)

    def chk_format_all(self, c_all_data):
        """
        check all conductor infomation

        Arguments:
            c_data: conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err_code xxx-xxxxx
            - err msg args (list)
        """
        err_code = 'xxx-xxxxxx'

        # check first block
        res_chk = self.chk_format(c_all_data)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        # check config block
        res_chk = self.chk_config(self.config_data)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        # check conductor block
        res_chk = self.chk_conductor(self.conductor_data)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        # check edge block
        res_chk = self.chk_edge(self.edge_datas)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        # check node block
        res_chk = self.chk_node(self.node_datas)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        # check node detail
        res_chk = self.chk_node_detail(self.node_datas)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        # check node call loop
        res_chk = self.chk_call_loop(self.conductor_data['id'], self._node_call_datas)
        if res_chk[0] is False:
            return False, err_code, res_chk[1]

        return True,

    def chk_format(self, c_all_data):
        """
        check format

        Arguments:
            c_all_data: conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        err_msg_args = []

        # check config
        if 'config' in c_all_data:
            if not c_all_data['config']:
                err_msg_args.append('config')
            self.config_data = c_all_data['config']
            del c_all_data['config']
        else:
            err_msg_args.append('config')

        # check conductor
        if 'conductor' in c_all_data:
            if not c_all_data['conductor']:
                err_msg_args.append('conductor')
            self.conductor_data = c_all_data['conductor']
            del c_all_data['conductor']
        else:
            err_msg_args.append('conductor')

        # check node and edge and extra
        is_exist_node = False
        is_exist_edge = False
        is_exist_extra = False
        for key, value in c_all_data.items():
            if re.fullmatch(r'node-\d{1,}', key):
                self.node_datas[key] = value
                is_exist_node = True
            elif re.fullmatch(r'line-\d{1,}', key):
                self.edge_datas[key] = value
                is_exist_edge = True
            else:
                is_exist_extra = True

        if is_exist_node is False:
            err_msg_args.append('node')
        if is_exist_edge is False:
            err_msg_args.append('edge')
        if is_exist_extra is True:
            err_msg_args.append('extra block is existed')

        if len(err_msg_args) != 0:
            return False, [','.join(err_msg_args)]
        else:
            return True,

    def chk_config(self, c_data):
        """
        check config block

        Arguments:
            c_data: config_data in conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        err_msg_args = []

        if 'nodeNumber' not in c_data:
            err_msg_args.append('config.nodeNumber')
        else:
            if type(c_data['nodeNumber']) is not int:
                err_msg_args.append('config.nodeNumber')

        if 'terminalNumber' not in c_data:
            err_msg_args.append('config.terminalNumber')
        else:
            if type(c_data['terminalNumber']) is not int:
                err_msg_args.append('config.terminalNumber')

        if 'edgeNumber' not in c_data:
            err_msg_args.append('config.edgeNumber')
        else:
            if type(c_data['edgeNumber']) is not int:
                err_msg_args.append('config.edgeNumber')

        if len(err_msg_args) != 0:
            return False, [','.join(err_msg_args)]
        else:
            return True,

    def chk_conductor(self, c_data):
        """
        check conductor block

        Arguments:
            c_data: conductor_data in conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        err_msg_args = []

        if 'id' not in c_data:
            err_msg_args.append('conductor.id')
        elif c_data['id']:
            data_list = self.__db.table_select('T_COMN_CONDUCTOR_CLASS', 'WHERE `DISUSE_FLAG`=0 AND `CONDUCTOR_CLASS_ID`=%s', [c_data['id']])  # noqa E501
            if len(data_list) == 0:
                err_msg_args.append('conductor.id not exists')

        if 'conductor_name' not in c_data:
            err_msg_args.append('conductor.conductor_name')

        if 'note' not in c_data:
            err_msg_args.append('conductor.note')

        if 'last_update_date_time' not in c_data:
            err_msg_args.append('conductor.last_update_date_time')

        if len(err_msg_args) != 0:
            return False, [','.join(err_msg_args)]
        else:
            return True,

    def chk_node(self, node_datas):
        """
        check node block

        Arguments:
            node_datas: node_datas in conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        err_msg_args = []

        chk_start_node = []
        for key, block_1 in node_datas.items():
            block_err_msg_args = []

            if 'id' not in block_1 or not re.fullmatch(r'node-\d{1,}', block_1['id']):
                block_err_msg_args.append('id')

            if 'type' not in block_1 or block_1['type'] not in self._node_type_list:
                block_err_msg_args.append('type')

            if 'terminal' not in block_1 or not block_1['terminal']:
                block_err_msg_args.append('terminal')
            else:
                res_chk_terminal_block = self.chk_terminal_block(block_1['terminal'])
                if res_chk_terminal_block[0] is False:
                    block_err_msg_args.append(res_chk_terminal_block[1])

            if 'x' not in block_1 or type(block_1['x']) is not int:
                block_err_msg_args.append('x')

            if 'y' not in block_1 or type(block_1['y']) is not int:
                block_err_msg_args.append('y')

            if 'w' not in block_1 or type(block_1['w']) is not int:
                block_err_msg_args.append('w')

            if 'h' not in block_1 or type(block_1['h']) is not int:
                block_err_msg_args.append('h')

            if 'note' in block_1 and block_1['note']:
                if len(block_1['note']) > 4000:
                    block_err_msg_args.append('note is too long')

            if len(block_err_msg_args) != 0:
                err_msg_args.append('{}({})'.format(key, ','.join(block_err_msg_args)))
            else:
                # make node_id_list
                self._node_id_list.append(block_1['id'])
                # check type=start
                if block_1['type'] == 'start':
                    chk_start_node.append(block_1['id'])
                # extract type=call
                elif block_1['type'] == 'call':
                    self._node_call_datas[key] = block_1

        if len(err_msg_args) != 0:
            return False, ['\n'.join(err_msg_args)]
        else:
            if len(chk_start_node) != 1:
                return False, ['node[type=start] is duplicate']

            return True,

    def chk_terminal_block(self, terminal_blcok):
        """
        check node terminal block

        Arguments:
            node_type: node type
            terminal_blcok: terminal dict in node
        Returns:
            (tuple)
            - retBool (bool)
            - err msg (str)
        """
        err_msg_args = []

        for terminalname, terminalinfo in terminal_blcok.items():
            block_err_msg_args = []

            if 'id' not in terminalinfo or not re.fullmatch(r'terminal-\d{1,}', terminalinfo['id']):
                block_err_msg_args.append('terminal.{}.id'.format(terminalname))

            if 'type' not in terminalinfo or terminalinfo['type'] not in self._terminal_type_list:
                block_err_msg_args.append('terminal.{}.type'.format(terminalname))

            if 'targetNode' not in terminalinfo or not terminalinfo['targetNode']:
                block_err_msg_args.append('terminal.{}.targetNode'.format(terminalname))

            if 'edge' not in terminalinfo or not terminalinfo['edge']:
                block_err_msg_args.append('terminal.{}.edge'.format(terminalname))

            if 'x' not in terminalinfo or type(terminalinfo['x']) is not int:
                block_err_msg_args.append('terminal.{}.x'.format(terminalname))

            if 'y' not in terminalinfo or type(terminalinfo['y']) is not int:
                block_err_msg_args.append('terminal.{}.y'.format(terminalname))

            if len(block_err_msg_args) != 0:
                err_msg_args.append(','.join(block_err_msg_args))

        if len(err_msg_args) != 0:
            return False, ','.join(err_msg_args)
        else:
            return True,

    def chk_node_detail(self, node_datas):
        """
        check node detail

        Arguments:
            node_datas: node_datas in conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        err_msg_args = []
        for key, block_1 in node_datas.items():
            node_type = block_1['type']

            if node_type == 'end':
                if 'end_type' not in block_1 or block_1['end_type'] not in self._node_end_type_list:
                    err_msg_args.append('{}(end_type)'.format(key))
                    continue
            elif node_type == 'movement':
                res_chk = self.chk_type_movement(block_1)
                if res_chk[0] is False:
                    err_msg_args.append('{}({})'.format(key, res_chk[1]))
                    continue
            elif node_type == 'call':
                res_chk = self.chk_type_call(block_1)
                if res_chk[0] is False:
                    err_msg_args.append('{}({})'.format(key, res_chk[1]))
                    continue

            # check node conditions
            res_chk = self.chk_node_conditions(node_type, block_1['terminal'])
            if res_chk[0] is False:
                err_msg_args.append('{}({})'.format(key, res_chk[1]))
                continue

        if len(err_msg_args) != 0:
            return False, ['\n'.join(err_msg_args)]
        else:
            return True,

    def chk_type_movement(self, node_blcok):
        """
        check node type=movement

        Arguments:
            node_blcok: node data
        Returns:
            (tuple)
            - retBool (bool)
            - err msg (str)
        """
        err_msg_args = []

        if 'movement_id' not in node_blcok or not node_blcok['movement_id']:
            err_msg_args.append('movement_id')
        else:
            data_list = self.__db.table_select('T_COMN_MOVEMENT', 'WHERE `DISUSE_FLAG`=0 AND `MOVEMENT_ID`=%s', [node_blcok['movement_id']])
            if len(data_list) == 0:
                err_msg_args.append('movement_id is not available')

        if 'movement_name' not in node_blcok:
            err_msg_args.append('movement_name')

        if 'skip_flag' not in node_blcok:
            err_msg_args.append('skip_flag')

        if 'operation_id' not in node_blcok:
            err_msg_args.append('operation_id')
        elif node_blcok['operation_id']:
            data_list = self.__db.table_select('T_COMN_OPERATION', 'WHERE `DISUSE_FLAG`=0 AND `OPERATION_ID`=%s', [node_blcok['operation_id']])
            if len(data_list) == 0:
                err_msg_args.append('operation_id is not available')

        if 'operation_name' not in node_blcok:
            err_msg_args.append('operation_name')

        if 'orchestra_id' not in node_blcok or node_blcok['orchestra_id'] not in self._orchestra_id_list:
            err_msg_args.append('orchestra_id')

        if len(err_msg_args) != 0:
            return False, ','.join(err_msg_args)
        else:
            return True,

    def chk_type_call(self, node_blcok):
        """
        check node type=call

        Arguments:
            node_blcok: node data
        Returns:
            (tuple)
            - retBool (bool)
            - err msg (str)
        """
        err_msg_args = []

        if 'call_conductor_id' not in node_blcok or not node_blcok['call_conductor_id']:
            err_msg_args.append('call_conductor_id')
        else:
            data_list = self.__db.table_select('T_COMN_CONDUCTOR_CLASS', 'WHERE `DISUSE_FLAG`=0 AND `CONDUCTOR_CLASS_ID`=%s', [node_blcok['call_conductor_id']])  # noqa E501
            if len(data_list) == 0:
                err_msg_args.append('call_conductor_id is not available')

        if 'call_conductor_name' not in node_blcok:
            err_msg_args.append('call_conductor_name')

        if 'skip_flag' not in node_blcok:
            err_msg_args.append('skip_flag')

        if 'operation_id' not in node_blcok:
            err_msg_args.append('operation_id')
        elif node_blcok['operation_id']:
            data_list = self.__db.table_select('T_COMN_OPERATION', 'WHERE `DISUSE_FLAG`=0 AND `OPERATION_ID`=%s', [node_blcok['operation_id']])
            if len(data_list) == 0:
                err_msg_args.append('operation_id is not available')

        if 'operation_name' not in node_blcok:
            err_msg_args.append('operation_name')

        if len(err_msg_args) != 0:
            return False, ','.join(err_msg_args)
        else:
            return True,

    def chk_node_conditions(self, node_type, terminal_blcok):
        """
        check node conditions

        Arguments:
            node_type: node type
            terminal_blcok: terminal dict in node
        Returns:
            (tuple)
            - retBool (bool)
            - err msg (str)
        """
        err_msg_args = []

        if node_type in self._node_connect_point_condition:
            connect_point_condition = self._node_connect_point_condition[node_type]
        else:
            connect_point_condition = []

        for terminalname, terminalinfo in terminal_blcok.items():
            # check whether node is connected
            if terminalinfo['targetNode'] not in self._node_id_list:
                err_msg_args.append('terminal.{}.targetNode not connected'.format(terminalname))
                continue

            # check node connect point
            terminal_type = terminalinfo['type']
            target_node = terminalinfo['targetNode']
            target_node_type = self.node_datas[target_node]['type']
            if target_node_type not in connect_point_condition[terminal_type]:
                err_msg_args.append('terminal.{}.target_node-connect-point is invalid'.format(terminalname))
                continue

        if len(err_msg_args) != 0:
            return False, ','.join(err_msg_args)

        # check 'conditional-branch' status id
        if node_type == 'conditional-branch':
            res_chk = self.chk_type_condtional_branch(terminal_blcok)

            if res_chk[0] is False:
                return False, res_chk[1]

        # check 'status-file-branch' condition
        elif node_type == 'status-file-branch':
            res_chk = self.chk_type_status_file_branch(terminal_blcok)

            if res_chk[0] is False:
                return False, res_chk[1]

        return True,

    def chk_type_condtional_branch(self, terminal_blcok):
        """
        check node type=condtional-branch

        Arguments:
            terminal_blcok: terminal dict in node
        Returns:
            (tuple)
            - retBool (bool)
            - err msg (str)
        """
        err_msg_args = []

        for terminalname, terminalinfo in terminal_blcok.items():
            if terminalinfo['type'] == 'out':
                if 'condition' not in terminalinfo or not terminalinfo['condition']:
                    err_msg_args.append('terminal.{}.condition'.format(terminalname))
                    continue

                is_conditon_invalid = True
                for condition in terminalinfo['condition']:
                    if condition not in self._node_status_list:
                        is_conditon_invalid = False
                        err_msg_args.append('terminal.{}.condition'.format(terminalname))
                        continue
                if is_conditon_invalid is False:
                    continue

        if len(err_msg_args) != 0:
            return False, ','.join(err_msg_args)
        else:
            return True,

    def chk_type_status_file_branch(self, terminal_blcok):
        """
        check node type=status-file-branch

        Arguments:
            terminal_blcok: terminal dict in node
        Returns:
            (tuple)
            - retBool (bool)
            - err msg (str)
        """
        err_msg_args = []
        condition_val_list = []
        condition_caseno_list = []

        for terminalname, terminalinfo in terminal_blcok.items():
            if terminalinfo['type'] == 'out':
                if 'case' not in terminalinfo or not terminalinfo['case']:
                    err_msg_args.append('terminal.{}.case'.format(terminalname))
                    continue
                elif terminalinfo['case'] == 'else':
                    continue

                if 'condition' not in terminalinfo or not terminalinfo['condition'] or not terminalinfo['condition'][0]:
                    err_msg_args.append('terminal.{}.condition'.format(terminalname))
                    continue

                is_conditon_invalid = True
                for condition in terminalinfo['condition']:
                    if condition not in self._node_status_list:
                        is_conditon_invalid = False
                        err_msg_args.append('terminal.{}.condition'.format(terminalname))
                        continue
                if is_conditon_invalid is False:
                    continue

                condtion_caseno = terminalinfo['case']
                condition_val = terminalinfo['condition'][0]

                if condtion_caseno not in condition_caseno_list:
                    condition_caseno_list.append(condtion_caseno)
                else:
                    err_msg_args.append('terminal.{}.case is invalid'.format(terminalname))
                    continue

                if condition_val not in condition_val_list:
                    condition_val_list.append(condition_val)
                else:
                    err_msg_args.append('terminal.{}.condition is duplicate'.format(terminalname))
                    continue

        if len(err_msg_args) != 0:
            return False, ','.join(err_msg_args)
        else:
            return True,

    def chk_edge(self, c_data):
        """
        check edge block

        Arguments:
            c_data: edge_datas in conductor infomation(dict)
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        err_msg_args = []

        for key, block_1 in c_data.items():
            block_err_msg_args = []

            if 'id' not in block_1:
                block_err_msg_args.append('id')
            else:
                val = block_1['id']
                if not re.fullmatch(r'line-\d{1,}', val):
                    block_err_msg_args.append('id')

            if 'type' not in block_1:
                block_err_msg_args.append('type')
            else:
                val = block_1['type']
                ###  暫定追加
                if val not in ['edge', 'egde']:
                    block_err_msg_args.append('type')

            if 'inNode' not in block_1:
                block_err_msg_args.append('inNode')
            else:
                val = block_1['inNode']
                if not re.fullmatch(r'node-\d{1,}', val):
                    block_err_msg_args.append('inNode')

            if 'inTerminal' not in block_1:
                block_err_msg_args.append('inTerminal')
            else:
                val = block_1['inTerminal']
                if not re.fullmatch(r'terminal-\d{1,}', val):
                    block_err_msg_args.append('inTerminal')

            if 'outNode' not in block_1:
                block_err_msg_args.append('outNode')
            else:
                val = block_1['outNode']
                if not re.fullmatch(r'node-\d{1,}', val):
                    block_err_msg_args.append('outNode')

            if 'outTerminal' not in block_1:
                block_err_msg_args.append('outTerminal')
            else:
                val = block_1['outTerminal']
                if not re.fullmatch(r'terminal-\d{1,}', val):
                    block_err_msg_args.append('outTerminal')

            if len(block_err_msg_args) != 0:
                err_msg_args.append('{}({})'.format(key, ','.join(block_err_msg_args)))

        if len(err_msg_args) != 0:
            return False, ['\n'.join(err_msg_args)]
        else:
            return True,

    def chk_call_loop(self, chk_call_conductor_id, node_call_datas):
        """
        check whether node type=call is loop recursively

        Arguments:
            chk_call_conductor_id: my conductor id
            node_call_datas: node datas type=call
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        # dont check when you want to insert
        if not chk_call_conductor_id:
            return True,

        err_msg_args = []

        for key, block_1 in node_call_datas.items():
            res_chk = self._chk_call_loop_recursive(block_1['call_conductor_id'], chk_call_conductor_id)
            if res_chk[0] is False:
                err_msg_args.append('{}.{}'.format(key, res_chk[1]))

        if len(err_msg_args) != 0:
            return False, ['\n'.join(err_msg_args)]
        else:
            return True,

    def _chk_call_loop_recursive(self, call_conductor_id, chk_call_conductor_id):
        """
        check whether node type=call is loop

        Arguments:
            call_conductor_id: conductor id for target data
            chk_call_conductor_id: my conductor id
        Returns:
            (tuple)
            - retBool (bool)
            - err msg args (list)
        """
        data_list = self.__db.table_select('T_COMN_CONDUCTOR_CLASS', 'WHERE `DISUSE_FLAG`=0 AND `CONDUCTOR_CLASS_ID`=%s', [call_conductor_id])
        if len(data_list) == 0:
            return False, 'call_conductor_id={} is not available'.format(call_conductor_id)

        chk_c_data = json.loads(data_list[0]['SETTING'])
        chk_node_datas = self.extract_node(chk_c_data)
        chk_node_call_datas = self.extract_node_type(chk_node_datas, 'call')

        for key, block_1 in chk_node_call_datas.items():
            if block_1['call_conductor_id'] == chk_call_conductor_id:
                return False, 'call_conductor_id={} is loop'.format(chk_call_conductor_id)
            else:
                return self._chk_call_loop_recursive(block_1['call_conductor_id'], chk_call_conductor_id)

        return True,

    def extract_node_type(self, node_datas, node_type):
        """
        extract node type={node_type} from node datas

        Arguments:
            node_datas: node_datas in conductor infomation(dict)
        Returns:
            node_datas
        """
        res = {}

        for key, block_1 in node_datas.items():
            if block_1['type'] == node_type:
                res[key] = block_1

        return res

    def extract_node(self, c_data):
        """
        extract node datas

        Arguments:
            c_data: conductor infomation(dict)
        Returns:
            node_datas
        """
        res = {}

        for key, value in c_data.items():
            if re.fullmatch(r'node-\d{1,}', key):
                res[key] = value

        return res

    def override_node_idlink(self, c_all_data=None):
        """
        update conductor infomation(dict)

        Arguments:
            c_data: conductor infomation(dict)
        Returns:
        Returns:
            (tuple)
            - retBool (bool)
            - err_code xxx-xxxxx
            # - err msg args (list)
        """
        retCode = 'xxx-xxxxx'

        if c_all_data:
            res_check = self.chk_format_all(c_all_data)
            if res_check[0] is False:
                return res_check

        try:
            # conductor name
            if self.conductor_data['id']:
                data_list = self.__db.table_select('T_COMN_CONDUCTOR_CLASS', 'WHERE `DISUSE_FLAG`=0 AND `CONDUCTOR_CLASS_ID`=%s', [self.conductor_data['id']])  # noqa E501
                self.conductor_data['conductor_name'] = data_list[0]['CONDUCTOR_NAME']

            for key, block_1 in self.node_datas.items():
                node_type = block_1['type']

                if node_type == 'movement':
                    # movement_name
                    data_list = self.__db.table_select('T_COMN_MOVEMENT', 'WHERE `DISUSE_FLAG`=0 AND `MOVEMENT_ID`=%s', [block_1['movement_id']])
                    block_1['movement_name'] = data_list[0]['MOVEMENT_NAME']
                    # operation_name
                    if block_1['operation_id']:
                        data_list = self.__db.table_select('T_COMN_OPERATION', 'WHERE `DISUSE_FLAG`=0 AND `OPERATION_ID`=%s', [block_1['operation_id']])  # noqa E501
                        block_1['operation_name'] = data_list[0]['OPERATION_NAME']
                elif node_type == 'call':
                    # call_conductor_name
                    data_list = self.__db.table_select('T_COMN_CONDUCTOR_CLASS', 'WHERE `DISUSE_FLAG`=0 AND `CONDUCTOR_CLASS_ID`=%s', [block_1['call_conductor_id']])  # noqa E501
                    block_1['call_conductor_name'] = data_list[0]['CONDUCTOR_NAME']
                    # operation_name
                    if block_1['operation_id']:
                        data_list = self.__db.table_select('T_COMN_OPERATION', 'WHERE `DISUSE_FLAG`=0 AND `OPERATION_ID`=%s', [block_1['operation_id']])  # noqa E501
                        block_1['operation_name'] = data_list[0]['OPERATION_NAME']

        except Exception as e:
            g.applogger.error(e)
            return False, retCode

        res = {
            'config': self.config_data,
            'conductor': self.conductor_data,
        }
        res.update(self.node_datas)
        res.update(self.edge_datas)

        return True, res,
