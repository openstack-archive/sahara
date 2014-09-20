# Copyright (c) 2013 Hortonworks, Inc.
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

from oslo.config import cfg
import six


from sahara import exceptions as e
from sahara.i18n import _
from sahara.plugins.general import exceptions as ex
from sahara.plugins.general import utils
from sahara.swift import swift_helper as h
from sahara.topology import topology_helper as th


CONF = cfg.CONF
TOPOLOGY_CONFIG = {
    "topology.node.switch.mapping.impl":
    "org.apache.hadoop.net.ScriptBasedMapping",
    "topology.script.file.name":
    "/etc/hadoop/conf/topology.sh"
}


def create_service(name):
    for cls in Service.__subclasses__():
        if cls.get_service_id() == name:
            return cls()
    # no subclass found, return service base class
    return Service(name)


class Service(object):
    def __init__(self, name):
        self.name = name
        self.configurations = set(['global', 'core-site'])
        self.components = []
        self.users = []
        self.deployed = False

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
        # check for a single NAMENODE
        count = cluster_spec.get_deployed_node_group_count('NAMENODE')
        if count != 1:
            raise ex.InvalidComponentCountException('NAMENODE', 1, count)

    def finalize_configuration(self, cluster_spec):
        nn_hosts = cluster_spec.determine_component_hosts('NAMENODE')
        if nn_hosts:
            props = {'core-site': ['fs.default.name'],
                     'hdfs-site': ['dfs.http.address', 'dfs.https.address']}
            self._replace_config_token(
                cluster_spec, '%NN_HOST%', nn_hosts.pop().fqdn(), props)

        snn_hosts = cluster_spec.determine_component_hosts(
            'SECONDARY_NAMENODE')
        if snn_hosts:
            props = {'hdfs-site': ['dfs.secondary.http.address']}
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
        global_config = cluster_spec.configurations['global']
        hdfs_site_config['dfs.name.dir'] = self._generate_storage_path(
            nn_ng.storage_paths(), '/hadoop/hdfs/namenode')
        global_config['dfs_name_dir'] = self._generate_storage_path(
            nn_ng.storage_paths(), '/hadoop/hdfs/namenode')
        if common_paths:
            hdfs_site_config['dfs.data.dir'] = self._generate_storage_path(
                common_paths, '/hadoop/hdfs/data')
            global_config['dfs_data_dir'] = self._generate_storage_path(
                common_paths, '/hadoop/hdfs/data')

    def register_service_urls(self, cluster_spec, url_info):
        namenode_ip = cluster_spec.determine_component_hosts(
            'NAMENODE').pop().management_ip

        ui_port = self._get_port_from_cluster_spec(cluster_spec, 'hdfs-site',
                                                   'dfs.http.address')
        nn_port = self._get_port_from_cluster_spec(cluster_spec, 'core-site',
                                                   'fs.default.name')

        url_info['HDFS'] = {
            'Web UI': 'http://%s:%s' % (namenode_ip, ui_port),
            'NameNode': 'hdfs://%s:%s' % (namenode_ip, nn_port)
        }
        return url_info

    def is_mandatory(self):
        return True

    def _get_swift_properties(self):
        return h.get_swift_configs()


class MapReduceService(Service):
    def __init__(self):
        super(MapReduceService, self).__init__(
            MapReduceService.get_service_id())
        self.configurations.add('mapred-site')

    @classmethod
    def get_service_id(cls):
        return 'MAPREDUCE'

    def validate(self, cluster_spec, cluster):
        count = cluster_spec.get_deployed_node_group_count('JOBTRACKER')
        if count != 1:
            raise ex.InvalidComponentCountException('JOBTRACKER', 1, count)

        count = cluster_spec.get_deployed_node_group_count('TASKTRACKER')
        if not count:
            raise ex.InvalidComponentCountException(
                'TASKTRACKER', '> 0', count)

    def finalize_configuration(self, cluster_spec):
        jt_hosts = cluster_spec.determine_component_hosts('JOBTRACKER')
        if jt_hosts:
            props = {'mapred-site': ['mapred.job.tracker',
                                     'mapred.job.tracker.http.address',
                                     'mapreduce.history.server.http.address']}

            self._replace_config_token(
                cluster_spec, '%JT_HOST%', jt_hosts.pop().fqdn(), props)

        # HISTORYSERVER component now a part of MapReduce 1 in Ambari 1.6.0
        hs_hosts = cluster_spec.determine_component_hosts('HISTORYSERVER')
        if hs_hosts:
            props = {'mapred-site': ['mapreduce.jobhistory.webapp.address']}

            self._replace_config_token(
                cluster_spec, '%HS_HOST%', hs_hosts.pop().fqdn(), props)

        # data locality/rack awareness prop processing
        mapred_site_config = cluster_spec.configurations['mapred-site']
        if CONF.enable_data_locality:
            for prop in th.vm_awareness_mapred_config():
                mapred_site_config[prop['name']] = prop['value']

        # process storage paths to accommodate ephemeral or cinder storage
        # NOTE:  mapred.system.dir is an HDFS namespace path (not a filesystem
        # path) so the default path should suffice
        tt_node_groups = cluster_spec.get_node_groups_containing_component(
            'TASKTRACKER')
        if tt_node_groups:
            global_config = cluster_spec.configurations['global']
            common_paths = self._get_common_paths(tt_node_groups)
            mapred_site_config['mapred.local.dir'] = (
                self._generate_storage_path(common_paths, '/hadoop/mapred'))
            global_config['mapred_local_dir'] = self._generate_storage_path(
                common_paths, '/hadoop/mapred')

    def finalize_ng_components(self, cluster_spec):
        # add HISTORYSERVER, since HDP 1.3.2 stack was
        # modified in Ambari 1.5.1/1.6.0 to include this component
        # in the MAPREDUCE service
        ambari_server_ngs = (
            cluster_spec.get_node_groups_containing_component('JOBTRACKER'))
        for ng in ambari_server_ngs:
            if 'HISTORYSERVER' not in ng.components:
                ng.components.append('HISTORYSERVER')

    def register_service_urls(self, cluster_spec, url_info):
        jobtracker_ip = cluster_spec.determine_component_hosts(
            'JOBTRACKER').pop().management_ip

        ui_port = self._get_port_from_cluster_spec(
            cluster_spec, 'mapred-site', 'mapreduce.jobhistory.webapp.address')
        jt_port = self._get_port_from_cluster_spec(
            cluster_spec, 'mapred-site', 'mapred.job.tracker')

        url_info['MapReduce'] = {
            'Web UI': 'http://%s:%s' % (jobtracker_ip, ui_port),
            'JobTracker': '%s:%s' % (jobtracker_ip, jt_port)
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
                     'core-site': ['hadoop.proxyuser.hive.hosts'],
                     'hive-site': ['javax.jdo.option.ConnectionURL']}
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
                {'global': ['hive_jdbc_connection_url']})

    def register_user_input_handlers(self, ui_handlers):
        ui_handlers['hive-site/javax.jdo.option.ConnectionUserName'] = (
            self._handle_user_property_metastore_user)
        ui_handlers['hive-site/javax.jdo.option.ConnectionPassword'] = (
            self._handle_user_property_metastore_pwd)

    def _handle_user_property_metastore_user(self, user_input, configurations):
        hive_site_config_map = configurations['hive-site']
        hive_site_config_map['javax.jdo.option.ConnectionUserName'] = (
            user_input.value)
        global_config_map = configurations['global']
        global_config_map['hive_metastore_user_name'] = user_input.value

    def _handle_user_property_metastore_pwd(self, user_input, configurations):
        hive_site_config_map = configurations['hive-site']
        hive_site_config_map['javax.jdo.option.ConnectionPassword'] = (
            user_input.value)
        global_config_map = configurations['global']
        global_config_map['hive_metastore_user_passwd'] = user_input.value

    def finalize_ng_components(self, cluster_spec):
        hive_ng = cluster_spec.get_node_groups_containing_component(
            'HIVE_SERVER')[0]
        components = hive_ng.components
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
        if 'MAPREDUCE_CLIENT' not in components:
            components.append('MAPREDUCE_CLIENT')
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
            'hbase-site/hbase.hregion.memstore.flush.size',
            'global/hregion_memstoreflushsize'],
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
            'HBASE_MASTER')[0]
        components = hbase_ng.components
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
        if 'MAPREDUCE_CLIENT' not in components:
            components.append('MAPREDUCE_CLIENT')
        # ensure that mr and hdfs clients are colocated with oozie client
        client_ngs = cluster_spec.get_node_groups_containing_component(
            'OOZIE_CLIENT')
        for ng in client_ngs:
            components = ng.components
            if 'HDFS_CLIENT' not in components:
                components.append('HDFS_CLIENT')
        if 'MAPREDUCE_CLIENT' not in components:
            components.append('MAPREDUCE_CLIENT')

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
        global_config_map = configurations['global']
        global_config_map['oozie_metastore_user_name'] = user_input.value

    def _handle_user_property_db_pwd(self, user_input, configurations):
        oozie_site_config_map = configurations['oozie-site']
        oozie_site_config_map['oozie.service.JPAService.jdbc.password'] = (
            user_input.value)
        global_config_map = configurations['global']
        global_config_map['oozie_metastore_user_passwd'] = user_input.value


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
        super(AmbariService, self).__init__(AmbariService.get_service_id())
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
            if 'MAPREDUCE_CLIENT' not in ng.components:
                ng.components.append('MAPREDUCE_CLIENT')
