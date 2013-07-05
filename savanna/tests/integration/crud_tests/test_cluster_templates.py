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


class ClusterTemplatesCrudTest(base.ITestCase):

    def setUp(self):
        super(ClusterTemplatesCrudTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

        self.create_node_group_templates()

    def test_crud_cl_tmpl_nnjt_dntt(self):
        """This test checks cluster template creation with
        configuration | JT + NN | TT + DN |.
        """
        node_list = {self.id_jt_nn: 1, self.id_tt_dn: 2}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-1', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nn_jt_dn_tt(self):
        """This test checks cluster template creation with
        configuration | JT | NN | TT | DN |.
        """
        node_list = {self.id_nn: 1, self.id_jt: 1, self.id_tt: 5,
                     self.id_dn: 5}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-2', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nn_jt_dntt(self):
        """This test checks cluster template creation with
        configuration | JT | NN | TT + DN |.
        """
        node_list = {self.id_jt: 1, self.id_nn: 1, self.id_tt_dn: 7}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-3', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nn(self):
        """This test checks cluster template creation with
        configuration | NN |.
        """
        node_list = {self.id_nn: 1}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-4', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nn_dn(self):
        """This test checks cluster template creation with
        configuration | NN | DN |.
        """
        node_list = {self.id_nn: 1, self.id_dn: 7}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-5', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nn_jt_dn(self):
        """This test checks cluster template creation with
        configuration | JT | NN | DN |.
        """
        node_list = {self.id_nn: 1, self.id_jt: 1, self.id_dn: 7}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-6', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_jt_nnttdn(self):
        """This test checks cluster template creation with
        configuration | JT | NN + TT + DN |.
        """
        node_list = {self.id_jt: 1, self.id_nn_tt_dn: 1}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-7', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nn_jtttdn(self):
        """This test checks cluster template creation with
        configuration | NN | JT + TT + DN |.
        """
        node_list = {self.id_nn: 1, self.id_jt_tt_dn: 1}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-8', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_nnttdn_jt_ttdn(self):
        """This test checks cluster template creation with
        configuration | JT | NN + TT + DN | TT + DN |.
        """
        node_list = {self.id_nn_tt_dn: 1, self.id_jt: 1, self.id_tt_dn: 7}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-9', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def test_crud_cl_tmpl_jtttdn_nn_ttdn(self):
        """This test checks cluster template creation with
        configuration | JT + TT + DN | NN | TT + DN |.
        """
        node_list = {self.id_jt_tt_dn: 1, self.id_nn: 1, self.id_tt_dn: 7}
        cl_tmpl_body = self.make_cluster_template('cl-tmpl-10', node_list)
        self.crud_object(cl_tmpl_body, self.url_cl_tmpl)

    def tearDown(self):
        self.delete_node_group_templates()
