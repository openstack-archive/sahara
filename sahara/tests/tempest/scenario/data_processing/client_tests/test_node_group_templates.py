# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.lib.common.utils import data_utils
from tempest import test

from sahara.tests.tempest.scenario.data_processing.client_tests import base


class NodeGroupTemplateTest(base.BaseDataProcessingTest):
    def _check_create_node_group_template(self):
        template_name = data_utils.rand_name('sahara-ng-template')

        # create node group template
        resp_body = self.create_node_group_template(template_name,
                                                    **self.worker_template)
        # check that template created successfully
        self.assertEqual(template_name, resp_body.name)
        self.assertDictContainsSubset(self.worker_template,
                                      resp_body.__dict__)

        return resp_body.id, template_name

    def _check_node_group_template_list(self, template_id, template_name):
        # check for node group template in list
        template_list = self.client.node_group_templates.list()
        templates_info = [(template.id, template.name)
                          for template in template_list]
        self.assertIn((template_id, template_name), templates_info)

    def _check_node_group_template_get(self, template_id, template_name):
        # check node group template fetch by id
        template = self.client.node_group_templates.get(
            template_id)
        self.assertEqual(template_name, template.name)
        self.assertDictContainsSubset(self.worker_template,
                                      template.__dict__)

    def _check_node_group_template_update(self, template_id):
        values = {
            'name': data_utils.rand_name('updated-sahara-ng-template'),
            'description': 'description',
            'volumes_per_node': 2,
            'volumes_size': 2,
        }

        resp_body = self.client.node_group_templates.update(template_id,
                                                            **values)
        # check that template updated successfully
        self.assertDictContainsSubset(values,
                                      resp_body.__dict__)

    def _check_node_group_template_delete(self, template_id):
        # delete node group template by id
        self.client.node_group_templates.delete(template_id)

        # check that node group really deleted
        templates = self.client.node_group_templates.list()
        self.assertNotIn(template_id, [template.id for template in templates])

    @test.services('data_processing')
    def test_node_group_templates(self):
        template_id, template_name = self._check_create_node_group_template()
        self._check_node_group_template_list(template_id, template_name)
        self._check_node_group_template_get(template_id, template_name)
        self._check_node_group_template_update(template_id)
        self._check_node_group_template_delete(template_id)
