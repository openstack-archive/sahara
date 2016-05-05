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

from sahara.plugins.ambari import plugin
from sahara.tests.unit import base as test_base


class TestPlugin(test_base.SaharaTestCase):
    def setUp(self):
        self.plugin = plugin.AmbariPluginProvider()
        super(TestPlugin, self).setUp()

    def test_job_types(self):
        self.assertEqual({
            '2.3': [
                'Hive', 'Java', 'MapReduce', 'MapReduce.Streaming',
                'Pig', 'Shell', 'Spark'],
            '2.4': [
                'Hive', 'Java', 'MapReduce', 'MapReduce.Streaming',
                'Pig', 'Shell', 'Spark']
        }, self.plugin.get_edp_job_types())

        self.assertEqual({
            '2.3': [
                'Hive', 'Java', 'MapReduce', 'MapReduce.Streaming',
                'Pig', 'Shell', 'Spark'],
        }, self.plugin.get_edp_job_types(versions=['2.3']))

        self.assertEqual({
            '2.4': [
                'Hive', 'Java', 'MapReduce', 'MapReduce.Streaming',
                'Pig', 'Shell', 'Spark'],
        }, self.plugin.get_edp_job_types(versions=['2.4']))
