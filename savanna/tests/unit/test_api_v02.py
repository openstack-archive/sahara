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

import json
import tempfile
import unittest
import uuid
import os

import eventlet
from oslo.config import cfg

from savanna.main import make_app
from savanna.service import api
from savanna.storage.defaults import setup_defaults
from savanna.storage.models import Node, NodeTemplate
from savanna.storage.db import DB
import savanna.main
from savanna.utils import scheduler
from savanna.utils.openstack import nova
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def _stub_vm_creation_job(template_id):
    template = NodeTemplate.query.filter_by(id=template_id).first()
    eventlet.sleep(2)
    return 'ip-address', uuid.uuid4().hex, template.id


def _stub_launch_cluster(headers, cluster):
    LOG.debug('stub launch_cluster called with %s, %s', headers, cluster)
    pile = eventlet.GreenPile(scheduler.POOL)

    for elem in cluster.node_counts:
        node_count = elem.count
        for _ in xrange(0, node_count):
            pile.spawn(_stub_vm_creation_job, elem.node_template_id)

    for (ip, vm_id, elem) in pile:
        DB.session.add(Node(vm_id, cluster.id, elem))
        LOG.debug("VM '%s/%s/%s' created", ip, vm_id, elem)


def _stub_stop_cluster(headers, cluster):
    LOG.debug("stub stop_cluster called with %s, %s", headers, cluster)


def _stub_auth_token(*args, **kwargs):
    LOG.debug('stub token filter called with %s, %s', args, kwargs)

    def _filter(app):
        def _handler(env, start_response):
            env['HTTP_X_TENANT_ID'] = 'tenant-id-1'
            return app(env, start_response)

        return _handler

    return _filter


def _stub_auth_valid(*args, **kwargs):
    LOG.debug('stub token validation called with %s, %s', args, kwargs)

    def _filter(app):
        def _handler(env, start_response):
            return app(env, start_response)

        return _handler

    return _filter


def _stub_get_flavors(headers):
    LOG.debug('Stub get_flavors called with %s', headers)
    return [u'test_flavor', u'test_flavor_2']


def _stub_get_images(headers):
    LOG.debug('Stub get_images called with %s', headers)
    return [u'base-image-id', u'base-image-id_2']


CONF = cfg.CONF
CONF.import_opt('debug', 'savanna.openstack.common.log')
CONF.import_opt('allow_cluster_ops', 'savanna.config')
CONF.import_opt('database_uri', 'savanna.storage.db', group='sqlalchemy')
CONF.import_opt('echo', 'savanna.storage.db', group='sqlalchemy')


class TestApi(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.maxDiff = 10000

        # override configs
        CONF.set_override('debug', True)
        CONF.set_override('allow_cluster_ops', True)  # stub process
        CONF.set_override('database_uri', 'sqlite:///' + self.db_path,
                          group='sqlalchemy')
        CONF.set_override('echo', False, group='sqlalchemy')

        # store functions that will be stubbed
        self._prev_auth_token = savanna.main.auth_token
        self._prev_auth_valid = savanna.main.auth_valid
        self._prev_cluster_launch = api.cluster_ops.launch_cluster
        self._prev_cluster_stop = api.cluster_ops.stop_cluster
        self._prev_get_flavors = nova.get_flavors
        self._prev_get_images = nova.get_images

        # stub functions
        savanna.main.auth_token = _stub_auth_token
        savanna.main.auth_valid = _stub_auth_valid
        api.cluster_ops.launch_cluster = _stub_launch_cluster
        api.cluster_ops.stop_cluster = _stub_stop_cluster
        nova.get_flavors = _stub_get_flavors
        nova.get_images = _stub_get_images

        app = make_app()

        DB.drop_all()
        DB.create_all()
        setup_defaults(True, True)

        LOG.debug('Test db path: %s', self.db_path)
        LOG.debug('Test app.config: %s', app.config)

        self.app = app.test_client()

    def tearDown(self):
        # unstub functions
        savanna.main.auth_token = self._prev_auth_token
        savanna.main.auth_valid = self._prev_auth_valid
        api.cluster_ops.launch_cluster = self._prev_cluster_launch
        api.cluster_ops.stop_cluster = self._prev_cluster_stop
        nova.get_flavors = self._prev_get_flavors
        nova.get_images = self._prev_get_images

        os.close(self.db_fd)
        os.unlink(self.db_path)

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
                u'job_tracker': {
                    u'heap_size': u'1792'
                },
                u'name': u'jt.small',
                u'node_type': {
                    u'processes': [
                        u'job_tracker'
                    ],
                    u'name': u'JT'
                },
                u'flavor_id': u'm1.small'
            },
            {
                u'job_tracker': {
                    u'heap_size': u'3712'
                },
                u'name': u'jt.medium',
                u'node_type': {
                    u'processes': [
                        u'job_tracker'
                    ],
                    u'name': u'JT'},
                u'flavor_id': u'm1.medium'
            },
            {
                u'name': u'nn.small',
                u'node_type': {
                    u'processes': [
                        u'name_node'
                    ],
                    u'name': u'NN'
                },
                u'flavor_id': u'm1.small',
                u'name_node': {
                    u'heap_size': u'1792'
                }
            },
            {
                u'name': u'nn.medium',
                u'node_type': {
                    u'processes': [
                        u'name_node'
                    ],
                    u'name': u'NN'
                },
                u'flavor_id': u'm1.medium',
                u'name_node': {
                    u'heap_size': u'3712'
                }
            },
            {
                u'name': u'tt_dn.small',
                u'task_tracker': {
                    u'heap_size': u'896'
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
                    u'heap_size': u'1792'
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
