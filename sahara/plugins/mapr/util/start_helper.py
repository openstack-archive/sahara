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

from oslo_log import log as logging

from sahara import context
from sahara.i18n import _LI
from sahara.plugins.mapr.util import names
from sahara.plugins.mapr.util import run_scripts
import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.plugins.utils as utils
from sahara.utils import files as files


LOG = logging.getLogger(__name__)


def exec_configure_sh_on_cluster(cluster, script_string):
    inst_list = utils.get_instances(cluster)
    for n in inst_list:
        exec_configure_sh_on_instance(cluster, n, script_string)


def exec_configure_sh_on_instance(cluster, instance, script_string):
    LOG.info(_LI('START: Executing configure.sh'))
    if check_for_mapr_db(cluster):
        script_string += ' -M7'
    if not check_if_mapr_user_exist(instance):
        script_string += ' --create-user'
    LOG.debug('script_string = %s', script_string)
    instance.remote().execute_command(script_string, run_as_root=True)
    LOG.info(_LI('END: Executing configure.sh'))


def check_for_mapr_db(cluster):
    h_version = cluster.hadoop_version
    v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
    return v_handler.get_context(cluster).is_m7_enabled()


def setup_maprfs_on_cluster(cluster, path_to_disk_setup_script):
    mapr_node_list = utils.get_instances(cluster, 'FileServer')
    for instance in mapr_node_list:
        setup_maprfs_on_instance(instance, path_to_disk_setup_script)


def setup_maprfs_on_instance(instance, path_to_disk_setup_script):
    LOG.info(_LI('START: Setup maprfs on instance %s'), instance.instance_name)
    create_disk_list_file(instance, path_to_disk_setup_script)
    execute_disksetup(instance)
    LOG.info(_LI('END: Setup maprfs on instance.'))


def create_disk_list_file(instance, path_to_disk_setup_script):
    LOG.info(_LI('START: Creating disk list file.'))
    script_path = '/tmp/disk_setup_script.sh'
    rmt = instance.remote()
    LOG.debug('Writing /tmp/disk_setup_script.sh')
    rmt.write_file_to(
        script_path, files.get_file_text(path_to_disk_setup_script))
    LOG.debug('Start executing command: chmod +x %s', script_path)
    rmt.execute_command('chmod +x ' + script_path, run_as_root=True)
    LOG.debug('Done for executing command.')
    args = ' '.join(instance.node_group.storage_paths())
    cmd = '%s %s' % (script_path, args)
    LOG.debug('Executing %s', cmd)
    rmt.execute_command(cmd, run_as_root=True)
    LOG.info(_LI('END: Creating disk list file.'))


def execute_disksetup(instance):
    LOG.info(_LI('START: Executing disksetup.'))
    rmt = instance.remote()
    rmt.execute_command(
        '/opt/mapr/server/disksetup -F /tmp/disk.list', run_as_root=True)
    LOG.info(_LI('END: Executing disksetup.'))


def wait_for_mfs_unlock(cluster, path_to_waiting_script):
    mapr_node_list = utils.get_instances(cluster, names.FILE_SERVER)
    for instance in mapr_node_list:
        create_waiting_script_file(instance, path_to_waiting_script)
        exec_waiting_script_on_instance(instance)


def start_zookeeper_nodes_on_cluster(cluster):
    zkeeper_node_list = utils.get_instances(cluster, names.ZOOKEEPER)
    for z_keeper_node in zkeeper_node_list:
        run_scripts.start_zookeeper(z_keeper_node.remote())


def start_warden_on_cluster(cluster):
    node_list = utils.get_instances(cluster)
    for node in node_list:
        run_scripts.start_warden(node.remote())


def start_warden_on_cldb_nodes(cluster):
    node_list = utils.get_instances(cluster, names.CLDB)
    for node in node_list:
        run_scripts.start_warden(node.remote())


def start_warden_on_other_nodes(cluster):
    node_list = utils.get_instances(cluster)
    for node in node_list:
        if names.CLDB not in node.node_group.node_processes:
            run_scripts.start_warden(node.remote())


def create_waiting_script_file(instance, path_to_waiting_script):
    LOG.info(_LI('START: Creating waiting script file.'))
    script_path = '/tmp/waiting_script.sh'
    rmt = instance.remote()
    rmt.write_file_to(script_path, files.get_file_text(path_to_waiting_script))
    LOG.info(_LI('END: Creating waiting script file.'))


def exec_waiting_script_on_instance(instance):
    LOG.info(_LI('START: Waiting script'))
    rmt = instance.remote()
    rmt.execute_command('chmod +x /tmp/waiting_script.sh', run_as_root=True)
    rmt.execute_command('/tmp/waiting_script.sh', run_as_root=True)
    LOG.info(_LI('END: Waiting script'))


def check_if_mapr_user_exist(instance):
    ec, out = instance.remote().execute_command('id -u mapr',
                                                run_as_root=True,
                                                raise_when_error=False)
    return ec == 0


def check_for_mapr_component(instance, component_name):
    component_list = instance.node_group.node_processes
    return component_name in component_list


def install_role_on_instance(instance,  cluster_context):
    LOG.info(_LI('START: Installing roles on node '))
    roles_list = instance.node_group.node_processes
    exec_str = (cluster_context.get_install_manager()
                + cluster_context.get_roles_str(roles_list))
    LOG.debug('Executing "%(command)s" on %(instance)s',
              {'command': exec_str, 'instance': instance.instance_id})

    instance.remote().execute_command(exec_str, run_as_root=True, timeout=900)
    LOG.info(_LI('END: Installing roles on node '))


def install_roles(cluster,  cluster_context):
    LOG.info(_LI('START: Installing roles on cluster'))
    instances = utils.get_instances(cluster)
    with context.ThreadGroup(len(instances)) as tg:
        for instance in instances:
            tg.spawn('install_roles_%s' % instance.instance_id,
                     install_role_on_instance,
                     instance,
                     cluster_context)
    LOG.info(_LI('END: Installing roles on cluster'))


def start_ecosystem(cluster_context):
    oozie_inst = cluster_context.get_oozie_instance()
    if oozie_inst is not None:
        context.sleep(names.WAIT_OOZIE_INTERVAL)
        run_scripts.start_oozie(oozie_inst.remote())
