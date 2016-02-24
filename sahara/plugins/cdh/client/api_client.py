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

from sahara.plugins.cdh.client import clusters
from sahara.plugins.cdh.client import cms
from sahara.plugins.cdh.client import hosts
from sahara.plugins.cdh.client import http_client
from sahara.plugins.cdh.client import resource
from sahara.plugins.cdh.client import users

API_AUTH_REALM = "Cloudera Manager"
API_CURRENT_VERSION = 8


class ApiResource(resource.Resource):
    """Top-level API Resource

    Resource object that provides methods for managing the top-level API
    resources.
    """

    def __init__(self, server_host, server_port=None,
                 username="admin", password="admin",
                 use_tls=False, version=API_CURRENT_VERSION):
        """Creates a Resource object that provides API endpoints.

        :param server_host: The hostname of the Cloudera Manager server.
        :param server_port: The port of the server. Defaults to 7180 (http) or
            7183 (https).
        :param username: Login name.
        :param password: Login password.
        :param use_tls: Whether to use tls (https).
        :param version: API version.
        :return: Resource object referring to the root.
        """
        self._version = version
        protocol = "https" if use_tls else "http"
        if server_port is None:
            server_port = 7183 if use_tls else 7180
        base_url = ("%s://%s:%s/api/v%s"
                    % (protocol, server_host, server_port, version))

        client = http_client.HttpClient(base_url)
        client.set_basic_auth(username, password, API_AUTH_REALM)
        client.set_headers({"Content-Type": "application/json"})
        resource.Resource.__init__(self, client)

    @property
    def version(self):
        """Returns the API version (integer) being used."""
        return self._version

    def get_cloudera_manager(self):
        """Returns a Cloudera Manager object."""
        return cms.ClouderaManager(self)

    def create_cluster(self, name, version=None, fullVersion=None):
        """Create a new cluster

        :param name: Cluster name.
        :param version: Cluster major CDH version, e.g. 'CDH5'. Ignored if
            fullVersion is specified.
        :param fullVersion: Complete CDH version, e.g. '5.1.2'. Overrides major
            version if both specified.
        :return: The created cluster.
        """
        return clusters.create_cluster(self, name, version, fullVersion)

    def get_all_clusters(self, view=None):
        """Retrieve a list of all clusters

        :param view: View to materialize ('full' or 'summary').
        :return: A list of ApiCluster objects.
        """
        return clusters.get_all_clusters(self, view)

    def get_cluster(self, name):
        """Look up a cluster by name

        :param name: Cluster name.
        :return: An ApiCluster object.
        """
        return clusters.get_cluster(self, name)

    def delete_host(self, host_id):
        """Delete a host by id

        :param host_id: Host id
        :return: The deleted ApiHost object
        """
        return hosts.delete_host(self, host_id)

    def get_all_hosts(self, view=None):
        """Get all hosts

        :param view: View to materialize ('full' or 'summary').
        :return: A list of ApiHost objects.
        """
        return hosts.get_all_hosts(self, view)

    def get_user(self, username):
        """Look up a user by username.

        @param username: Username to look up
        @return: An ApiUser object
        """
        return users.get_user(self, username)

    def update_user(self, user):
        """Update a user detail profile.

        @param user: An ApiUser object
        @return: An ApiUser object
        """
        return users.update_user(self, user)

    def get_service_health_status(self, cluster):
        """Get clusters service health status

        :param cluster: Cluster name.
        :return: A dict with cluster health status
        """
        cluster = clusters.get_cluster(self, cluster)
        return cluster.get_service_health_status()
