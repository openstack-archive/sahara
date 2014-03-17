# Copyright (c) 2013 Intel Corporation
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

from sahara.plugins.general import exceptions as g_ex
from sahara.plugins.intel import plugin as p
from sahara.plugins.intel.v2_5_1 import config_helper as c_helper
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu


class TestIDHPlugin251(base.SaharaWithDbTestCase):

    def test_get_configs(self):
        plugin = p.IDHProvider()
        configs = plugin.get_configs('2.5.1')

        self.assertIn(c_helper.IDH_REPO_URL, configs)
        self.assertIn(c_helper.IDH_TARBALL_URL, configs)
        self.assertIn(c_helper.OS_REPO_URL, configs)

    def test_validate(self):
        plugin = p.IDHProvider()

        ng_mng = tu.make_ng_dict('mng', 'f1', ['manager'], 1)
        ng_nn = tu.make_ng_dict('nn', 'f1', ['namenode'], 1)
        ng_jt = tu.make_ng_dict('jt', 'f1', ['jobtracker'], 1)
        ng_dn = tu.make_ng_dict('dn', 'f1', ['datanode'], 2)
        ng_tt = tu.make_ng_dict('tt', 'f1', ['tasktracker'], 2)

        cl = tu.create_cluster('cl1', 't1', 'intel', '2.5.1',
                               [ng_nn] + [ng_dn])
        self.assertRaises(g_ex.InvalidComponentCountException,
                          plugin.validate, cl)

        cl = tu.create_cluster('cl1', 't1', 'intel', '2.5.1', [ng_mng])
        self.assertRaises(g_ex.InvalidComponentCountException,
                          plugin.validate, cl)

        cl = tu.create_cluster('cl1', 't1', 'intel', '2.5.1',
                               [ng_mng] + [ng_nn] * 2)
        self.assertRaises(g_ex.InvalidComponentCountException,
                          plugin.validate, cl)

        cl = tu.create_cluster('cl1', 't1', 'intel', '2.5.1',
                               [ng_mng] + [ng_nn] + [ng_tt])
        self.assertRaises(g_ex.RequiredServiceMissingException,
                          plugin.validate, cl)

        cl = tu.create_cluster('cl1', 't1', 'intel', '2.5.1',
                               [ng_mng] + [ng_nn] + [ng_jt] * 2 + [ng_tt])
        self.assertRaises(g_ex.InvalidComponentCountException,
                          plugin.validate, cl)
