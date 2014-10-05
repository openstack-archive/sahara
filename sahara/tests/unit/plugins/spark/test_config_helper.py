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

from sahara.plugins.spark import config_helper as c_helper
from sahara.tests.unit import base as test_base


class ConfigHelperUtilsTest(test_base.SaharaTestCase):
    def test_make_hadoop_path(self):
        storage_paths = ['/mnt/one', '/mnt/two']
        paths = c_helper.make_hadoop_path(storage_paths, '/spam')
        expected = ['/mnt/one/spam', '/mnt/two/spam']
        self.assertEqual(expected, paths)
