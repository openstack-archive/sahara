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
# released by Cloudrea. Codes not used by Sahara CDH plugin are removed.
# You can find the original codes at
#
#     https://github.com/cloudera/cm_api/tree/master/python/src/cm_api
#
# To satisfy the pep8 and python3 tests, we did some changes to the codes.
# We also change some importings to use Sahara inherited classes.

from sahara.plugins.cdh.client import types

ROLES_PATH = "/clusters/%s/services/%s/roles"
CM_ROLES_PATH = "/cm/service/roles"


def _get_roles_path(cluster_name, service_name):
    if cluster_name:
        return ROLES_PATH % (cluster_name, service_name)
    else:
        return CM_ROLES_PATH


def _get_role_path(cluster_name, service_name, role_name):
    path = _get_roles_path(cluster_name, service_name)
    return "%s/%s" % (path, role_name)


def create_role(resource_root,
                service_name,
                role_type,
                role_name,
                host_id,
                cluster_name="default"):
    """Create a role

    :param resource_root: The root Resource object.
    :param service_name: Service name
    :param role_type: Role type
    :param role_name: Role name
    :param cluster_name: Cluster name
    :return: An ApiRole object
    """
    apirole = ApiRole(resource_root, role_name, role_type,
                      types.ApiHostRef(resource_root, host_id))
    return types.call(resource_root.post,
                      _get_roles_path(cluster_name, service_name),
                      ApiRole, True, data=[apirole])[0]


def get_role(resource_root, service_name, name, cluster_name="default"):
    """Lookup a role by name

    :param resource_root: The root Resource object.
    :param service_name: Service name
    :param name: Role name
    :param cluster_name: Cluster name
    :return: An ApiRole object
    """
    return _get_role(resource_root, _get_role_path(cluster_name,
                     service_name, name))


def _get_role(resource_root, path):
    return types.call(resource_root.get, path, ApiRole)


def get_all_roles(resource_root, service_name, cluster_name="default",
                  view=None):
    """Get all roles

    :param resource_root: The root Resource object.
    :param service_name: Service name
    :param cluster_name: Cluster name
    :return: A list of ApiRole objects.
    """
    return types.call(resource_root.get,
                      _get_roles_path(cluster_name, service_name), ApiRole,
                      True, params=(dict(view=view) if view else None))


def get_roles_by_type(resource_root, service_name, role_type,
                      cluster_name="default", view=None):
    """Get all roles of a certain type in a service

    :param resource_root: The root Resource object.
    :param service_name: Service name
    :param role_type: Role type
    :param cluster_name: Cluster name
    :return: A list of ApiRole objects.
    """
    roles = get_all_roles(resource_root, service_name, cluster_name, view)
    return [r for r in roles if r.type == role_type]


def delete_role(resource_root, service_name, name, cluster_name="default"):
    """Delete a role by name

    :param resource_root: The root Resource object.
    :param service_name: Service name
    :param name: Role name
    :param cluster_name: Cluster name
    :return: The deleted ApiRole object
    """
    return types.call(resource_root.delete,
                      _get_role_path(cluster_name, service_name, name),
                      ApiRole)


class ApiRole(types.BaseApiResource):
    _ATTRIBUTES = {
        'name': None,
        'type': None,
        'hostRef': types.Attr(types.ApiHostRef),
        'roleState': types.ROAttr(),
        'healthSummary': types.ROAttr(),
        'healthChecks': types.ROAttr(),
        'serviceRef': types.ROAttr(types.ApiServiceRef),
        'configStale': types.ROAttr(),
        'configStalenessStatus': types.ROAttr(),
        'haStatus': types.ROAttr(),
        'roleUrl': types.ROAttr(),
        'commissionState': types.ROAttr(),
        'maintenanceMode': types.ROAttr(),
        'maintenanceOwners': types.ROAttr(),
        'roleConfigGroupRef': types.ROAttr(types.ApiRoleConfigGroupRef),
        'zooKeeperServerMode': types.ROAttr(),
    }

    def __init__(self, resource_root, name=None, type=None, hostRef=None):
        types.BaseApiObject.init(self, resource_root, locals())

    def __str__(self):
        return ("<ApiRole>: %s (cluster: %s; service: %s)"
                % (self.name, self.serviceRef.clusterName,
                   self.serviceRef.serviceName))

    def _path(self):
        return _get_role_path(self.serviceRef.clusterName,
                              self.serviceRef.serviceName,
                              self.name)

    def _get_log(self, log):
        path = "%s/logs/%s" % (self._path(), log)
        return self._get_resource_root().get(path)

    def get_commands(self, view=None):
        """Retrieve a list of running commands for this role

        :param view: View to materialize ('full' or 'summary')
        :return: A list of running commands.
        """
        return self._get("commands", types.ApiCommand, True,
                         params=(dict(view=view) if view else None))

    def get_config(self, view=None):
        """Retrieve the role's configuration

        The 'summary' view contains strings as the dictionary values. The full
        view contains types.ApiConfig instances as the values.

        :param view: View to materialize ('full' or 'summary')
        :return: Dictionary with configuration data.
        """
        return self._get_config("config", view)

    def update_config(self, config):
        """Update the role's configuration

        :param config: Dictionary with configuration to update.
        :return: Dictionary with updated configuration.
        """
        return self._update_config("config", config)
