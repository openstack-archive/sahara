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

from savanna.tests.integration.db import ITestCase
from telnetlib import Telnet


class ITestNodeTemplateApi(ITestCase):

    def setUp(self):
        super(ITestNodeTemplateApi, self).setUp()
        Telnet(self.host, self.port)

    def test_crud_nt_jtnn(self):
        nt_jtnn = self.make_nt('jtnn', 'JT+NN', 1024, 1024)
        get_jtnn = self._get_body_nt('jtnn', 'JT+NN', 1024, 1024)

        self._crud_object(nt_jtnn, get_jtnn, self.url_nt)

    def test_crud_nt_ttdn(self):
        nt_ttdn = self.make_nt('ttdn', 'TT+DN', 1024, 1024)
        get_ttdn = self._get_body_nt('ttdn', 'TT+DN', 1024, 1024)

        self._crud_object(nt_ttdn, get_ttdn, self.url_nt)

    def test_crud_nt_nn(self):
        nt_nn = self.make_nt('nn', 'NN', 1024, 1024)
        get_nn = self._get_body_nt('nn', 'NN', 1024, 1024)

        self._crud_object(nt_nn, get_nn, self.url_nt)

    def test_crud_nt_jt(self):
        nt_jt = self.make_nt('jt', 'JT', 1024, 1024)
        get_jt = self._get_body_nt('jt', 'JT', 1024, 1024)

        self._crud_object(nt_jt, get_jt, self.url_nt)
