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

from sahara.plugins.cdh.client import types

ROLE_CONFIG_GROUPS_PATH = "/clusters/%s/services/%s/roleConfigGroups"
CM_ROLE_CONFIG_GROUPS_PATH = "/cm/service/roleConfigGroups"


def _get_role_config_groups_path(cluster_name, service_name):
    if cluster_name:
        return ROLE_CONFIG_GROUPS_PATH % (cluster_name, service_name)
    else:
        return CM_ROLE_CONFIG_GROUPS_PATH


def _get_role_config_group_path(cluster_name, service_name, name):
    path = _get_role_config_groups_path(cluster_name, service_name)
    return "%s/%s" % (path, name)


def get_all_role_config_groups(resource_root, service_name,
                               cluster_name="default"):
    """Get all role config groups in the specified service

    :param resource_root: The root Resource object.
    :param service_name: Service name.
    :param cluster_name: Cluster name.
    :return: A list of ApiRoleConfigGroup objects.
    :since: API v3
    """
    return types.call(resource_root.get,
                      _get_role_config_groups_path(cluster_name, service_name),
                      ApiRoleConfigGroup, True, api_version=3)


class ApiRoleConfigGroup(types.BaseApiResource):
    _ATTRIBUTES = {
        'name': None,
        'displayName': None,
        'roleType': None,
        'config': types.Attr(types.ApiConfig),
        'base': types.ROAttr(),
        'serviceRef': types.ROAttr(types.ApiServiceRef),
    }

    def __init__(self, resource_root, name=None, displayName=None,
                 roleType=None, config=None):
        types.BaseApiObject.init(self, resource_root, locals())

    def __str__(self):
        return ("<ApiRoleConfigGroup>: %s (cluster: %s; service: %s)"
                % (self.name, self.serviceRef.clusterName,
                   self.serviceRef.serviceName))

    def _api_version(self):
        return 3

    def _path(self):
        return _get_role_config_group_path(self.serviceRef.clusterName,
                                           self.serviceRef.serviceName,
                                           self.name)

    def get_config(self, view=None):
        """Retrieve the group's configuration

        The 'summary' view contains strings as the dictionary values. The full
        view contains types.ApiConfig instances as the values.

        :param view: View to materialize ('full' or 'summary').
        :return: Dictionary with configuration data.
        """
        path = self._path() + '/config'
        resp = self._get_resource_root().get(
            path, params=(dict(view=view) if view else None))
        return types.json_to_config(resp, view == 'full')

    def update_config(self, config):
        """Update the group's configuration

        :param config: Dictionary with configuration to update.
        :return: Dictionary with updated configuration.
        """
        path = self._path() + '/config'
        resp = self._get_resource_root().put(
            path, data=types.config_to_json(config))
        return types.json_to_config(resp)
