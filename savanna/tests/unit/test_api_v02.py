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

import eventlet
import json
import unittest

from savanna.openstack.common import log as logging
from savanna.tests.unit.base import SavannaTestCase

LOG = logging.getLogger(__name__)


class TestApi(SavannaTestCase):

    def test_list_node_templates(self):
        rv = self.app.get('/v0.2/some-tenant-id/node-templates.json')
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        # clean all ids
        for idx in xrange(0, len(data.get(u'node_templates'))):
            del data.get(u'node_templates')[idx][u'id']

        self.assertEquals(data, _get_templates_stub_data())

    def test_create_node_template(self):
        rv = self.app.post('/v0.2/some-tenant-id/node-templates.json',
                           data=json.dumps(dict(
                               node_template=dict(
                                   name='test-template',
                                   node_type='JT+NN',
                                   flavor_id='test_flavor',
                                   job_tracker={
                                       'heap_size': '1234'
                                   },
                                   name_node={
                                       'heap_size': '2345'
                                   }
                               ))))
        self.assertEquals(rv.status_code, 202)
        data = json.loads(rv.data)

        data = data['node_template']

        # clean all ids
        del data[u'id']

        self.assertEquals(data, {
            u'job_tracker': {
                u'heap_size': u'1234'
            }, u'name': u'test-template',
            u'node_type': {
                u'processes': [
                    u'job_tracker', u'name_node'
                ],
                u'name': u'JT+NN'
            },
            u'flavor_id': u'test_flavor',
            u'name_node': {
                u'heap_size': u'2345'
            }
        })

    def test_list_clusters(self):
        rv = self.app.get('/v0.2/some-tenant-id/clusters.json')
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        self.assertEquals(data, {
            u'clusters': []
        })

    def test_create_clusters(self):
        rv = self.app.post('/v0.2/some-tenant-id/clusters.json',
                           data=json.dumps(dict(
                               cluster=dict(
                                   name='test-cluster',
                                   base_image_id='base-image-id',
                                   node_templates={
                                       'jt_nn.medium': 1,
                                       'tt_dn.small': 5
                                   }
                               ))))
        self.assertEquals(rv.status_code, 202)
        data = json.loads(rv.data)

        data = data['cluster']

        cluster_id = data.pop(u'id')

        self.assertEquals(data, {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'test-cluster',
            u'base_image_id': u'base-image-id',
            u'node_templates': {
                u'jt_nn.medium': 1,
                u'tt_dn.small': 5
            },
            u'nodes': []
        })

        eventlet.sleep(4)

        rv = self.app.get('/v0.2/some-tenant-id/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        data = data['cluster']

        self.assertEquals(data.pop(u'id'), cluster_id)

        # clean all ids
        for idx in xrange(0, len(data.get(u'nodes'))):
            del data.get(u'nodes')[idx][u'vm_id']
            del data.get(u'nodes')[idx][u'node_template'][u'id']

        nodes = data.pop(u'nodes')

        self.assertEquals(data, {
            u'status': u'Active',
            u'service_urls': {},
            u'name': u'test-cluster',
            u'base_image_id': u'base-image-id',
            u'node_templates': {
                u'jt_nn.medium': 1,
                u'tt_dn.small': 5
            }
        })

        self.assertEquals(_sorted_nodes(nodes), _sorted_nodes([
            {u'node_template': {u'name': u'tt_dn.small'}},
            {u'node_template': {u'name': u'tt_dn.small'}},
            {u'node_template': {u'name': u'tt_dn.small'}},
            {u'node_template': {u'name': u'tt_dn.small'}},
            {u'node_template': {u'name': u'tt_dn.small'}},
            {u'node_template': {u'name': u'jt_nn.medium'}}
        ]))

    def test_delete_node_template(self):
        rv = self.app.post('/v0.2/some-tenant-id/node-templates.json',
                           data=json.dumps(dict(
                               node_template=dict(
                                   name='test-template-2',
                                   node_type='JT+NN',
                                   flavor_id='test_flavor_2',
                                   job_tracker={
                                       'heap_size': '1234'
                                   },
                                   name_node={
                                       'heap_size': '2345'
                                   }
                               ))))
        self.assertEquals(rv.status_code, 202)
        data = json.loads(rv.data)

        data = data['node_template']

        node_template_id = data.pop(u'id')

        rv = self.app.get(
            '/v0.2/some-tenant-id/node-templates/%s.json' % node_template_id)
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        data = data['node_template']

        # clean all ids
        del data[u'id']

        self.assertEquals(data, {
            u'job_tracker': {
                u'heap_size': u'1234'
            }, u'name': u'test-template-2',
            u'node_type': {
                u'processes': [
                    u'job_tracker', u'name_node'
                ],
                u'name': u'JT+NN'
            },
            u'flavor_id': u'test_flavor_2',
            u'name_node': {
                u'heap_size': u'2345'
            }
        })

        rv = self.app.delete(
            '/v0.2/some-tenant-id/node-templates/%s.json' % node_template_id)
        self.assertEquals(rv.status_code, 204)

        rv = self.app.get(
            '/v0.2/some-tenant-id/node-templates/%s.json' % node_template_id)

        # todo(vrovachev): change success code to 404
        self.assertEquals(rv.status_code, 500)

    def test_delete_cluster(self):
        rv = self.app.post('/v0.2/some-tenant-id/clusters.json',
                           data=json.dumps(dict(
                               cluster=dict(
                                   name='test-cluster-2',
                                   base_image_id='base-image-id_2',
                                   node_templates={
                                       'jt_nn.medium': 1,
                                       'tt_dn.small': 5
                                   }
                               ))))
        self.assertEquals(rv.status_code, 202)
        data = json.loads(rv.data)

        data = data['cluster']

        cluster_id = data.pop(u'id')

        rv = self.app.get('/v0.2/some-tenant-id/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        data = data['cluster']

        # delete all ids
        del data[u'id']

        self.assertEquals(data, {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'test-cluster-2',
            u'base_image_id': u'base-image-id_2',
            u'node_templates': {
                u'jt_nn.medium': 1,
                u'tt_dn.small': 5
            },
            u'nodes': []
        })

        rv = self.app.delete(
            '/v0.2/some-tenant-id/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 204)

        eventlet.sleep(1)

        rv = self.app.get('/v0.2/some-tenant-id/clusters/%s.json' % cluster_id)

        # todo(vrovachev): change success code to 404
        self.assertEquals(rv.status_code, 500)


def _sorted_nodes(nodes):
    return sorted(nodes, key=lambda elem: elem[u'node_template'][u'name'])


def _get_templates_stub_data():
    return {
        u'node_templates': [
            {
                u'job_tracker': {
                    u'heap_size': u'896'
                },
                u'name': u'jt_nn.small',
                u'node_type': {
                    u'processes': [
                        u'job_tracker', u'name_node'
                    ],
                    u'name': u'JT+NN'
                },
                u'flavor_id': u'm1.small',
                u'name_node': {
                    u'heap_size': u'896'
                }
            },
            {
                u'job_tracker': {
                    u'heap_size': u'1792'
                },
                u'name': u'jt_nn.medium',
                u'node_type': {
                    u'processes': [
                        u'job_tracker', u'name_node'
                    ], u'name': u'JT+NN'
                },
                u'flavor_id': u'm1.medium',
                u'name_node': {
                    u'heap_size': u'1792'
                }
            },
            {
                u'name': u'tt_dn.small',
                u'task_tracker': {
                    u'heap_size': u'896',
                    u'mapred.child.java.opts': None,
                    u'mapred.tasktracker.map.tasks.maximum': None,
                    u'mapred.tasktracker.reduce.tasks.maximum': None
                },
                u'data_node': {
                    u'heap_size': u'896'
                },
                u'node_type': {
                    u'processes': [
                        u'task_tracker', u'data_node'
                    ],
                    u'name': u'TT+DN'
                },
                u'flavor_id': u'm1.small'
            },
            {
                u'name': u'tt_dn.medium',
                u'task_tracker': {
                    u'heap_size': u'1792',
                    u'mapred.child.java.opts': None,
                    u'mapred.tasktracker.map.tasks.maximum': None,
                    u'mapred.tasktracker.reduce.tasks.maximum': None
                },
                u'data_node': {
                    u'heap_size': u'1792'
                },
                u'node_type': {
                    u'processes': [
                        u'task_tracker', u'data_node'
                    ],
                    u'name': u'TT+DN'
                },
                u'flavor_id': u'm1.medium'
            }
        ]
    }


if __name__ == '__main__':
    unittest.main()
