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

from sahara.plugins.cdh import abstractversionhandler as avh
from sahara.plugins.cdh import versionfactory as vf
from sahara.tests.unit import base


class VersionFactoryTestCase(base.SaharaTestCase):

    def test_get_instance(self):
        self.assertFalse(vf.VersionFactory.initialized)
        factory = vf.VersionFactory.get_instance()
        self.assertIsInstance(factory, vf.VersionFactory)
        self.assertTrue(vf.VersionFactory.initialized)

    def test_get_versions(self):
        factory = vf.VersionFactory.get_instance()
        versions = factory.get_versions()
        expected_versions = self.get_support_versions()
        self.assertEqual(expected_versions, versions)

    def test_get_version_handler(self):
        factory = vf.VersionFactory.get_instance()
        versions = self.get_support_versions()
        for version in versions:
            hander = factory.get_version_handler(version)
            self.assertIsInstance(hander, avh.AbstractVersionHandler)

    def get_support_versions(self):
        return ['5', '5.3.0', '5.4.0', '5.5.0', '5.7.0']
