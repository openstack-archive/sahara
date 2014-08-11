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

from oslo.config import cfg

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.openstack.common import log as logging
import sahara.plugins.mapr.util.config_file_utils as cfu
import sahara.plugins.mapr.versions.version_handler_factory as vhf
from sahara.plugins import provisioning as p
import sahara.plugins.utils as u
from sahara.topology import topology_helper as th
from sahara.utils import files as f


MAPR_HOME = '/opt/mapr'
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF.import_opt("enable_data_locality", "sahara.topology.topology_helper")
ENABLE_DATA_LOCALITY = p.Config('Enable Data Locality', 'general', 'cluster',
                                config_type="bool", priority=1,
                                default_value=True, is_optional=True)


def post_configure_instance(instance):
    LOG.info(_LI('START: Post configuration for instance.'))
    with instance.remote() as r:
        if is_data_locality_enabled(instance.node_group.cluster):
            LOG.debug('Data locality is enabled.')
            t_script = MAPR_HOME + '/topology.sh'
            LOG.debug('Start writing file %s', t_script)
            r.write_file_to(t_script, f.get_file_text(
                'plugins/mapr/util/resources/topology.sh'), run_as_root=True)
            LOG.debug('Done for writing file %s', t_script)
            LOG.debug('Start executing command: chmod +x %s', t_script)
            r.execute_command('chmod +x ' + t_script, run_as_root=True)
            LOG.debug('Done for executing command.')
        else:
            LOG.debug('Data locality is disabled.')
    LOG.info(_LI('END: Post configuration for instance.'))


def configure_instances(cluster, instances):
    h_version = cluster.hadoop_version
    v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
    p_spec = v_handler.get_plugin_spec()
    configurer = v_handler.get_cluster_configurer(cluster, p_spec)
    configurer.configure(instances)


def configure_topology_data(cluster, is_node_awareness):
    LOG.info(_LI('START: configuring topology data.'))
    if is_data_locality_enabled(cluster):
        LOG.debug('Data locality is enabled.')
        LOG.debug('Start generating topology map.')
        topology_map = th.generate_topology_map(cluster, is_node_awareness)
        LOG.debug('Done for generating topology map.')
        topology_data = cfu.to_file_content(topology_map, 'topology')
        for i in u.get_instances(cluster):
            LOG.debug(
                'Start writing to file: %s/topology.data', MAPR_HOME)
            i.remote().write_file_to(MAPR_HOME + "/topology.data",
                                     topology_data, run_as_root=True)
            LOG.debug('Done writing to file: %s/topology.data', MAPR_HOME)
    else:
        LOG.debug('Data locality is disabled.')
    LOG.info(_LI('END: configuring topology data.'))


def get_plugin_configs():
    configs = []
    if CONF.enable_data_locality:
        configs.append(ENABLE_DATA_LOCALITY)
    return configs


def get_plugin_config_value(service, name, cluster):
    if cluster:
        for ng in cluster.node_groups:
            cl_param = ng.configuration().get(service, {}).get(name)
            if cl_param is not None:
                return cl_param

    for c in get_plugin_configs():
        if c.applicable_target == service and c.name == name:
            return c.default_value

    raise ex.NotFoundException(
        name, (_("Unable to get parameter '%(name)s' from service %(service)s")
               % {'name': name, 'service': service}))


def is_data_locality_enabled(cluster):
    if not CONF.enable_data_locality:
        return False
    return get_plugin_config_value(ENABLE_DATA_LOCALITY.applicable_target,
                                   ENABLE_DATA_LOCALITY.name, cluster)
