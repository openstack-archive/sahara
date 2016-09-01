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

import datetime

from sahara.plugins.cdh.client import types

HOSTS_PATH = "/hosts"


def get_all_hosts(resource_root, view=None):
    """Get all hosts

    :param resource_root: The root Resource object.
    :return: A list of ApiHost objects.
    """
    return types.call(resource_root.get, HOSTS_PATH, ApiHost, True,
                      params=(dict(view=view) if view else None))


def delete_host(resource_root, host_id):
    """Delete a host by id

    :param resource_root: The root Resource object.
    :param host_id: Host id
    :return: The deleted ApiHost object
    """
    return types.call(resource_root.delete, "%s/%s"
                      % (HOSTS_PATH, host_id), ApiHost)


class ApiHost(types.BaseApiResource):
    _ATTRIBUTES = {
        'hostId': None,
        'hostname': None,
        'ipAddress': None,
        'rackId': None,
        'status': types.ROAttr(),
        'lastHeartbeat': types.ROAttr(datetime.datetime),
        'roleRefs': types.ROAttr(types.ApiRoleRef),
        'healthSummary': types.ROAttr(),
        'healthChecks': types.ROAttr(),
        'hostUrl': types.ROAttr(),
        'commissionState': types.ROAttr(),
        'maintenanceMode': types.ROAttr(),
        'maintenanceOwners': types.ROAttr(),
        'numCores': types.ROAttr(),
        'totalPhysMemBytes': types.ROAttr(),
    }

    def __init__(self, resource_root, hostId=None, hostname=None,
                 ipAddress=None, rackId=None):
        types.BaseApiObject.init(self, resource_root, locals())

    def __str__(self):
        return "<ApiHost>: %s (%s)" % (self.hostId, self.ipAddress)

    def _path(self):
        return HOSTS_PATH + '/' + self.hostId

    def put_host(self):
        """Update this resource

        note (mionkin):Currently, according to Cloudera docs,
                       only updating the rackId is supported.
                       All other fields of the host will be ignored.
        :return: The updated object.
        """
        return self._put('', ApiHost, data=self)
