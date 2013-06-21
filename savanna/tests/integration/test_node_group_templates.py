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

import telnetlib

from savanna.tests.integration import base


class NodeGroupTemplatesCrudTest(base.ITestCase):

    def setUp(self):
        super(NodeGroupTemplatesCrudTest, self).setUp()
        telnetlib.Telnet(self.host, self.port)

    def test_crud_ngt_nn(self):
        body_nn = self.make_node_group_template('master_nn', 'qa probe', 'NN')
        self.crud_object(body_nn, self.url_ngt)

    def test_crud_ngt_jt(self):
        body_jt = self.make_node_group_template('master_jt', 'qa probe', 'JT')
        self.crud_object(body_jt, self.url_ngt)

    def test_crud_ngt_tt(self):
        body_tt = self.make_node_group_template('worker_tt', 'qa probe', 'TT')
        self.crud_object(body_tt, self.url_ngt)

    def test_crud_ngt_dn(self):
        body_dn = self.make_node_group_template('worker_dn', 'qa probe', 'DN')
        self.crud_object(body_dn, self.url_ngt)

    def test_crud_ngt_nn_jt(self):
        body_nn_jt = self.make_node_group_template('master_nn_jt', 'qa probe',
                                                   'JT+NN')
        self.crud_object(body_nn_jt, self.url_ngt)

    def test_crud_ngt_tt_dn(self):
        body_tt_dn = self.make_node_group_template('worker_dn_tt', 'qa probe',
                                                   'TT+DN')
        self.crud_object(body_tt_dn, self.url_ngt)

    def test_crud_ngt_nnttdn(self):
        body_tt_dn = self.make_node_group_template('nn_dn_tt', 'qa probe',
                                                   'NN+TT+DN')
        self.crud_object(body_tt_dn, self.url_ngt)

    def test_crud_ngt_jtttdn(self):
        body_tt_dn = self.make_node_group_template('jt_dn_tt', 'qa probe',
                                                   'JT+TT+DN')
        self.crud_object(body_tt_dn, self.url_ngt)
