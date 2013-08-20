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
import savanna.tests.integration.configs.parameters.common_parameters as param


@base.enable_test(param.ENABLE_CLUSTER_CL_TEMPLATE_CRUD_TESTS)
class ClusterFromClusterTemplateCrudTest(base.ITestCase):

    def setUp(self):
        super(ClusterFromClusterTemplateCrudTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

        self.create_node_group_templates()

    def crud_cluster_cl_template(self, node_list):
        cl_template_body = self.make_cluster_template('cl-template', node_list)

        try:
            cl_template_id = self.get_object_id(
                'cluster_template', self.post_object(self.url_cl_tmpl,
                                                     cl_template_body, 202))
        except Exception as e:
            self.fail('Failure while cluster template creation: ' + str(e))

        cluster_body = self.make_cl_body_cluster_template(cl_template_id)

        try:
            self.crud_object(cluster_body, self.url_cluster)

        except Exception as e:
            self.fail('CRUD test has failed: ' + str(e))

        finally:
            self.del_object(self.url_cl_tmpl_with_slash, cl_template_id, 204)

    def test_cluster_nnttdn_jt(self):
        """This test check cluster creation with topology | NN + TT + DN | JT |
        via cluster template.
        """
        node_list = {self.id_nn_tt_dn: 1, self.id_jt: 1}
        self.crud_cluster_cl_template(node_list)

    def test_cluster_jtttdn_nn(self):
        """This test check cluster creation with topology | JT + TT + DN | NN |
        via cluster template.
        """
        node_list = {self.id_jt_tt_dn: 1, self.id_nn: 1}
        self.crud_cluster_cl_template(node_list)

    def tearDown(self):
        self.delete_node_group_templates()
