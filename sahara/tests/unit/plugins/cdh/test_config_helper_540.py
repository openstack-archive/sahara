# Copyright (c) 2014 Mirantis Inc.
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

from sahara.plugins.cdh.v5_4_0 import config_helper as c_h
from sahara.tests.unit import base
from sahara.tests.unit.plugins.cdh import utils as ctu


class ConfigHelperTestCase(base.SaharaTestCase):
    def setUp(self):
        super(ConfigHelperTestCase, self).setUp()
        self.cluster = ctu.get_fake_cluster(cluster_configs={})

    def test_is_swift_enabled(self):
        self.assertTrue(c_h.is_swift_enabled(self.cluster))

        cluster = ctu.get_fake_cluster(
            cluster_configs={'general': {c_h.ENABLE_SWIFT.name: False}})
        self.assertFalse(c_h.is_swift_enabled(cluster))

    def test_get_swift_lib_url(self):
        self.assertEqual(c_h.DEFAULT_SWIFT_LIB_URL,
                         c_h.get_swift_lib_url(self.cluster))

        cluster = ctu.get_fake_cluster(
            cluster_configs={'general': {c_h.SWIFT_LIB_URL.name: 'spam'}})
        self.assertEqual('spam', c_h.get_swift_lib_url(cluster))

    def test_get_required_anti_affinity(self):
        self.assertTrue(c_h.get_required_anti_affinity(self.cluster))

        cluster = ctu.get_fake_cluster(
            cluster_configs={'general': {
                c_h.REQUIRE_ANTI_AFFINITY.name: False}})
        self.assertFalse(c_h.get_required_anti_affinity(cluster))
