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

import testtools

from sahara import main
from sahara.plugins import base as pb


class BasePluginsSupportTest(testtools.TestCase):

    def setUp(self):
        super(BasePluginsSupportTest, self).setUp()
        main.CONF.set_override('plugins', ['fake', 'cdh', 'spark'])
        pb.setup_plugins()

    def test_plugins_loaded(self):
        plugins = [p.name for p in pb.PLUGINS.get_plugins()]
        self.assertIn('fake', plugins)
