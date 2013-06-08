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

import unittest2

from savanna import context as ctx
import savanna.db.models as m
from savanna.tests.unit.db.models import base as models_test_base


SAMPLE_CONFIGS = {
    'a': 'av',
    'b': 123,
    'c': [1, '2', u"3"]
}


class TemplatesModelTest(models_test_base.ModelTestCase):
    def testCreateNodeGroupTemplate(self):
        session = ctx.current().session
        with session.begin():
            ngt = m.NodeGroupTemplate('ngt-1', 't-1', 'f-1', 'p-1', 'hv-1',
                                      ['np-1', 'np-2'], SAMPLE_CONFIGS, "d")
            session.add(ngt)

        res = session.query(m.NodeGroupTemplate).filter_by().first()

        self.assertIsValidModelObject(res)
        self.assertEquals(['np-1', 'np-2'], res.node_processes)
        self.assertEquals(SAMPLE_CONFIGS, res.node_configs)

        res_dict = self.get_clean_dict(res)

        self.assertEqual(res_dict, {
            'description': 'd',
            'flavor_id': 'f-1',
            'hadoop_version': 'hv-1',
            'name': 'ngt-1',
            'node_configs': SAMPLE_CONFIGS,
            'node_processes': ['np-1', 'np-2'],
            'plugin_name': 'p-1'
        })

    def testCreateClusterTemplate(self):
        session = ctx.current().session
        with session.begin():
            c = m.ClusterTemplate('c-1', 't-1', 'p-1', 'hv-1', SAMPLE_CONFIGS,
                                  "d")
            session.add(c)

        res = session.query(m.ClusterTemplate).filter_by().first()
        self.assertIsValidModelObject(res)
        self.assertEqual(SAMPLE_CONFIGS, res.cluster_configs)

        res_dict = self.get_clean_dict(res)

        self.assertEqual(res_dict, {
            'cluster_configs': SAMPLE_CONFIGS,
            'description': 'd',
            'hadoop_version': 'hv-1',
            'name': 'c-1',
            'plugin_name': 'p-1',
            'node_groups': []
        })

    def testCreateClusterTemplateWithNodeGroupTemplates(self):
        session = ctx.current().session
        with session.begin():
            ct = m.ClusterTemplate('ct', 't-1', 'p-1', 'hv-1')
            session.add(ct)

            ngts = []
            for i in xrange(0, 3):
                ngt = m.NodeGroupTemplate('ngt-%s' % i, 't-1', 'f-1', 'p-1',
                                          'hv-1', ['np-1', 'np-2'])
                session.add(ngt)
                session.flush()
                rel = ct.add_node_group_template({
                    'node_group_template_id': ngt.id,
                    'name': 'group-%s' % i,
                    'count': 5 + i
                })
                session.add(rel)
                ngts.append(ngt)

        with session.begin():
            res = session.query(m.ClusterTemplate).filter_by().first()
            self.assertIsValidModelObject(res)

            self.assertEqual(len(res.node_group_templates), 3)
            self.assertEqual(set(t.name for t in res.node_group_templates),
                             set('ngt-%s' % i for i in xrange(0, 3)))


class NestedTemplateTest(unittest2.TestCase):
    @unittest2.skip('template to obj conversions are not fully implemented')
    def test_nested_templates(self):
        ct = m.ClusterTemplate('ct', 't-1', 'p-1', 'hv-1')
        ct.cluster_configs = {
            "service:map-reduce": {
                "ct": 0,
                "nt": 0,
                "c": 0,
                "n": 0
            },
            "service:hdfs": {
                "ct": 0,
                "nt": 0,
                "c": 0,
                "n": 0
            }
        }

        c = m.Cluster('c-1', 't-1', 'p-1', 'hv-1')
        c.cluster_configs = {
            "service:map-reduce": {
                "c": 1,
                "nt": 1,
                "n": 1
            },
            "service:hdfs": {
                "c": 1,
                "nt": 1,
                "n": 1
            }
        }
        c.base_cluster_template = ct

        ngt = m.NodeGroupTemplate("ngt", "t-1", "f-1", "p-1",
                                  "h-1", ["tt", "dn"])
        ngt.node_configs = {
            "service:map-reduce": {
                "nt": 2,
                "n": 2
            },
            "service:hdfs": {
                "nt": 2,
                "n": 2
            }
        }

        ng = m.NodeGroup("ng", "f-i", ["tt", "dn"], 1)
        ng.cluster = c
        ng.base_node_group_template = ngt
        ng.node_configs = {
            "service:map-reduce": {
                "n": 3
            },
            "service:hdfs": {
                "n": 3
            }
        }

        self.assertEqual(ng.configuration["service:map-reduce"]["ct"], 0)
        self.assertEqual(ng.configuration["service:map-reduce"]["c"], 1)
        self.assertEqual(ng.configuration["service:map-reduce"]["nt"], 2)
        self.assertEqual(ng.configuration["service:map-reduce"]["n"], 3)
