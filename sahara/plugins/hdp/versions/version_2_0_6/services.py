# Copyright (c) 2014 Hortonworks, Inc.
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

import re

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara import exceptions as e
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.plugins import exceptions as ex
from sahara.plugins import utils
from sahara.swift import swift_helper as h
from sahara.topology import topology_helper as th

CONF = cfg.CONF
TOPOLOGY_CONFIG = {
    "net.topology.node.switch.mapping.impl":
    "org.apache.hadoop.net.ScriptBasedMapping",
    "net.topology.script.file.name":
    "/etc/hadoop/conf/topology.sh"
}

LOG = logging.getLogger(__name__)


def create_service(name):
    for cls in Service.__subclasses__():
        if cls.get_service_id() == name:
            return cls()
    # no subclass found, return service base class
    return Service(name)


class Service(object):
    def __init__(self, name, ambari_managed=True):
        self.name = name
        self.configurations = set(['global', 'core-site'])
        self.components = []
        self.users = []
        self.deployed = False
        self.ambari_managed = ambari_managed

    def add_component(self, component):
        self.components.append(component)

    def add_user(self, user):
        self.users.append(user)

    def validate(self, cluster_spec, cluster):
        pass

    def finalize_configuration(self, cluster_spec):
        pass

    def register_user_input_handlers(self, ui_handlers):
        pass

    def register_service_urls(self, cluster_spec, url_info):
        return url_info

    def pre_service_start(self, cluster_spec, ambari_info, started_services):
        pass

    def finalize_ng_components(self, cluster_spec):
        pass

    def is_user_template_component(self, component):
        return True

    def is_mandatory(self):
        return False

    def _replace_config_token(self, cluster_spec, token, value, props):
        for config_name, props in six.iteritems(props):
            config = cluster_spec.configurations[config_name]
            for prop in props:
                config[prop] = config[prop].replace(token, value)

    def _update_config_values(self, configurations, value, props):
        for absolute_prop_name in props:
            tokens = absolute_prop_name.split('/')
            config_name = tokens[0]
            prop_name = tokens[1]
            config = configurations[config_name]
            config[prop_name] = value

    def _get_common_paths(self, node_groups):
        if len(node_groups) == 1:
            paths = node_groups[0].storage_paths()
        else:
            sets = [set(ng.storage_paths()) for ng in node_groups]
            paths = list(set.intersection(*sets))

        if len(paths) > 1 and '/mnt' in paths:
            paths.remove('/mnt')

        return paths

    def _generate_storage_path(self, storage_paths, path):
        return ",".join([p + path for p in storage_paths])

    def _get_port_from_cluster_spec(self, cluster_spec, service, prop_name):
        address = cluster_spec.configurations[service][prop_name]
        return utils.get_port_from_address(address)


class HdfsService(Service):
    def __init__(self):
        super(HdfsService, self).__init__(HdfsService.get_service_id())
        self.configurations.add('hdfs-site')

    @classmethod
    def get_service_id(cls):
        return 'HDFS'

    def validate(self, cluster_spec, cluster):
        # Check NAMENODE and HDFS HA constraints
        nn_count = cluster_spec.get_deployed_node_group_count('NAMENODE')
        jn_count = cluster_spec.get_deployed_node_group_count('JOURNALNODE')
        zkfc_count = cluster_spec.get_deployed_node_group_count('ZKFC')

        if cluster_spec.is_hdfs_ha_enabled(cluster):
            if nn_count != 2:
                raise ex.NameNodeHAConfigurationError(
                    "Hadoop cluster with HDFS HA enabled requires "
                    "2 NAMENODE. Actual NAMENODE count is %s" % nn_count)
            # Check the number of journalnodes
            if not (jn_count >= 3 and (jn_count % 2 == 1)):
                raise ex.NameNodeHAConfigurationError(
                    "JOURNALNODE count should be an odd number "
                    "greater than or equal 3 for NameNode High Availability. "
                    "Actual JOURNALNODE count is %s" % jn_count)
        else:
            if nn_count != 1:
                raise ex.InvalidComponentCountException('NAMENODE', 1,
                                                        nn_count)
            # make sure that JOURNALNODE is only used when HDFS HA is enabled
            if jn_count > 0:
                raise ex.NameNodeHAConfigurationError(
                    "JOURNALNODE can only be added when "
                    "NameNode High Availability is enabled.")
            # make sure that ZKFC is only used when HDFS HA is enabled
            if zkfc_count > 0:
                raise ex.NameNodeHAConfigurationError(
                    "ZKFC can only be added when "
                    "NameNode High Availability is enabled.")

    def finalize_configuration(self, cluster_spec):
        nn_hosts = cluster_spec.determine_component_hosts('NAMENODE')
        if nn_hosts:
            props = {'core-site': ['fs.defaultFS'],
                     'hdfs-site': ['dfs.namenode.http-address',
                                   'dfs.namenode.https-address']}
            self._replace_config_token(
                cluster_spec, '%NN_HOST%', nn_hosts.pop().fqdn(), props)

        snn_hosts = cluster_spec.determine_component_hosts(
            'SECONDARY_NAMENODE')
        if snn_hosts:
            props = {'hdfs-site': ['dfs.namenode.secondary.http-address']}
            self._replace_config_token(
                cluster_spec, '%SNN_HOST%', snn_hosts.pop().fqdn(), props)

        # add swift properties to configuration
        core_site_config = cluster_spec.configurations['core-site']
        for prop in self._get_swift_properties():
            core_site_config[prop['name']] = prop['value']

        # add topology properties to configuration, if enabled
        if CONF.enable_data_locality:
            for prop in th.vm_awareness_core_config():
                core_site_config[prop['name']] = prop['value']

            core_site_config.update(TOPOLOGY_CONFIG)

            # process storage paths to accommodate ephemeral or cinder storage
        nn_ng = cluster_spec.get_node_groups_containing_component(
            'NAMENODE')[0]
        dn_node_groups = cluster_spec.get_node_groups_containing_component(
            'DATANODE')
        common_paths = []
        if dn_node_groups:
            common_paths = self._get_common_paths(dn_node_groups)
        hdfs_site_config = cluster_spec.configurations['hdfs-site']
        hdfs_site_config['dfs.namenode.name.dir'] = (
            self._generate_storage_path(
                nn_ng.storage_paths(), '/hadoop/hdfs/namenode'))
        if common_paths:
            hdfs_site_config['dfs.datanode.data.dir'] = (
                self._generate_storage_path(
                    common_paths, '/hadoop/hdfs/data'))

    def register_service_urls(self, cluster_spec, url_info):
        namenode_ip = cluster_spec.determine_component_hosts(
            'NAMENODE').pop().management_ip

        ui_port = self._get_port_from_cluster_spec(cluster_spec, 'hdfs-site',
                                                   'dfs.namenode.http-address')
        nn_port = self._get_port_from_cluster_spec(cluster_spec, 'core-site',
                                                   'fs.defaultFS')

        url_info['HDFS'] = {
            'Web UI': 'http://%s:%s' % (namenode_ip, ui_port),
            'NameNode': 'hdfs://%s:%s' % (namenode_ip, nn_port)
        }
        return url_info

    def finalize_ng_components(self, cluster_spec):
        hdfs_ng = cluster_spec.get_node_groups_containing_component(
            'NAMENODE')[0]
        components = hdfs_ng.components
        if not cluster_spec.get_deployed_node_group_count('ZOOKEEPER_SERVER'):
            zk_service = next(service for service in cluster_spec.services
                              if service.name == 'ZOOKEEPER')
            zk_service.deployed = True
            components.append('ZOOKEEPER_SERVER')

    def is_mandatory(self):
        return True

    def _get_swift_properties(self):
        return h.get_swift_configs()


class MapReduce2Service(Service):
    def __init__(self):
        super(MapReduce2Service, self).__init__(
            MapReduce2Service.get_service_id())
        self.configurations.add('mapred-site')

    @classmethod
    def get_service_id(cls):
        return 'MAPREDUCE2'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('HISTORYSERVER')
        if count != 1:
            raise ex.InvalidComponentCountException('HISTORYSERVER', 1, count)

    def finalize_configuration(self, cluster_spec):
        hs_hosts = cluster_spec.determine_component_hosts('HISTORYSERVER')
        if hs_hosts:
            props = {'mapred-site': ['mapreduce.jobhistory.webapp.address',
                                     'mapreduce.jobhistory.address']}

            self._replace_config_token(
                cluster_spec, '%HS_HOST%', hs_hosts.pop().fqdn(), props)

        # data locality/rack awareness prop processing
        mapred_site_config = cluster_spec.configurations['mapred-site']
        if CONF.enable_data_locality:
            for prop in th.vm_awareness_mapred_config():
                mapred_site_config[prop['name']] = prop['value']

    def register_service_urls(self, cluster_spec, url_info):
        historyserver_ip = cluster_spec.determine_component_hosts(
            'HISTORYSERVER').pop().management_ip

        ui_port = self._get_port_from_cluster_spec(
            cluster_spec, 'mapred-site', 'mapreduce.jobhistory.webapp.address')
        hs_port = self._get_port_from_cluster_spec(
            cluster_spec, 'mapred-site', 'mapreduce.jobhistory.address')

        url_info['MapReduce2'] = {
            'Web UI': 'http://%s:%s' % (historyserver_ip, ui_port),
            'History Server': '%s:%s' % (historyserver_ip, hs_port)
        }
        return url_info

    def finalize_ng_components(self, cluster_spec):
        mr2_ng = cluster_spec.get_node_groups_containing_component(
            'HISTORYSERVER')[0]
        components = mr2_ng.components
        if 'HDFS_CLIENT' not in components:
            components.append('HDFS_CLIENT')

    def is_mandatory(self):
        return True


class YarnService(Service):
    def __init__(self):
        super(YarnService, self).__init__(
            YarnService.get_service_id())
        self.configurations.add('yarn-site')
        self.configurations.add('capacity-scheduler')

    @classmethod
    def get_service_id(cls):
        return 'YARN'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('RESOURCEMANAGER')
        if count != 1:
            raise ex.InvalidComponentCountException('RESOURCEMANAGER', 1,
                                                    count)

        count = cluster_spec.get_deployed_node_group_count('NODEMANAGER')
        if not count:
            raise ex.InvalidComponentCountException(
                'NODEMANAGER', '> 0', count)

    def finalize_configuration(self, cluster_spec):
        rm_hosts = cluster_spec.determine_component_hosts('RESOURCEMANAGER')
        if rm_hosts:
            props = {'yarn-site': ['yarn.resourcemanager.'
                                   'resource-tracker.address',
                                   'yarn.resourcemanager.hostname',
                                   'yarn.resourcemanager.address',
                                   'yarn.resourcemanager.scheduler.address',
                                   'yarn.resourcemanager.webapp.address',
                                   'yarn.log.server.url',
                                   'yarn.resourcemanager.admin.address']}

            self._replace_config_token(
                cluster_spec, '%RM_HOST%', rm_hosts.pop().fqdn(), props)

        # data locality/rack awareness prop processing
        mapred_site_config = cluster_spec.configurations['mapred-site']
        if CONF.enable_data_locality:
            for prop in th.vm_awareness_mapred_config():
                mapred_site_config[prop['name']] = prop['value']

        # process storage paths to accommodate ephemeral or cinder storage
        yarn_site_config = cluster_spec.configurations['yarn-site']
        nm_node_groups = cluster_spec.get_node_groups_containing_component(
            'NODEMANAGER')
        if nm_node_groups:
            common_paths = self._get_common_paths(nm_node_groups)
            yarn_site_config['yarn.nodemanager.local-dirs'] = (
                self._generate_storage_path(common_paths,
                                            '/hadoop/yarn/local'))

    def register_service_urls(self, cluster_spec, url_info):
        resourcemgr_ip = cluster_spec.determine_component_hosts(
            'RESOURCEMANAGER').pop().management_ip

        ui_port = self._get_port_from_cluster_spec(
            cluster_spec, 'yarn-site', 'yarn.resourcemanager.webapp.address')
        rm_port = self._get_port_from_cluster_spec(
            cluster_spec, 'yarn-site', 'yarn.resourcemanager.address')

        url_info['Yarn'] = {
            'Web UI': 'http://%s:%s' % (resourcemgr_ip, ui_port),
            'ResourceManager': '%s:%s' % (resourcemgr_ip, rm_port)
        }
        return url_info

    def is_mandatory(self):
        return True


class HiveService(Service):
    def __init__(self):
        super(HiveService, self).__init__(HiveService.get_service_id())
        self.configurations.add('hive-site')

    @classmethod
    def get_service_id(cls):
        return 'HIVE'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('HIVE_SERVER')
        if count != 1:
            raise ex.InvalidComponentCountException('HIVE_SERVER', 1, count)

    def finalize_configuration(self, cluster_spec):
        hive_servers = cluster_spec.determine_component_hosts('HIVE_SERVER')
        if hive_servers:
            props = {'global': ['hive_hostname'],
                     'core-site': ['hadoop.proxyuser.hive.hosts']}
            self._replace_config_token(
                cluster_spec, '%HIVE_HOST%', hive_servers.pop().fqdn(), props)

        hive_ms = cluster_spec.determine_component_hosts('HIVE_METASTORE')
        if hive_ms:
            self._replace_config_token(
                cluster_spec, '%HIVE_METASTORE_HOST%', hive_ms.pop().fqdn(),
                {'hive-site': ['hive.metastore.uris']})

        hive_mysql = cluster_spec.determine_component_hosts('MYSQL_SERVER')
        if hive_mysql:
            self._replace_config_token(
                cluster_spec, '%HIVE_MYSQL_HOST%', hive_mysql.pop().fqdn(),
                {'hive-site': ['javax.jdo.option.ConnectionURL']})

    def register_user_input_handlers(self, ui_handlers):
        ui_handlers['hive-site/javax.jdo.option.ConnectionUserName'] = (
            self._handle_user_property_metastore_user)
        ui_handlers['hive-site/javax.jdo.option.ConnectionPassword'] = (
            self._handle_user_property_metastore_pwd)

    def _handle_user_property_metastore_user(self, user_input, configurations):
        hive_site_config_map = configurations['hive-site']
        hive_site_config_map['javax.jdo.option.ConnectionUserName'] = (
            user_input.value)

    def _handle_user_property_metastore_pwd(self, user_input, configurations):
        hive_site_config_map = configurations['hive-site']
        hive_site_config_map['javax.jdo.option.ConnectionPassword'] = (
            user_input.value)

    def finalize_ng_components(self, cluster_spec):
        hive_ng = cluster_spec.get_node_groups_containing_component(
            'HIVE_SERVER')[0]
        components = hive_ng.components
        if 'MAPREDUCE2_CLIENT' not in components:
            components.append('MAPREDUCE2_CLIENT')
        if not cluster_spec.get_deployed_node_group_count('HIVE_METASTORE'):
            components.append('HIVE_METASTORE')
        if not cluster_spec.get_deployed_node_group_count('MYSQL_SERVER'):
            components.append('MYSQL_SERVER')
        if not cluster_spec.get_deployed_node_group_count('ZOOKEEPER_SERVER'):
            zk_service = next(service for service in cluster_spec.services
                              if service.name == 'ZOOKEEPER')
            zk_service.deployed = True
            components.append('ZOOKEEPER_SERVER')


class WebHCatService(Service):
    def __init__(self):
        super(WebHCatService, self).__init__(WebHCatService.get_service_id())
        self.configurations.add('webhcat-site')

    @classmethod
    def get_service_id(cls):
        return 'WEBHCAT'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('WEBHCAT_SERVER')
        if count != 1:
            raise ex.InvalidComponentCountException('WEBHCAT_SERVER', 1, count)

    def finalize_configuration(self, cluster_spec):
        webhcat_servers = cluster_spec.determine_component_hosts(
            'WEBHCAT_SERVER')
        if webhcat_servers:
            self._replace_config_token(
                cluster_spec, '%WEBHCAT_HOST%', webhcat_servers.pop().fqdn(),
                {'core-site': ['hadoop.proxyuser.hcat.hosts']})

        hive_ms_servers = cluster_spec.determine_component_hosts(
            'HIVE_METASTORE')
        if hive_ms_servers:
            self._replace_config_token(
                cluster_spec, '%HIVE_METASTORE_HOST%',
                hive_ms_servers.pop().fqdn(),
                {'webhcat-site': ['templeton.hive.properties']})

        zk_servers = cluster_spec.determine_component_hosts('ZOOKEEPER_SERVER')
        if zk_servers:
            zk_list = ['{0}:2181'.format(z.fqdn()) for z in zk_servers]
            self._replace_config_token(
                cluster_spec, '%ZOOKEEPER_HOSTS%', ','.join(zk_list),
                {'webhcat-site': ['templeton.zookeeper.hosts']})

    def finalize_ng_components(self, cluster_spec):
        webhcat_ng = cluster_spec.get_node_groups_containing_component(
            'WEBHCAT_SERVER')[0]
        components = webhcat_ng.components
        if 'HDFS_CLIENT' not in components:
            components.append('HDFS_CLIENT')
        if 'MAPREDUCE2_CLIENT' not in components:
            components.append('MAPREDUCE2_CLIENT')
        # per AMBARI-3483
        if 'YARN_CLIENT' not in components:
            components.append('YARN_CLIENT')
        if 'ZOOKEEPER_CLIENT' not in components:
            # if zk server isn't in cluster, add to ng
            if not cluster_spec.get_deployed_node_group_count(
                    'ZOOKEEPER_SERVER'):

                zk_service = next(service for service in cluster_spec.services
                                  if service.name == 'ZOOKEEPER')
                zk_service.deployed = True
                components.append('ZOOKEEPER_SERVER')
            components.append('ZOOKEEPER_CLIENT')


class HBaseService(Service):
    property_map = {
        'hbase-site/hbase.tmp.dir': [
            'hbase-site/hbase.tmp.dir', 'global/hbase_tmp_dir'],
        'hbase-site/hbase.regionserver.global.memstore.upperLimit': [
            'hbase-site/hbase.regionserver.global.memstore.upperLimit',
            'global/regionserver_memstore_upperlimit'],
        'hbase-site/hbase.hstore.blockingStoreFiles': [
            'hbase-site/hbase.hstore.blockingStoreFiles',
            'global/hstore_blockingstorefiles'],
        'hbase-site/hbase.hstore.compactionThreshold': [
            'hbase-site/hbase.hstore.compactionThreshold',
            'global/hstore_compactionthreshold'],
        'hbase-site/hfile.block.cache.size': [
            'hbase-site/hfile.block.cache.size',
            'global/hfile_blockcache_size'],
        'hbase-site/hbase.hregion.max.filesize': [
            'hbase-site/hbase.hregion.max.filesize',
            'global/hstorefile_maxsize'],
        'hbase-site/hbase.regionserver.handler.count': [
            'hbase-site/hbase.regionserver.handler.count',
            'global/regionserver_handlers'],
        'hbase-site/hbase.hregion.majorcompaction': [
            'hbase-site/hbase.hregion.majorcompaction',
            'global/hregion_majorcompaction'],
        'hbase-site/hbase.regionserver.global.memstore.lowerLimit': [
            'hbase-site/hbase.regionserver.global.memstore.lowerLimit',
            'global/regionserver_memstore_lowerlimit'],
        'hbase-site/hbase.hregion.memstore.block.multiplier': [
            'hbase-site/hbase.hregion.memstore.block.multiplier',
            'global/hregion_blockmultiplier'],
        'hbase-site/hbase.hregion.memstore.mslab.enabled': [
            'hbase-site/hbase.hregion.memstore.mslab.enabled',
            'global/regionserver_memstore_lab'],
        'hbase-site/hbase.hregion.memstore.flush.size': [
            'hbase-site/hbase.hregion.memstore.flush.size'],
        'hbase-site/hbase.client.scanner.caching': [
            'hbase-site/hbase.client.scanner.caching',
            'global/client_scannercaching'],
        'hbase-site/zookeeper.session.timeout': [
            'hbase-site/zookeeper.session.timeout',
            'global/zookeeper_sessiontimeout'],
        'hbase-site/hbase.client.keyvalue.maxsize': [
            'hbase-site/hbase.client.keyvalue.maxsize',
            'global/hfile_max_keyvalue_size'],
        'hdfs-site/dfs.support.append': [
            'hdfs-site/dfs.support.append',
            'hbase-site/dfs.support.append',
            'global/hdfs_support_append'],
        'hbase-site/dfs.client.read.shortcircuit': [
            'hbase-site/dfs.client.read.shortcircuit',
            'global/hdfs_enable_shortcircuit_read']
    }

    def __init__(self):
        super(HBaseService, self).__init__(
            HBaseService.get_service_id())
        self.configurations.add('hbase-site')

    @classmethod
    def get_service_id(cls):
        return 'HBASE'

    def validate(self, cluster_spec, cluster):
        # check for a single HBASE_SERVER
        count = cluster_spec.get_deployed_node_group_count('HBASE_MASTER')
        if count != 1:
            raise ex.InvalidComponentCountException('HBASE_MASTER', 1, count)

    def register_service_urls(self, cluster_spec, url_info):
        master_ip = cluster_spec.determine_component_hosts(
            'HBASE_MASTER').pop().management_ip

        hbase_config = cluster_spec.configurations['hbase-site']
        info_port = hbase_config['hbase.master.info.port']

        url_info['HBase'] = {
            'Web UI': 'http://%s:%s/master-status' % (master_ip, info_port),
            'Logs': 'http://%s:%s/logs' % (master_ip, info_port),
            'Zookeeper Info': 'http://%s:%s/zk.jsp' % (master_ip, info_port),
            'JMX': 'http://%s:%s/jmx' % (master_ip, info_port),
            'Debug Dump': 'http://%s:%s/dump' % (master_ip, info_port),
            'Thread Stacks': 'http://%s:%s/stacks' % (master_ip, info_port)
        }
        return url_info

    def register_user_input_handlers(self, ui_handlers):
        for prop_name in self.property_map:
            ui_handlers[prop_name] = (
                self._handle_config_property_update)

        ui_handlers['hbase-site/hbase.rootdir'] = (
            self._handle_user_property_root_dir)

    def _handle_config_property_update(self, user_input, configurations):
        self._update_config_values(configurations, user_input.value,
                                   self.property_map[user_input.config.name])

    def _handle_user_property_root_dir(self, user_input, configurations):
        configurations['hbase-site']['hbase.rootdir'] = user_input.value

        match = re.search('(^hdfs://)(.*?)(/.*)', user_input.value)
        if match:
            configurations['global']['hbase_hdfs_root_dir'] = match.group(3)
        else:
            raise e.InvalidDataException(
                _("Invalid value for property 'hbase-site/hbase.rootdir' : %s")
                % user_input.value)

    def finalize_configuration(self, cluster_spec):
        nn_servers = cluster_spec.determine_component_hosts('NAMENODE')
        if nn_servers:
            self._replace_config_token(
                cluster_spec, '%NN_HOST%', nn_servers.pop().fqdn(),
                {'hbase-site': ['hbase.rootdir']})

        zk_servers = cluster_spec.determine_component_hosts('ZOOKEEPER_SERVER')
        if zk_servers:
            zk_list = [z.fqdn() for z in zk_servers]
            self._replace_config_token(
                cluster_spec, '%ZOOKEEPER_HOSTS%', ','.join(zk_list),
                {'hbase-site': ['hbase.zookeeper.quorum']})

    def finalize_ng_components(self, cluster_spec):
        hbase_ng = cluster_spec.get_node_groups_containing_component(
            'HBASE_MASTER')
        components = hbase_ng[0].components
        if 'HDFS_CLIENT' not in components:
            components.append('HDFS_CLIENT')

        if not cluster_spec.get_deployed_node_group_count(
                'HBASE_REGIONSERVER'):
            components.append('HBASE_REGIONSERVER')
        else:
            hbase_ng = cluster_spec.get_node_groups_containing_component(
                'HBASE_REGIONSERVER')
        for ng in hbase_ng:
            components = ng.components
            if 'HDFS_CLIENT' not in components:
                components.append('HDFS_CLIENT')

        if not cluster_spec.get_deployed_node_group_count('ZOOKEEPER_SERVER'):
            zk_service = next(service for service in cluster_spec.services
                              if service.name == 'ZOOKEEPER')
            zk_service.deployed = True
            components.append('ZOOKEEPER_SERVER')


class ZookeeperService(Service):
    def __init__(self):
        super(ZookeeperService, self).__init__(
            ZookeeperService.get_service_id())

    @classmethod
    def get_service_id(cls):
        return 'ZOOKEEPER'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('ZOOKEEPER_SERVER')
        if count < 1:
            raise ex.InvalidComponentCountException(
                'ZOOKEEPER_SERVER', '1+', count)

        # check if HDFS HA is enabled
        if cluster_spec.is_hdfs_ha_enabled(cluster):
            # check if we have an odd number of zookeeper_servers > 3
            if not (count >= 3 and (count % 2 == 1)):
                raise ex.NameNodeHAConfigurationError(
                    "ZOOKEEPER_SERVER count should be an odd number "
                    "greater than 3 for NameNode High Availability. "
                    "Actual ZOOKEEPER_SERVER count is %s" % count)

    def is_mandatory(self):
        return True


class OozieService(Service):
    def __init__(self):
        super(OozieService, self).__init__(OozieService.get_service_id())
        self.configurations.add('oozie-site')

    @classmethod
    def get_service_id(cls):
        return 'OOZIE'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('OOZIE_SERVER')
        if count != 1:
            raise ex.InvalidComponentCountException(
                'OOZIE_SERVER', 1, count)
        count = cluster_spec.get_deployed_node_group_count('OOZIE_CLIENT')
        if not count:
            raise ex.InvalidComponentCountException(
                'OOZIE_CLIENT', '1+', count)

    def finalize_configuration(self, cluster_spec):
        oozie_servers = cluster_spec.determine_component_hosts('OOZIE_SERVER')
        if oozie_servers:
            oozie_server = oozie_servers.pop()
            name_list = [oozie_server.fqdn(), oozie_server.internal_ip,
                         oozie_server.management_ip]
            self._replace_config_token(
                cluster_spec, '%OOZIE_HOST%', oozie_server.fqdn(),
                {'global': ['oozie_hostname'],
                 'oozie-site': ['oozie.base.url']})
            self._replace_config_token(
                cluster_spec, '%OOZIE_HOST%', ",".join(name_list),
                {'core-site': ['hadoop.proxyuser.oozie.hosts']})

    def finalize_ng_components(self, cluster_spec):
        oozie_ng = cluster_spec.get_node_groups_containing_component(
            'OOZIE_SERVER')[0]
        components = oozie_ng.components
        if 'HDFS_CLIENT' not in components:
            components.append('HDFS_CLIENT')
        if 'MAPREDUCE2_CLIENT' not in components:
            components.append('MAPREDUCE2_CLIENT')
        # per AMBARI-3483
        if 'YARN_CLIENT' not in components:
            components.append('YARN_CLIENT')
        # ensure that mr and hdfs clients are colocated with oozie client
        client_ngs = cluster_spec.get_node_groups_containing_component(
            'OOZIE_CLIENT')
        for ng in client_ngs:
            components = ng.components
            if 'HDFS_CLIENT' not in components:
                components.append('HDFS_CLIENT')
            if 'MAPREDUCE2_CLIENT' not in components:
                components.append('MAPREDUCE2_CLIENT')

    def register_service_urls(self, cluster_spec, url_info):
        oozie_ip = cluster_spec.determine_component_hosts(
            'OOZIE_SERVER').pop().management_ip
        port = self._get_port_from_cluster_spec(cluster_spec, 'oozie-site',
                                                'oozie.base.url')
        url_info['JobFlow'] = {
            'Oozie': 'http://%s:%s' % (oozie_ip, port)
        }
        return url_info

    def register_user_input_handlers(self, ui_handlers):
        ui_handlers['oozie-site/oozie.service.JPAService.jdbc.username'] = (
            self._handle_user_property_db_user)
        ui_handlers['oozie.service.JPAService.jdbc.password'] = (
            self._handle_user_property_db_pwd)

    def _handle_user_property_db_user(self, user_input, configurations):
        oozie_site_config_map = configurations['oozie-site']
        oozie_site_config_map['oozie.service.JPAService.jdbc.username'] = (
            user_input.value)

    def _handle_user_property_db_pwd(self, user_input, configurations):
        oozie_site_config_map = configurations['oozie-site']
        oozie_site_config_map['oozie.service.JPAService.jdbc.password'] = (
            user_input.value)


class GangliaService(Service):
    def __init__(self):
        super(GangliaService, self).__init__(GangliaService.get_service_id())

    @classmethod
    def get_service_id(cls):
        return 'GANGLIA'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('GANGLIA_SERVER')
        if count != 1:
            raise ex.InvalidComponentCountException('GANGLIA_SERVER', 1, count)

    def is_user_template_component(self, component):
        return component.name != 'GANGLIA_MONITOR'

    def finalize_ng_components(self, cluster_spec):
        for ng in cluster_spec.node_groups.values():
            if 'GANGLIA_MONITOR' not in ng.components:
                ng.components.append('GANGLIA_MONITOR')


class AmbariService(Service):
    def __init__(self):
        super(AmbariService, self).__init__(AmbariService.get_service_id(),
                                            False)
        self.configurations.add('ambari')
        # TODO(jspeidel): don't hard code default admin user
        self.admin_user_name = 'admin'

    @classmethod
    def get_service_id(cls):
        return 'AMBARI'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('AMBARI_SERVER')
        if count != 1:
            raise ex.InvalidComponentCountException('AMBARI_SERVER', 1, count)

    def register_service_urls(self, cluster_spec, url_info):
        ambari_ip = cluster_spec.determine_component_hosts(
            'AMBARI_SERVER').pop().management_ip

        port = cluster_spec.configurations['ambari'].get(
            'server.port', '8080')

        url_info['Ambari Console'] = {
            'Web UI': 'http://{0}:{1}'.format(ambari_ip, port)
        }
        return url_info

    def is_user_template_component(self, component):
        return component.name != 'AMBARI_AGENT'

    def register_user_input_handlers(self, ui_handlers):
        ui_handlers['ambari-stack/ambari.admin.user'] = (
            self._handle_user_property_admin_user)
        ui_handlers['ambari-stack/ambari.admin.password'] = (
            self._handle_user_property_admin_password)

    def is_mandatory(self):
        return True

    def _handle_user_property_admin_user(self, user_input, configurations):
        admin_user = next(user for user in self.users
                          if user.name == 'admin')
        admin_user.name = user_input.value
        self.admin_user_name = user_input.value

    def _handle_user_property_admin_password(self, user_input, configurations):
        admin_user = next(user for user in self.users
                          if user.name == self.admin_user_name)
        admin_user.password = user_input.value


class SqoopService(Service):
    def __init__(self):
        super(SqoopService, self).__init__(SqoopService.get_service_id())

    @classmethod
    def get_service_id(cls):
        return 'SQOOP'

    def finalize_ng_components(self, cluster_spec):
        sqoop_ngs = cluster_spec.get_node_groups_containing_component('SQOOP')
        for ng in sqoop_ngs:
            if 'HDFS_CLIENT' not in ng.components:
                ng.components.append('HDFS_CLIENT')
            if 'MAPREDUCE2_CLIENT' not in ng.components:
                ng.components.append('MAPREDUCE2_CLIENT')


class NagiosService(Service):
    def __init__(self):
        super(NagiosService, self).__init__(NagiosService.get_service_id())

    @classmethod
    def get_service_id(cls):
        return 'NAGIOS'

    def finalize_ng_components(self, cluster_spec):
        # per AMBARI-2946
        nagios_ngs = (
            cluster_spec.get_node_groups_containing_component('NAGIOS_SERVER'))
        for ng in nagios_ngs:
            if 'YARN_CLIENT' not in ng.components:
                ng.components.append('YARN_CLIENT')
            if 'MAPREDUCE2_CLIENT' not in ng.components:
                ng.components.append('MAPREDUCE2_CLIENT')
            if cluster_spec.get_deployed_node_group_count('OOZIE_SERVER'):
                if 'OOZIE_CLIENT' not in ng.components:
                    ng.components.append('OOZIE_CLIENT')
            if cluster_spec.get_deployed_node_group_count('HIVE_SERVER'):
                if 'HIVE_CLIENT' not in ng.components:
                    ng.components.append('HIVE_CLIENT')
                if 'HCAT' not in ng.components:
                    if not cluster_spec.get_deployed_node_group_count(
                            'HCATALOG'):
                        hcat_service = next(service for service in
                                            cluster_spec.services if
                                            service.name == 'HCATALOG')
                        hcat_service.deployed = True
                    ng.components.append('HCAT')


class HueService(Service):
    default_web_ui_port = '8000'
    required_services = ['HIVE', 'OOZIE', 'WEBHCAT', 'YARN']

    def __init__(self):
        super(HueService, self).__init__(HueService.get_service_id(), False)

    @classmethod
    def get_service_id(cls):
        return "HUE"

    @staticmethod
    def _get_java_home_from_config(config):
        return (config.get('java64_home', None)
                or config.get('java_home', None) if config else None)

    @staticmethod
    def _get_java_home(cluster_spec):
        java_home = HueService._get_java_home_from_config(
            cluster_spec.configurations.get('hue', None)
        )

        if not java_home:
            java_home = HueService._get_java_home_from_config(
                cluster_spec.configurations.get('global', None)
            )

        return java_home or '/opt/jdk1.6.0_31'

    @staticmethod
    def _append_host_substitution(cluster_spec, component, var_name,
                                  var_pattern_name, subs):
        hosts = cluster_spec.determine_component_hosts(component)

        if hosts:
            subs[var_name] = hosts.pop().fqdn() or 'localhost'
            subs[var_pattern_name] = subs[var_name].replace('.', '\.')

    @staticmethod
    def _create_hue_ini_file_section(property_sub_tree, level):
        properties = property_sub_tree['properties']
        sections = property_sub_tree['sections']

        s = ''

        if properties:
            for name, value in six.iteritems(properties):
                s += ' ' * (level * 2)
                s += "{0} = {1}\n".format(name, value)

        if sections:
            for name, section in six.iteritems(sections):
                s += "\n"

                s += ' ' * ((level - 1) * 2)
                s += '[' * level
                s += name
                s += ']' * level
                s += "\n"

                s += HueService._create_hue_ini_file_section(section,
                                                             level + 1)

        return s

    @staticmethod
    def _create_hue_ini_file(property_tree):
        if property_tree:
            return HueService._create_hue_ini_file_section(property_tree, 1)
        else:
            return ''

    @staticmethod
    def _create_hue_property_tree(cluster_spec):
        config_name = 'hue-ini'

        hue_ini_property_tree = {'sections': {}, 'properties': {}}

        config = cluster_spec.configurations[config_name]

        if config is None:
            LOG.warning(_LW('Missing configuration named {config_name}, '
                            'aborting Hue ini file creation').format(
                        config_name=config_name))
        else:
            # replace values in hue-ini configuration
            subs = {}

            subs['%JAVA_HOME%'] = HueService._get_java_home(cluster_spec)

            HueService._append_host_substitution(cluster_spec,
                                                 'NAMENODE',
                                                 '%NN_HOST%',
                                                 '%NN_HOST_PATTERN%',
                                                 subs)

            HueService._append_host_substitution(cluster_spec,
                                                 'RESOURCEMANAGER',
                                                 '%RM_HOST%',
                                                 '%RM_HOST_PATTERN%',
                                                 subs)

            HueService._append_host_substitution(cluster_spec,
                                                 'HISTORYSERVER',
                                                 '%HS_HOST%',
                                                 '%HS_HOST_PATTERN%',
                                                 subs)

            HueService._append_host_substitution(cluster_spec,
                                                 'OOZIE_SERVER',
                                                 '%OOZIE_HOST%',
                                                 '%OOZIE_HOST_PATTERN%',
                                                 subs)

            HueService._append_host_substitution(cluster_spec,
                                                 'WEBHCAT_SERVER',
                                                 '%WEBHCAT_HOST%',
                                                 '%WEBHCAT_HOST_PATTERN%',
                                                 subs)

            HueService._append_host_substitution(cluster_spec,
                                                 'HUE',
                                                 '%HUE_HOST%',
                                                 '%HUE_HOST_PATTERN%',
                                                 subs)

            # Parse configuration properties into Hue ini configuration tree
            # where <token1>:<token2>:<token3> = <value>
            # becomes
            #   <token1> {
            #       <token2> {
            #           <token3>=<value>
            #       }
            #   }
            for prop_name, prop_value in six.iteritems(config):
                # Skip empty property values
                if prop_value:
                    # Attempt to make any necessary substitutions
                    if subs:
                        for placeholder, sub in six.iteritems(subs):
                            if prop_value.find(placeholder) >= 0:
                                value = prop_value.replace(placeholder, sub)
                                LOG.debug('Converting placeholder in property '
                                          '{p_name}:\n\t\t{p_value}\n\tto\n\t'
                                          '\t{value}\n'.
                                          format(p_name=prop_name,
                                                 p_value=prop_value,
                                                 value=value))
                                prop_value = value

                    # If the property value still is a value, add it and it's
                    # relevant path to the tree
                    if prop_value and len(prop_value) > 0:
                        node = hue_ini_property_tree
                        tokens = prop_name.split('/')

                        if tokens:
                            name = tokens.pop()

                            while tokens:
                                token = tokens.pop(0)

                                if token not in node['sections']:
                                    data = {'sections': {},
                                            'properties': {}}

                                    node['sections'][token] = data

                                node = node['sections'][token]

                            # TODO(rlevas) : handle collisions
                            node['properties'][name] = prop_value

        LOG.info(_LI('Created Hue ini property tree from configuration named '
                     '{config_name}').format(config_name=config_name))

        return hue_ini_property_tree

    @staticmethod
    def _merge_configurations(cluster_spec, src_config_name, dst_config_name):
        src_config = cluster_spec.configurations[src_config_name]
        dst_config = cluster_spec.configurations[dst_config_name]

        if src_config is None:
            LOG.warning(_LW('Missing source configuration property set, '
                            'aborting merge: {config_name}').
                        format(config_name=src_config_name))
        elif dst_config is None:
            LOG.warning(_LW('Missing destination configuration property set, '
                            'aborting merge: {config_name}').
                        format(config_name=dst_config_name))
        else:
            for property_name, property_value in six.iteritems(src_config):
                if property_name in dst_config:
                    if dst_config[property_name] == src_config[property_name]:
                        LOG.debug('Skipping unchanged configuration property '
                                  'in {d_config_name} and {s_config_name}: '
                                  '{property_name}'
                                  .format(d_config_name=dst_config_name,
                                          s_config_name=src_config_name,
                                          property_name=property_name))
                    else:
                        LOG.warning(_LW('Overwriting existing configuration '
                                        'property in {dst_config_name} from '
                                        '{src_config_name} for Hue: '
                                        '{property_name} '
                                        '[{dst_config} -> {src_config}]').
                                    format(dst_config_name=dst_config_name,
                                           src_config_name=src_config_name,
                                           property_name=property_name,
                                           dst_config=dst_config[
                                               property_name],
                                           src_config=src_config[
                                               property_name]))
                else:
                    LOG.debug('Adding Hue configuration property to {d_config}'
                              ' from {s_config}: {p_name}'.format(
                                  d_config=dst_config_name,
                                  s_config=src_config_name,
                                  p_name=property_name))

                dst_config[property_name] = property_value
                LOG.info(_LI('Merged configuration properties: {source} -> '
                             '{destination}')
                         .format(source=src_config_name,
                                 destination=dst_config_name))

    @staticmethod
    def _handle_pre_service_start(instance, cluster_spec, hue_ini,
                                  create_user):
        with instance.remote() as r:
            r.execute_command('yum -y install hue',
                              run_as_root=True)
            LOG.info(_LI('Installed Hue on {fqdn}')
                     .format(fqdn=instance.fqdn()))

            r.write_file_to('/etc/hue/conf/hue.ini',
                            hue_ini,
                            True)
            # update hue.ini if HDFS HA is enabled and restart hadoop-httpfs
            # /tmp/hueini-hdfsha is written by versionhandler when HDFS is
            # enabled
            r.execute_command('[ ! -f /tmp/hueini-hdfsha ] || sed -i '
                              '"s/hdfs.*.:8020/hdfs:\\/\\/`cat '
                              '/tmp/hueini-hdfsha`/g" /etc/hue/conf/hue.ini',
                              run_as_root=True)
            r.execute_command('[ ! -f /tmp/hueini-hdfsha ] || sed -i '
                              '"s/http.*.\\/webhdfs\\/v1\\//http:\\/\\'
                              '/localhost:14000\\/webhdfs\\/v1\\//g" '
                              '/etc/hue/conf/hue.ini', run_as_root=True)
            LOG.info(_LI('Set Hue configuration on {fqdn}')
                     .format(fqdn=instance.fqdn()))

            r.execute_command(
                '/usr/lib/hue/build/env/bin/python '
                '/usr/lib/hue/tools/app_reg/app_reg.py '
                '--remove shell',
                run_as_root=True)
            LOG.info(_LI('Shell uninstalled, if it was installed '
                         'on {fqdn}').format(fqdn=instance.fqdn()))

            if create_user:
                r.execute_command('/usr/lib/hue/build/env/bin/hue '
                                  'create_sandbox_user', run_as_root=True)
                LOG.info(_LI('Initial Hue user created on {fqdn}')
                         .format(fqdn=instance.fqdn()))

            java_home = HueService._get_java_home(cluster_spec)
            if java_home:
                r.replace_remote_string(
                    '/etc/hadoop/conf/hadoop-env.sh',
                    'export JAVA_HOME=.*',
                    'export JAVA_HOME=%s' % java_home)

            r.execute_command('service hue start', run_as_root=True)

            # start httpfs if HDFS HA is enabled
            r.execute_command('[ ! -f /tmp/hueini-hdfsha ] || '
                              'service hadoop-httpfs start',
                              run_as_root=True)
            LOG.info(_LI('Hue (re)started on {fqdn}')
                     .format(fqdn=instance.fqdn()))

    def finalize_configuration(self, cluster_spec):
        # add Hue-specific properties to the core-site file ideally only on
        # the following nodes:
        #
        #       NameNode
        #       Secondary
        #       NameNode
        #       DataNodes
        #
        LOG.debug('Inserting Hue configuration properties into core-site')
        self._merge_configurations(cluster_spec, 'hue-core-site', 'core-site')

        # add Hue-specific properties to the hdfs-site file
        LOG.debug('Inserting Hue configuration properties into hdfs-site')
        self._merge_configurations(cluster_spec, 'hue-hdfs-site', 'hdfs-site')

        # add Hue-specific properties to the webhcat-site file
        LOG.debug('Inserting Hue configuration properties into webhcat-site')
        self._merge_configurations(cluster_spec, 'hue-webhcat-site',
                                   'webhcat-site')

        # add Hue-specific properties to the webhcat-site file
        LOG.debug('Inserting Hue configuration properties into oozie-site')
        self._merge_configurations(cluster_spec, 'hue-oozie-site',
                                   'oozie-site')

    def register_service_urls(self, cluster_spec, url_info):
        hosts = cluster_spec.determine_component_hosts('HUE')

        if hosts is not None:
            host = hosts.pop()

            if host is not None:
                config = cluster_spec.configurations['hue-ini']
                if config is not None:
                    port = config.get('desktop/http_port',
                                      self.default_web_ui_port)
                else:
                    port = self.default_web_ui_port

                ip = host.management_ip

                url_info[self.name.title()] = {
                    'Web UI': 'http://{0}:{1}'.format(ip, port)
                }

        return url_info

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('HUE')
        if count != 1:
            raise ex.InvalidComponentCountException('HUE', 1, count)

        services = cluster_spec.services

        for reqd_service in self.required_services:
            reqd_service_deployed = False

            if services is not None:
                for service in services:
                    reqd_service_deployed = (service.deployed
                                             and service.name == reqd_service)

                    if reqd_service_deployed:
                        break

            if not reqd_service_deployed:
                raise ex.RequiredServiceMissingException(reqd_service,
                                                         self.name)

    def finalize_ng_components(self, cluster_spec):
        hue_ngs = cluster_spec.get_node_groups_containing_component('HUE')

        if hue_ngs is not None:
            for hue_ng in hue_ngs:
                components = hue_ng.components

                if 'HDFS_CLIENT' not in components:
                    components.append('HDFS_CLIENT')
                    LOG.info(_LI('HDFS client was missed from Hue node. '
                                 'Added it since it is required for Hue'))

                if cluster_spec.get_deployed_node_group_count('HIVE_SERVER'):
                    if 'HIVE_CLIENT' not in components:
                        components.append('HIVE_CLIENT')
                        LOG.info(_LI('HIVE client was missed from Hue node. '
                                     'Added it since it is required for '
                                     'Beeswax and HCatalog'))

    def pre_service_start(self, cluster_spec, ambari_info, started_services):

        # Create hue.ini file
        hue_property_tree = HueService._create_hue_property_tree(cluster_spec)
        hue_ini = HueService._create_hue_ini_file(hue_property_tree)

        create_user = False
        config = cluster_spec.configurations['hue-ini']

        if config is not None:
            username = config.get('useradmin/default_username', '')
            password = config.get('useradmin/default_user_password', '')

            create_user = username != '' and password != ''

        # Install Hue on the appropriate node(s)...
        hue_ngs = cluster_spec.get_node_groups_containing_component("HUE")
        if hue_ngs:
            for ng in hue_ngs:
                if ng.instances:
                    for instance in ng.instances:
                        HueService._handle_pre_service_start(instance,
                                                             cluster_spec,
                                                             hue_ini,
                                                             create_user)
