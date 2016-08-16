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

from sahara.plugins.cdh.client.services import ApiService
from sahara.plugins.cdh.client import types


class ClouderaManager(types.BaseApiResource):
    """The Cloudera Manager instance

    Provides access to CM configuration and services.
    """
    def __init__(self, resource_root):
        types.BaseApiObject.init(self, resource_root)

    def _path(self):
        return '/cm'

    def create_mgmt_service(self, service_setup_info):
        """Setup the Cloudera Management Service

        :param service_setup_info: ApiServiceSetupInfo object.
        :return: The management service instance.
        """
        return self._put("service", ApiService, data=service_setup_info)

    def get_service(self):
        """Return the Cloudera Management Services instance

        :return: An ApiService instance.
        """
        return self._get("service", ApiService)

    def hosts_start_roles(self, host_names):
        """Start all the roles on the specified hosts

        :param host_names: List of names of hosts on which to start all roles.
        :return: Information about the submitted command.
        :since: API v2
        """
        return self._cmd('hostsStartRoles', data=host_names)

    def update_config(self, config):
        """Update the CM configuration.

        :param config: Dictionary with configuration to update.
        :return: Dictionary with updated configuration.
        """
        return self._update_config("config", config)

    def import_admin_credentials(self, username, password):
        """Imports the KDC Account Manager credentials needed by Cloudera

        Manager to create kerberos principals needed by CDH services.

        :param username Username of the Account Manager. Full name including
            the Kerberos realm must be specified.
        :param password Password for the Account Manager.
        :return: Information about the submitted command.
        :since: API v7
        """
        return self._cmd('importAdminCredentials', params=dict(
            username=username, password=password))
