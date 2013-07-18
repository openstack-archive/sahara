# Copyright (c) 2013 Mirantis Inc.
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

import pkg_resources as pkg
import unittest2

from savanna.plugins.vanilla import scaling as sc
from savanna import version


class ProvisioningPluginBaseTest(unittest2.TestCase):
    def test_result_for_3_nodes(self):
        ins = open(pkg.resource_filename(
            version.version_info.package, "tests/unit/resources/"
                                          "dfs_admin_3_nodes.txt"), "r")
        big_string = ins.read()

        exp1 = {"Name": "10.155.0.94:50010", "Decommission Status": "Normal"}
        exp2 = {"Name": "10.155.0.90:50010", "Last contact": "Tue Jul 16 12:"
                "00:07 UTC 2013"}
        exp3 = {"Configured Capacity": "10568916992 (9.84 GB)", "DFS "
                "Remaining%": "93.42%"}
        expected = [exp1, exp2, exp3]
        res = sc.parse_dfs_report(big_string)
        self.assertItemsEqual(expected, res)

    def test_result_for_0_nodes(self):
        ins = open(pkg.resource_filename(
            version.version_info.package, "tests/unit/resources/"
                                          "dfs_admin_0_nodes.txt"), "r")
        big_string = ins.read()
        res = sc.parse_dfs_report(big_string)
        self.assertEqual(0, len(res))

    def test_result_for_1_node(self):
        ins = open(pkg.resource_filename(
            version.version_info.package, "tests/unit/resources/"
                                          "dfs_admin_1_nodes.txt"), "r")
        big_string = ins.read()
        exp = {"Name": "10.155.0.94:50010", "Decommission Status": "Normal"}
        res = sc.parse_dfs_report(big_string)
        self.assertIn(exp, res)
