# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from oslo_log import log as logging

from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.plugins.provisioning as p
from sahara.utils import files

LOG = logging.getLogger(__name__)

CLDB = np.NodeProcess(
    name='cldb',
    ui_name='CLDB',
    package='mapr-cldb',
    open_ports=[7222, 7220, 7221]
)
FILE_SERVER = np.NodeProcess(
    name='fileserver',
    ui_name='FileServer',
    package='mapr-fileserver',
    open_ports=[]
)
NFS = np.NodeProcess(
    name='nfs',
    ui_name='NFS',
    package='mapr-nfs',
    open_ports=[2049, 9997, 9998]
)


class MapRFS(s.Service):
    _CREATE_DISK_LIST = 'plugins/mapr/resources/create_disk_list_file.sh'
    _DISK_SETUP_CMD = '/opt/mapr/server/disksetup -F /tmp/disk.list'
    _DISK_SETUP_TIMEOUT = 600

    ENABLE_MAPR_DB_NAME = 'Enable MapR-DB'
    HEAP_SIZE_PERCENT_NAME = 'MapR-FS heap size percent'

    ENABLE_MAPR_DB_CONFIG = p.Config(
        name=ENABLE_MAPR_DB_NAME,
        applicable_target='general',
        scope='cluster',
        config_type="bool",
        priority=1,
        default_value=True,
        description=_('Specifies that MapR-DB is in use.')
    )

    HEAP_SIZE_PERCENT = p.Config(
        name=HEAP_SIZE_PERCENT_NAME,
        applicable_target='MapRFS',
        scope='cluster',
        config_type="int",
        priority=1,
        default_value=8,
        description=_(
            'Specifies heap size for MapR-FS in percents of maximum value.')
    )

    def __init__(self):
        super(MapRFS, self).__init__()
        self._ui_name = 'MapRFS'
        self._node_processes = [CLDB, FILE_SERVER, NFS]
        self._ui_info = [
            ('Container Location Database (CLDB)', CLDB,
             {s.SERVICE_UI: 'http://%s:7221'}),
        ]
        self._validation_rules = [
            vu.at_least(1, CLDB),
            vu.each_node_has(FILE_SERVER),
            vu.on_same_node(CLDB, FILE_SERVER),
            vu.has_volumes(),
        ]

    def service_dir(self, cluster_context):
        return

    def home_dir(self, cluster_context):
        return

    def conf_dir(self, cluster_context):
        return '%s/conf' % cluster_context.mapr_home

    def post_install(self, cluster_context, instances):
        LOG.debug('Initializing MapR FS')
        instances = instances or cluster_context.get_instances()
        file_servers = cluster_context.filter_instances(instances, FILE_SERVER)
        with context.ThreadGroup() as tg:
            for instance in file_servers:
                tg.spawn('init-mfs-%s' % instance.id,
                         self._init_mfs_instance, instance)
        LOG.info(_LI('MapR FS successfully initialized'))

    def _init_mfs_instance(self, instance):
        self._generate_disk_list_file(instance, self._CREATE_DISK_LIST)
        self._execute_disksetup(instance)

    def _generate_disk_list_file(self, instance, path_to_disk_setup_script):
        LOG.debug('Creating disk list file')
        g.run_script(instance, path_to_disk_setup_script, 'root',
                     *instance.storage_paths())

    def _execute_disksetup(self, instance):
        with instance.remote() as rmt:
            rmt.execute_command(
                self._DISK_SETUP_CMD, run_as_root=True,
                timeout=self._DISK_SETUP_TIMEOUT)

    def get_configs(self):
        return [MapRFS.ENABLE_MAPR_DB_CONFIG, MapRFS.HEAP_SIZE_PERCENT]

    def get_config_files(self, cluster_context, configs, instance=None):
        default_path = 'plugins/mapr/services/maprfs/resources/cldb.conf'
        cldb_conf = bcf.PropertiesFile("cldb.conf")
        cldb_conf.remote_path = self.conf_dir(cluster_context)
        if instance:
            cldb_conf.fetch(instance)
        cldb_conf.parse(files.get_file_text(default_path))
        cldb_conf.add_properties(self._get_cldb_conf_props(cluster_context))

        warden_conf = bcf.PropertiesFile("warden.conf")
        warden_conf.remote_path = "/opt/mapr/conf/"
        if instance:
            warden_conf.fetch(instance)
        warden_conf.add_properties(
            {'service.command.mfs.heapsize.percent': configs[
                self.HEAP_SIZE_PERCENT_NAME]})

        return [cldb_conf, warden_conf]

    def _get_cldb_conf_props(self, context):
        zookeepers = context.get_zookeeper_nodes_ip_with_port()
        return {'cldb.zookeeper.servers': zookeepers}
