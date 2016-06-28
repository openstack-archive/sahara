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

from tempest import config
from tempest.lib.common.utils import data_utils

from sahara.tests.tempest.scenario.data_processing.client_tests import base


TEMPEST_CONF = config.CONF


class ClusterTemplateTest(base.BaseDataProcessingTest):
    def _check_create_cluster_template(self):
        ng_template_name = data_utils.rand_name('sahara-ng-template')
        ng_template = self.create_node_group_template(ng_template_name,
                                                      **self.worker_template)

        full_cluster_template = self.cluster_template.copy()
        full_cluster_template['node_groups'] = [
            {
                'name': 'master-node',
                'flavor_id': TEMPEST_CONF.compute.flavor_ref,
                'node_processes': ['namenode'],
                'count': 1
            },
            {
                'name': 'worker-node',
                'node_group_template_id': ng_template.id,
                'count': 3
            }
        ]

        template_name = data_utils.rand_name('sahara-cluster-template')

        # create cluster template
        resp_body = self.create_cluster_template(template_name,
                                                 **full_cluster_template)

        # check that template created successfully
        self.assertEqual(template_name, resp_body.name)
        self.assertDictContainsSubset(self.cluster_template,
                                      resp_body.__dict__)

        return resp_body.id, template_name

    def _check_cluster_template_list(self, template_id, template_name):
        # check for cluster template in list
        template_list = self.client.cluster_templates.list()
        templates_info = [(template.id, template.name)
                          for template in template_list]
        self.assertIn((template_id, template_name), templates_info)

    def _check_cluster_template_get(self, template_id, template_name):
        # check cluster template fetch by id
        template = self.client.cluster_templates.get(
            template_id)
        self.assertEqual(template_name, template.name)
        self.assertDictContainsSubset(self.cluster_template, template.__dict__)

    def _check_cluster_template_update(self, template_id):
        values = {
            'name': data_utils.rand_name('updated-sahara-ct'),
            'description': 'description',
        }

        # check updating of cluster template
        template = self.client.cluster_templates.update(
            template_id, **values)
        self.assertDictContainsSubset(values, template.__dict__)

    def _check_cluster_template_delete(self, template_id):
        # delete cluster template by id
        self.client.cluster_templates.delete(
            template_id)

        # check that cluster template really deleted
        templates = self.client.cluster_templates.list()
        self.assertNotIn(template_id, [template.id for template in templates])

    def test_cluster_templates(self):
        template_id, template_name = self._check_create_cluster_template()
        self._check_cluster_template_list(template_id, template_name)
        self._check_cluster_template_get(template_id, template_name)
        self._check_cluster_template_update(template_id)
        self._check_cluster_template_delete(template_id)
