# Copyright (c) 2014 Intel Corporation.
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
#
# The contents of this file are mainly copied from cm_api sources,
# released by Cloudera. Codes not used by Sahara CDH plugin are removed.
# You can find the original codes at
#
#     https://github.com/cloudera/cm_api/tree/master/python/src/cm_api
#
# To satisfy the pep8 and python3 tests, we did some changes to the codes.
# We also change some importings to use Sahara inherited classes.

from oslo_serialization import jsonutils as json
import six

from sahara.plugins.cdh.client import role_config_groups
from sahara.plugins.cdh.client import roles
from sahara.plugins.cdh.client import types

SERVICES_PATH = "/clusters/%s/services"
SERVICE_PATH = "/clusters/%s/services/%s"
ROLETYPES_CFG_KEY = 'roleTypeConfigs'


def create_service(resource_root, name, service_type,
                   cluster_name="default"):
    """Create a service

    :param resource_root: The root Resource object.
    :param name: Service name
    :param service_type: Service type
    :param cluster_name: Cluster name
    :return: An ApiService object
    """
    apiservice = ApiService(resource_root, name, service_type)
    return types.call(resource_root.post, SERVICES_PATH % (cluster_name,),
                      ApiService, True, data=[apiservice])[0]


def get_service(resource_root, name, cluster_name="default"):
    """Lookup a service by name

    :param resource_root: The root Resource object.
    :param name: Service name
    :param cluster_name: Cluster name
    :return: An ApiService object
    """
    return _get_service(resource_root, "%s/%s"
                        % (SERVICES_PATH % (cluster_name,), name))


def _get_service(resource_root, path):
    return types.call(resource_root.get, path, ApiService)


def get_all_services(resource_root, cluster_name="default", view=None):
    """Get all services

    :param resource_root: The root Resource object.
    :param cluster_name: Cluster name
    :return: A list of ApiService objects.
    """
    return types.call(resource_root.get, SERVICES_PATH % (cluster_name,),
                      ApiService, True,
                      params=(dict(view=view) if view else None))


def delete_service(resource_root, name, cluster_name="default"):
    """Delete a service by name

    :param resource_root: The root Resource object.
    :param name: Service name
    :param cluster_name: Cluster name
    :return: The deleted ApiService object
    """
    return types.call(resource_root.delete,
                      "%s/%s" % (SERVICES_PATH % (cluster_name,), name),
                      ApiService)


class ApiService(types.BaseApiResource):
    _ATTRIBUTES = {
        'name': None,
        'type': None,
        'displayName': None,
        'serviceState': types.ROAttr(),
        'healthSummary': types.ROAttr(),
        'healthChecks': types.ROAttr(),
        'clusterRef': types.ROAttr(types.ApiClusterRef),
        'configStale': types.ROAttr(),
        'configStalenessStatus': types.ROAttr(),
        'clientConfigStalenessStatus': types.ROAttr(),
        'serviceUrl': types.ROAttr(),
        'maintenanceMode': types.ROAttr(),
        'maintenanceOwners': types.ROAttr(),
    }

    def __init__(self, resource_root, name=None, type=None):
        types.BaseApiObject.init(self, resource_root, locals())

    def __str__(self):
        return ("<ApiService>: %s (cluster: %s)"
                % (self.name, self._get_cluster_name()))

    def _get_cluster_name(self):
        if hasattr(self, 'clusterRef') and self.clusterRef:
            return self.clusterRef.clusterName
        return None

    def _path(self):
        """Return the API path for this service

        This method assumes that lack of a cluster reference means that the
        object refers to the Cloudera Management Services instance.
        """
        if self._get_cluster_name():
            return SERVICE_PATH % (self._get_cluster_name(), self.name)
        else:
            return '/cm/service'

    def _role_cmd(self, cmd, roles, api_version=1):
        return self._post("roleCommands/" + cmd, types.ApiBulkCommandList,
                          data=roles, api_version=api_version)

    def _parse_svc_config(self, json_dic, view=None):
        """Parse a json-decoded ApiServiceConfig dictionary into a 2-tuple

        :param json_dic: The json dictionary with the config data.
        :param view: View to materialize.
        :return: 2-tuple (service config dictionary, role type configurations)
        """
        svc_config = types.json_to_config(json_dic, view == 'full')
        rt_configs = {}
        if ROLETYPES_CFG_KEY in json_dic:
            for rt_config in json_dic[ROLETYPES_CFG_KEY]:
                rt_configs[rt_config['roleType']] = types.json_to_config(
                    rt_config, view == 'full')

        return (svc_config, rt_configs)

    def create_yarn_job_history_dir(self):
        """Create the Yarn job history directory

        :return: Reference to submitted command.
        :since: API v6
        """
        return self._cmd('yarnCreateJobHistoryDirCommand', api_version=6)

    def get_config(self, view=None):
        """Retrieve the service's configuration

        Retrieves both the service configuration and role type configuration
        for each of the service's supported role types. The role type
        configurations are returned as a dictionary, whose keys are the
        role type name, and values are the respective configuration
        dictionaries.

        The 'summary' view contains strings as the dictionary values. The full
        view contains types.ApiConfig instances as the values.

        :param view: View to materialize ('full' or 'summary')
        :return: 2-tuple (service config dictionary, role type configurations)
        """
        path = self._path() + '/config'
        resp = self._get_resource_root().get(
            path, params=(dict(view=view) if view else None))
        return self._parse_svc_config(resp, view)

    def update_config(self, svc_config, **rt_configs):
        """Update the service's configuration

        :param svc_config: Dictionary with service configuration to update.
        :param rt_configs: Dict of role type configurations to update.
        :return: 2-tuple (service config dictionary, role type configurations)
        """
        path = self._path() + '/config'

        if svc_config:
            data = types.config_to_api_list(svc_config)
        else:
            data = {}
        if rt_configs:
            rt_list = []
            for rt, cfg in six.iteritems(rt_configs):
                rt_data = types.config_to_api_list(cfg)
                rt_data['roleType'] = rt
                rt_list.append(rt_data)
            data[ROLETYPES_CFG_KEY] = rt_list

        resp = self._get_resource_root().put(path, data=json.dumps(data))
        return self._parse_svc_config(resp)

    def create_role(self, role_name, role_type, host_id):
        """Create a role

        :param role_name: Role name
        :param role_type: Role type
        :param host_id: ID of the host to assign the role to
        :return: An ApiRole object
        """
        return roles.create_role(self._get_resource_root(), self.name,
                                 role_type, role_name, host_id,
                                 self._get_cluster_name())

    def delete_role(self, name):
        """Delete a role by name

        :param name: Role name
        :return: The deleted ApiRole object
        """
        return roles.delete_role(self._get_resource_root(), self.name, name,
                                 self._get_cluster_name())

    def get_roles_by_type(self, role_type, view=None):
        """Get all roles of a certain type in a service

        :param role_type: Role type
        :param view: View to materialize ('full' or 'summary')
        :return: A list of ApiRole objects.
        """
        return roles.get_roles_by_type(self._get_resource_root(), self.name,
                                       role_type, self._get_cluster_name(),
                                       view)

    def get_all_role_config_groups(self):
        """Get a list of role configuration groups in the service

        :return: A list of ApiRoleConfigGroup objects.
        :since: API v3
        """
        return role_config_groups.get_all_role_config_groups(
            self._get_resource_root(), self.name, self._get_cluster_name())

    def start(self):
        """Start a service

        :return: Reference to the submitted command.
        """
        return self._cmd('start')

    def stop(self):
        """Stop a service

        :return: Reference to the submitted command.
        """
        return self._cmd('stop')

    def restart(self):
        """Restart a service

        :return: Reference to the submitted command.
        """
        return self._cmd('restart')

    def get_health_summary(self):
        return getattr(self, 'healthSummary', None)

    def get_health_checks_status(self):
        return getattr(self, 'healthChecks', None)

    def start_roles(self, *role_names):
        """Start a list of roles

        :param role_names: names of the roles to start.
        :return: List of submitted commands.
        """
        return self._role_cmd('start', role_names)

    def create_hbase_root(self):
        """Create the root directory of an HBase service

        :return: Reference to the submitted command.
        """
        return self._cmd('hbaseCreateRoot')

    def create_hdfs_tmp(self):
        """Create /tmp directory in HDFS

        Create the /tmp directory in HDFS with appropriate ownership and
        permissions.

        :return: Reference to the submitted command
        :since: API v2
        """
        return self._cmd('hdfsCreateTmpDir')

    def refresh(self, *role_names):
        """Execute the "refresh" command on a set of roles

        :param role_names: Names of the roles to refresh.
        :return: Reference to the submitted command.
        """
        return self._role_cmd('refresh', role_names)

    def decommission(self, *role_names):
        """Decommission roles in a service

        :param role_names: Names of the roles to decommission.
        :return: Reference to the submitted command.
        """
        return self._cmd('decommission', data=role_names)

    def deploy_client_config(self, *role_names):
        """Deploys client configuration to the hosts where roles are running

        :param role_names: Names of the roles to decommission.
        :return: Reference to the submitted command.
        """
        return self._cmd('deployClientConfig', data=role_names)

    def format_hdfs(self, *namenodes):
        """Format NameNode instances of an HDFS service

        :param namenodes: Name of NameNode instances to format.
        :return: List of submitted commands.
        """
        return self._role_cmd('hdfsFormat', namenodes)

    def install_oozie_sharelib(self):
        """Installs the Oozie ShareLib

        Oozie must be stopped before running this command.

        :return: Reference to the submitted command.
        :since: API v3
        """
        return self._cmd('installOozieShareLib', api_version=3)

    def create_oozie_db(self):
        """Creates the Oozie Database Schema in the configured database

        :return: Reference to the submitted command.
        :since: API v2
        """
        return self._cmd('createOozieDb', api_version=2)

    def upgrade_oozie_db(self):
        """Upgrade Oozie Database schema as part of a major version upgrade

        :return: Reference to the submitted command.
        :since: API v6
        """
        return self._cmd('oozieUpgradeDb', api_version=6)

    def create_hive_metastore_tables(self):
        """Creates the Hive metastore tables in the configured database

        Will do nothing if tables already exist. Will not perform an upgrade.

        :return: Reference to the submitted command.
        :since: API v3
        """
        return self._cmd('hiveCreateMetastoreDatabaseTables', api_version=3)

    def create_hive_warehouse(self):
        """Creates the Hive warehouse directory in HDFS

        :return: Reference to the submitted command.
        :since: API v3
        """
        return self._cmd('hiveCreateHiveWarehouse')

    def create_hive_userdir(self):
        """Creates the Hive user directory in HDFS

        :return: Reference to the submitted command.
        :since: API v4
        """
        return self._cmd('hiveCreateHiveUserDir')

    def enable_nn_ha(self, active_name, standby_host_id, nameservice, jns,
                     standby_name_dir_list=None, qj_name=None,
                     standby_name=None, active_fc_name=None,
                     standby_fc_name=None, zk_service_name=None,
                     force_init_znode=True,
                     clear_existing_standby_name_dirs=True,
                     clear_existing_jn_edits_dir=True):
        """Enable High Availability (HA) with Auto-Failover for HDFS NameNode

        @param active_name: Name of Active NameNode.
        @param standby_host_id: ID of host where Standby NameNode will be
                                created.
        @param nameservice: Nameservice to be used while enabling HA.
                            Optional if Active NameNode already has this
                            config set.
        @param jns: List of Journal Nodes to be created during the command.
                    Each element of the list must be a dict containing the
                    following items:
                    - jns['jnHostId']: ID of the host where the new JournalNode
                                       will be created.
                    - jns['jnName']: Name of the JournalNode role (optional)
                    - jns['jnEditsDir']: Edits dir of the JournalNode. Can be
                                         omitted if the config is already set
                                         at RCG level.
        @param standby_name_dir_list: List of directories for the new Standby
                                      NameNode. If not provided then it will
                                      use same dirs as Active NameNode.
        @param qj_name: Name of the journal located on each JournalNodes'
                        filesystem. This can be optionally provided if the
                        config hasn't been already set for the Active NameNode.
                        If this isn't provided and Active NameNode doesn't
                        also have the config, then nameservice is used by
                        default.
        @param standby_name: Name of the Standby NameNode role to be created
                             (Optional).
        @param active_fc_name: Name of the Active Failover Controller role to
                               be created (Optional).
        @param standby_fc_name: Name of the Standby Failover Controller role to
                                be created (Optional).
        @param zk_service_name: Name of the ZooKeeper service to use for auto-
                                failover. If HDFS service already depends on a
                                ZooKeeper service then that ZooKeeper service
                                will be used for auto-failover and in that case
                                this parameter can either be omitted or should
                                be the same ZooKeeper service.
        @param force_init_znode: Indicates if the ZNode should be force
                                 initialized if it is already present. Useful
                                 while re-enabling High Availability. (Default:
                                 TRUE)
        @param clear_existing_standby_name_dirs: Indicates if the existing name
                                                 directories for Standby
                                                 NameNode should be cleared
                                                 during the workflow.
                                                 Useful while re-enabling High
                                                 Availability. (Default: TRUE)
        @param clear_existing_jn_edits_dir: Indicates if the existing edits
                                            directories for the JournalNodes
                                            for the specified nameservice
                                            should be cleared during the
                                            workflow. Useful while re-enabling
                                            High Availability. (Default: TRUE)
        @return: Reference to the submitted command.
        @since: API v6
        """
        args = dict(
            activeNnName=active_name,
            standbyNnName=standby_name,
            standbyNnHostId=standby_host_id,
            standbyNameDirList=standby_name_dir_list,
            nameservice=nameservice,
            qjName=qj_name,
            activeFcName=active_fc_name,
            standbyFcName=standby_fc_name,
            zkServiceName=zk_service_name,
            forceInitZNode=force_init_znode,
            clearExistingStandbyNameDirs=clear_existing_standby_name_dirs,
            clearExistingJnEditsDir=clear_existing_jn_edits_dir,
            jns=jns
        )
        return self._cmd('hdfsEnableNnHa', data=args, api_version=6)

    def enable_rm_ha(self, new_rm_host_id, zk_service_name=None):
        """Enable high availability for a YARN ResourceManager.

        @param new_rm_host_id: id of the host where the second ResourceManager
                               will be added.
        @param zk_service_name: Name of the ZooKeeper service to use for auto-
                                failover. If YARN service depends on a
                                ZooKeeper service then that ZooKeeper service
                                will be used for auto-failover and in that case
                                this parameter can be omitted.
        @return: Reference to the submitted command.
        @since: API v6
        """
        args = dict(
            newRmHostId=new_rm_host_id,
            zkServiceName=zk_service_name
        )
        return self._cmd('enableRmHa', data=args)


class ApiServiceSetupInfo(ApiService):
    _ATTRIBUTES = {
        'name': None,
        'type': None,
        'config': types.Attr(types.ApiConfig),
        'roles': types.Attr(roles.ApiRole),
    }

    def __init__(self, name=None, type=None,
                 config=None, roles=None):
        # The BaseApiObject expects a resource_root, which we don't care about
        resource_root = None
        # Unfortunately, the json key is called "type". So our input arg
        # needs to be called "type" as well, despite it being a python keyword.
        types.BaseApiObject.init(self, None, locals())

    def set_config(self, config):
        """Set the service configuration

        :param config: A dictionary of config key/value
        """
        if self.config is None:
            self.config = {}
        self.config.update(types.config_to_api_list(config))

    def add_role_info(self, role_name, role_type, host_id, config=None):
        """Add a role info

        The role will be created along with the service setup.

        :param role_name: Role name
        :param role_type: Role type
        :param host_id: The host where the role should run
        :param config: (Optional) A dictionary of role config values
        """
        if self.roles is None:
            self.roles = []
        api_config_list = (config is not None
                           and types.config_to_api_list(config)
                           or None)
        self.roles.append({
            'name': role_name,
            'type': role_type,
            'hostRef': {'hostId': host_id},
            'config': api_config_list})
