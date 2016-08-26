# Copyright (c) 2015 Mirantis Inc.
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

import mock

from sahara.plugins.ambari import requests_helper
from sahara.tests.unit import base


class RequestsHelperTestCase(base.SaharaTestCase):

    def setUp(self):
        super(RequestsHelperTestCase, self).setUp()
        self.i1 = mock.MagicMock()
        self.i1.fqdn.return_value = "i1"

        self.i2 = mock.MagicMock()
        self.i2.fqdn.return_value = "i2"

    def test_build_datanode_decommission_request(self):
        c_name = "c1"
        instances = [self.i1, self.i2]

        res = requests_helper.build_datanode_decommission_request(c_name,
                                                                  instances)
        self.assertEqual("i1,i2",
                         res["RequestInfo"]["parameters"]["excluded_hosts"])
        self.assertEqual("c1",
                         res["RequestInfo"]["operation_level"]["cluster_name"])

    def test_build_nodemanager_decommission_request(self):
        c_name = "c1"
        instances = [self.i1, self.i2]

        res = requests_helper.build_nodemanager_decommission_request(
            c_name, instances)

        self.assertEqual("i1,i2",
                         res["RequestInfo"]["parameters"]["excluded_hosts"])
        self.assertEqual("c1",
                         res["RequestInfo"]["operation_level"]["cluster_name"])

    def test_build_namenode_restart_request(self):
        res = requests_helper.build_namenode_restart_request("c1", self.i1)

        self.assertEqual("i1", res["Requests/resource_filters"][0]["hosts"])
        self.assertEqual("c1",
                         res["RequestInfo"]["operation_level"]["cluster_name"])

    def test_build_resourcemanager_restart_request(self):
        res = requests_helper.build_resourcemanager_restart_request("c1",
                                                                    self.i1)

        self.assertEqual("i1", res["Requests/resource_filters"][0]["hosts"])
        self.assertEqual("c1",
                         res["RequestInfo"]["operation_level"]["cluster_name"])

    def test_build_stop_service_request(self):
        res = requests_helper.build_stop_service_request("HDFS")
        expected = {
            "RequestInfo": {
                "context": "Restart HDFS service (stopping)",
            },
            "Body": {
                "ServiceInfo": {
                    "state": "INSTALLED"
                }
            }
        }
        self.assertEqual(res, expected)

    def test_build_start_service_request(self):
        res = requests_helper.build_start_service_request("HDFS")
        expected = {
            "RequestInfo": {
                "context": "Restart HDFS service (starting)",
            },
            "Body": {
                "ServiceInfo": {
                    "state": "STARTED"
                }
            }
        }
        self.assertEqual(res, expected)
