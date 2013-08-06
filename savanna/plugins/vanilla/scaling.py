# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from savanna import context
from savanna.plugins.general import utils
from savanna.plugins.vanilla import run_scripts as run


def decommission_tt(jt, inst_to_be_deleted, survived_inst):
    with jt.remote as r:
        r.write_file_to('/etc/hadoop/tt.excl',
                        utils.generate_fqdn_host_names(
                            inst_to_be_deleted))
        run.refresh_nodes(jt.remote, "mradmin")
        context.sleep(3)
        r.write_files_to({'/etc/hadoop/tt.incl':
                         utils.generate_fqdn_host_names(survived_inst),
                         '/etc/hadoop/tt.excl': "",
                          })


def decommission_dn(nn, inst_to_be_deleted, survived_inst):
    with nn.remote as r:
        r.write_file_to('/etc/hadoop/dn.excl',
                        utils.generate_fqdn_host_names(
                            inst_to_be_deleted))
        run.refresh_nodes(nn.remote, "dfsadmin")
        context.sleep(3)

        att_amount = 10
        while att_amount:
            cmd = r.execute_command(
                "sudo su -c 'hadoop dfsadmin -report' hadoop")
            all_found = True
            datanodes_info = parse_dfs_report(cmd[1])
            for i in inst_to_be_deleted:
                for dn in datanodes_info:
                    if (dn["Name"].startswith(i.internal_ip)) and (
                            dn["Decommission Status"] != "Decommissioned"):
                        all_found = False
                        break

            if all_found:
                r.write_files_to({'/etc/hadoop/dn.incl':
                                 utils.
                                 generate_fqdn_host_names(survived_inst),
                                  '/etc/hadoop/dn.excl': "",
                                  })
                break
            context.sleep(3)
            att_amount -= 1

        if not att_amount:
            raise Exception("Cannot finish decommission")


def parse_dfs_report(cmd_output):
    report = cmd_output.rstrip().split(os.linesep)
    array = []
    started = False
    for line in report:
        if started:
            array.append(line)
        if line.startswith("Datanodes available"):
            started = True

    res = []
    datanode_info = {}
    for i in xrange(0, len(array)):
        if array[i]:
            idx = str.find(array[i], ':')
            name = array[i][0:idx]
            value = array[i][idx + 2:]
            datanode_info[name.strip()] = value.strip()
        if not array[i] and datanode_info:
            res.append(datanode_info)
            datanode_info = {}
    if datanode_info:
        res.append(datanode_info)
    return res
