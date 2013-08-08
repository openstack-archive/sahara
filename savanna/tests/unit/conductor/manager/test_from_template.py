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

import copy

from savanna import context
import savanna.tests.unit.conductor.manager.base as test_base
from savanna.tests.unit.conductor.manager import test_clusters
from savanna.tests.unit.conductor.manager import test_templates


CORRECT_CONF = {
    u'service_1': {u'config_2': u'value_2', u'config_1': u'value_1'},
    u'service_2': {u'config_1': u'value_1'}
}


class ClusterTest(test_base.ConductorApiTestCase):
    def test_cluster_create_from_templates(self):
        ctx = context.ctx()

        # create node_group_template
        ng_tmpl = test_templates.SAMPLE_NGT.copy()
        ng_tmpl['volumes_size'] = '10'
        ng_tmpl['node_configs']['service_1']['config_2'] = 'value_2'
        ng_tmpl = self.api.node_group_template_create(ctx, ng_tmpl)

        # create cluster template
        cl_tmpl = self.api.cluster_template_create(ctx,
                                                   test_templates.SAMPLE_CLT)

        # create cluster
        cluster_val = copy.deepcopy(test_clusters.SAMPLE_CLUSTER)
        cluster_val['cluster_template_id'] = cl_tmpl['id']
        cluster_val['node_groups'][0]['node_group_template_id'] = ng_tmpl['id']
        cluster = self.api.cluster_create(ctx, cluster_val)
        self.assertEqual(CORRECT_CONF, cluster['cluster_configs'])

        for node_group in cluster['node_groups']:
            if node_group['name'] == 'ng_1':
                self.assertEqual(['p1', 'p2'], node_group['node_processes'])
                self.assertEqual(10, node_group['volumes_size'])
                self.assertEqual(CORRECT_CONF, node_group['node_configs'])

    def test_node_group_add_from_template(self):
        ctx = context.ctx()

        # create cluster
        cluster_val = test_clusters.SAMPLE_CLUSTER.copy()
        cluster = self.api.cluster_create(ctx, cluster_val)

        # create node_group_template
        ng_tmpl = test_templates.SAMPLE_NGT.copy()
        ng_tmpl['volumes_size'] = '10'
        ng_tmpl['node_configs']['service_1']['config_2'] = 'value_2'
        ng_tmpl = self.api.node_group_template_create(ctx, ng_tmpl)

        # add node group to cluster
        ng = test_clusters.SAMPLE_CLUSTER['node_groups'][0].copy()
        ng['node_group_template_id'] = ng_tmpl['id']
        ng['count'] = 5
        ng['name'] = 'ng_3'
        ng = self.api.node_group_add(ctx, cluster['id'], ng)

        # refetch cluster
        cluster = self.api.cluster_get(ctx, cluster['id'])

        for node_group in cluster['node_groups']:
            if node_group['name'] == 'ng_3':
                self.assertEqual(['p1', 'p2'], node_group['node_processes'])
                self.assertEqual(10, node_group['volumes_size'])
                self.assertEqual(CORRECT_CONF, node_group['node_configs'])
                self.assertEqual(5, node_group['count'])
