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

from sahara import context
from sahara.i18n import _LI
from sahara.openstack.common import log as logging
from sahara.plugins.mapr.util import config
from sahara.plugins.mapr.util import names
from sahara.plugins.mapr.util import run_scripts
from sahara.plugins.mapr.util import start_helper
from sahara.utils import general as gen


LOG = logging.getLogger(__name__)

STOP_WARDEN_CMD = 'service mapr-warden stop'
STOP_ZOOKEEPER_CMD = 'service mapr-zookeeper stop'
GET_SERVER_ID_CMD = ('maprcli node list -json -filter [ip==%s] -columns id'
                     ' | grep id | grep -o \'[0-9]*\'')
MOVE_NODE_CMD = 'maprcli node move -serverids %s -topology /decommissioned'
GET_HOSTNAME_CMD = ('maprcli node list -json -filter [ip==%s]'
                    ' -columns hostname | grep hostname'
                    ' | grep -Po \'(?<=("hostname":")).*?(?=")\'')
REMOVE_NODE_CMD = 'maprcli node remove -filter [ip==%(ip)s] -nodes %(nodes)s'
REMOVE_MAPR_PACKAGES_CMD = ('python -mplatform | grep Ubuntu '
                            '&& apt-get remove mapr-\* -y'
                            ' || yum remove mapr-\* -y')
REMOVE_MAPR_HOME_CMD = 'rm -rf /opt/mapr'
REMOVE_MAPR_CORES_CMD = 'rm -rf /opt/cores/*.core.*'


def scale_cluster(cluster, instances, disk_setup_script_path, waiting_script,
                  context, configure_sh_string, is_node_awareness):
    LOG.info(_LI('START: Cluster scaling. Cluster = %s'), cluster.name)
    for inst in instances:
        start_helper.install_role_on_instance(inst, context)
    config.configure_instances(cluster, instances)
    start_services(cluster, instances, disk_setup_script_path,
                   waiting_script, configure_sh_string)
    LOG.info(_LI('END: Cluster scaling. Cluster = %s'), cluster)


def decommission_nodes(cluster, instances, configure_sh_string):
    LOG.info(_LI('Start decommission . Cluster = %s'), cluster.name)
    move_node(cluster, instances)
    stop_services(cluster, instances)
    context.sleep(names.WAIT_NODE_ALARM_NO_HEARTBEAT)
    remove_node(cluster, instances)
    remove_services(cluster, instances)
    if check_for_cldb_or_zookeeper_service(instances):
        all_instances = gen.get_instances(cluster)
        current_cluster_instances = [
            x for x in all_instances if x not in instances]
        for inst in current_cluster_instances:
            start_helper.exec_configure_sh_on_instance(
                cluster, inst, configure_sh_string)
    LOG.info(_LI('End decommission. Cluster = %s'), cluster.name)


def start_services(cluster, instances, disk_setup_script_path,
                   waiting_script, configure_sh_string):
    LOG.info(_LI('START: Starting services.'))
    for inst in instances:
        start_helper.exec_configure_sh_on_instance(
            cluster, inst, configure_sh_string)
        start_helper.wait_for_mfs_unlock(cluster, waiting_script)
        start_helper.setup_maprfs_on_instance(inst, disk_setup_script_path)

        if check_if_is_zookeeper_node(inst):
            run_scripts.start_zookeeper(inst.remote())

        run_scripts.start_warden(inst.remote())

    if check_for_cldb_or_zookeeper_service(instances):
        start_helper.exec_configure_sh_on_cluster(
            cluster, configure_sh_string)
    LOG.info(_LI('END: Starting services.'))


def stop_services(cluster, instances):
    LOG.info(_LI("Stop warden and zookeeper"))
    for instance in instances:
        with instance.remote() as r:
            r.execute_command(STOP_WARDEN_CMD, run_as_root=True)
            if check_if_is_zookeeper_node(instance):
                r.execute_command(STOP_ZOOKEEPER_CMD, run_as_root=True)
    LOG.info(_LI("Warden and zookeeper stoped"))


def move_node(cluster, instances):
    LOG.info(_LI("Start moving the node to the /decommissioned"))
    for instance in instances:
        with instance.remote() as r:
            command = GET_SERVER_ID_CMD % instance.management_ip
            ec, out = r.execute_command(command, run_as_root=True)
            command = MOVE_NODE_CMD % out.strip()
            r.execute_command(command, run_as_root=True)
    LOG.info(_LI("Nodes moved to the /decommissioned"))


def remove_node(cluster, instances):
    LOG.info("Start removing the nodes")
    for instance in instances:
        with instance.remote() as r:
            command = GET_HOSTNAME_CMD % instance.management_ip
            ec, out = r.execute_command(command, run_as_root=True)
            command = REMOVE_NODE_CMD % {'ip': instance.management_ip,
                                         'nodes': out.strip()}
            r.execute_command(command, run_as_root=True)
    LOG.info("Nodes removed")


def remove_services(cluster, instances):
    LOG.info(_LI("Start remove all mapr services"))
    for instance in instances:
        with instance.remote() as r:
            r.execute_command(REMOVE_MAPR_PACKAGES_CMD, run_as_root=True)
            r.execute_command(REMOVE_MAPR_HOME_CMD, run_as_root=True)
            r.execute_command(REMOVE_MAPR_CORES_CMD, run_as_root=True)
    LOG.info(_LI("All mapr services removed"))


def check_if_is_zookeeper_node(instance):
    processes_list = instance.node_group.node_processes
    return names.ZOOKEEPER in processes_list


def check_for_cldb_or_zookeeper_service(instances):
    for inst in instances:
        np_list = inst.node_group.node_processes
        if names.ZOOKEEPER in np_list or names.CLDB in np_list:
            return True
    return False
