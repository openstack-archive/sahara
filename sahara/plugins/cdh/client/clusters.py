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

from sahara.i18n import _
from sahara.plugins.cdh.client import services
from sahara.plugins.cdh.client import types
from sahara.plugins.cdh import exceptions as ex

CLUSTERS_PATH = "/clusters"


def create_cluster(resource_root, name, version=None, fullVersion=None):
    """Create a cluster

    :param resource_root: The root Resource object.
    :param name: Cluster name
    :param version: Cluster CDH major version (eg: "CDH4")
                    - The CDH minor version will be assumed to be the
                      latest released version for CDH4, or 5.0 for CDH5.
    :param fullVersion: Cluster's full CDH version. (eg: "5.1.1")
                        - If specified, 'version' will be ignored.
                        - Since: v6
    :return: An ApiCluster object
    """
    if version is None and fullVersion is None:
        raise ex.CMApiVersionError(
            _("Either 'version' or 'fullVersion' must be specified"))
    if fullVersion is not None:
        api_version = 6
        version = None
    else:
        api_version = 1

    apicluster = ApiCluster(resource_root, name, version, fullVersion)
    return types.call(resource_root.post, CLUSTERS_PATH, ApiCluster, True,
                      data=[apicluster], api_version=api_version)[0]


def get_cluster(resource_root, name):
    """Lookup a cluster by name

    :param resource_root: The root Resource object.
    :param name: Cluster name
    :return: An ApiCluster object
    """
    return types.call(resource_root.get, "%s/%s"
                      % (CLUSTERS_PATH, name), ApiCluster)


def get_all_clusters(resource_root, view=None):
    """Get all clusters

    :param resource_root: The root Resource object.
    :return: A list of ApiCluster objects.
    """
    return types.call(resource_root.get, CLUSTERS_PATH, ApiCluster, True,
                      params=(dict(view=view) if view else None))


class ApiCluster(types.BaseApiResource):
    _ATTRIBUTES = {
        'name': None,
        'displayName': None,
        'version': None,
        'fullVersion': None,
        'maintenanceMode': types.ROAttr(),
        'maintenanceOwners': types.ROAttr(),
    }

    def __init__(self, resource_root, name=None, version=None,
                 fullVersion=None):
        types.BaseApiObject.init(self, resource_root, locals())

    def _path(self):
        return "%s/%s" % (CLUSTERS_PATH, self.name)

    def get_service_types(self):
        """Get all service types supported by this cluster

        :return: A list of service types (strings)
        """
        resp = self._get_resource_root().get(self._path() + '/serviceTypes')
        return resp[types.ApiList.LIST_KEY]

    def get_commands(self, view=None):
        """Retrieve a list of running commands for this cluster

        :param view: View to materialize ('full' or 'summary')
        :return: A list of running commands.
        """
        return self._get("commands", types.ApiCommand, True,
                         params=(dict(view=view) if view else None))

    def create_service(self, name, service_type):
        """Create a service

        :param name: Service name
        :param service_type: Service type
        :return: An ApiService object
        """
        return services.create_service(self._get_resource_root(), name,
                                       service_type, self.name)

    def get_service(self, name):
        """Lookup a service by name

        :param name: Service name
        :return: An ApiService object
        """
        return services.get_service(self._get_resource_root(),
                                    name, self.name)

    def start(self):
        """Start all services in a cluster, respecting dependencies

        :return: Reference to the submitted command.
        """
        return self._cmd('start')

    def deploy_client_config(self):
        """Deploys Service client configuration to the hosts on the cluster

        :return: Reference to the submitted command.
        :since: API v2
        """
        return self._cmd('deployClientConfig')

    def first_run(self):
        """Prepare and start services in a cluster

        Perform all the steps needed to prepare each service in a
        cluster and start the services in order.

        :return: Reference to the submitted command.
        :since: API v7
        """
        return self._cmd('firstRun', None, api_version=7)

    def remove_host(self, hostId):
        """Removes the association of the host with the cluster

        :return: A ApiHostRef of the host that was removed.
        :since: API v3
        """
        return self._delete("hosts/" + hostId, types.ApiHostRef, api_version=3)

    def get_service_health_status(self):
        """Lookup a service health status by name

        :return: A dict with cluster health status
        """
        health_dict = {}
        cl_services = services.get_all_services(self._get_resource_root(),
                                                cluster_name=self.name)
        for curr in cl_services:
            health_dict[curr.name] = {
                'summary': curr.get_health_summary(),
                'checks': curr.get_health_checks_status()}
        return health_dict
