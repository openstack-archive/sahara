# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from sahara.plugins.mapr.util import cluster_helper as clh_utils
from sahara.plugins.mapr.util import start_helper as start_helper
import sahara.plugins.utils as utils


def exec_configure_sh_on_cluster(cluster):
    inst_list = utils.get_instances(cluster)
    for n in inst_list:
        exec_configure_sh_on_instance(cluster, n)


def exec_configure_sh_on_instance(cluster, instance):
    script_string = ('/opt/mapr/server/configure.sh'
                     + ' -C ' + clh_utils.get_cldb_nodes_ip(cluster)
                     + ' -Z ' + clh_utils.get_zookeeper_nodes_ip(cluster)
                     + ' -f')
    if not start_helper.check_if_mapr_user_exist(instance):
        script_string = script_string + ' --create-user'

    instance.remote().execute_command(script_string, True)
