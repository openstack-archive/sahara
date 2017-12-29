# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from sahara.plugins.mapr.domain import distro
import sahara.tests.unit.base as b


class TestDistro(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestDistro, self).__init__(*args, **kwds)
        self.install_cmd = 'foo_bar'
        self.separator = '-'
        self.distro = distro.Distro('foo', 'foo', self.install_cmd,
                                    self.separator)

    def test_create_install_cmd(self):
        pkgs = [('foo',), ('bar', 'version')]
        cmd = self.distro.create_install_cmd(pkgs)
        self.assertIsNotNone(cmd)
        parts = cmd.split(' ')
        self.assertEqual(self.install_cmd, parts[0])
        self.assertEqual('foo', parts[1])
        self.assertEqual('bar', parts[2].split(self.separator)[0])
        self.assertEqual('version*', parts[2].split(self.separator)[1])
