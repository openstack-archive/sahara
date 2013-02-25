import json
import tempfile
import unittest

from eho.server.main import make_app
import eventlet
import os


class TestApi(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.maxDiff = 10000

        app = make_app(
            TESTING=True,
            RESET_DB=True,
            STUB_DATA=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///' + self.db_path,
            SQLALCHEMY_ECHO=False
        )
        print 'Test db path: %s' % self.db_path

        self.app = app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_list_node_templates(self):
        rv = self.app.get('/v0.1/node-templates.json')
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        # clean all ids
        for idx in xrange(0, len(data.get(u'templates'))):
            del data.get(u'templates')[idx][u'id']
            del data.get(u'templates')[idx][u'node_type'][u'id']

        self.assertEquals(data, self._get_templates_stub_data())

    def test_create_node_template(self):
        rv = self.app.post('/v0.1/node-templates.json', data=json.dumps(dict(
            name='test_template',
            node_type='JT+NN',
            tenant_id='test_tenant',
            flavor_id='test_flavor',
            configs={
                'job_tracker': {
                    'heap_size': '1234'
                },
                'name_node': {
                    'heap_size': '2345'
                }
            }
        )))
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        # clean all ids
        del data[u'id']
        del data.get(u'node_type')[u'id']

        self.assertEquals(data, {
            u'job_tracker': {
                u'heap_size': u'1234'
            }, u'name': u'test_template',
            u'tenant_id': u'test_tenant',
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
        rv = self.app.get('/v0.1/clusters.json')
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        self.assertEquals(data, {
            u'clusters': []
        })

    def test_create_clusters(self):
        rv = self.app.post('/v0.1/clusters.json', data=json.dumps(dict(
            name='test-cluster',
            base_image_id='base-image-id',
            tenant_id='tenant-id',
            templates={
                'jt_nn.medium': 1,
                'tt_dn.small': 5
            }
        )))
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        cluster_id = data.pop(u'id')

        self.assertEquals(data, {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'test-cluster',
            u'tenant_id': u'tenant-id',
            u'base_image_id': u'base-image-id',
            u'node_templates': {
                u'jt_nn.medium': 1,
                u'tt_dn.small': 5
            },
            u'nodes': []
        })

        eventlet.sleep(3)

        rv = self.app.get('/v0.1/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)
        self.assertEquals(data.pop(u'id'), cluster_id)

        # clean all ids
        for idx in xrange(0, len(data.get(u'nodes'))):
            del data.get(u'nodes')[idx][u'vm_id']
            del data.get(u'nodes')[idx][u'node_template'][u'id']

        self.assertEquals(data, {
            u'status': u'Active',
            u'service_urls': {},
            u'name': u'test-cluster',
            u'tenant_id': u'tenant-id',
            u'base_image_id': u'base-image-id',
            u'node_templates': {
                u'jt_nn.medium': 1,
                u'tt_dn.small': 5
            },
            u'nodes': [
                {u'node_template': {u'name': u'jt_nn.medium'}},
                {u'node_template': {u'name': u'tt_dn.small'}},
                {u'node_template': {u'name': u'tt_dn.small'}},
                {u'node_template': {u'name': u'tt_dn.small'}},
                {u'node_template': {u'name': u'tt_dn.small'}},
                {u'node_template': {u'name': u'tt_dn.small'}}
            ]
        })

    def test_delete_node_template_for_id(self):
        rv = self.app.post('/v0.1/node-templates.json', data=json.dumps(dict(
            name='test_template_2',
            node_type='JT+NN',
            tenant_id='test_tenant_2',
            flavor_id='test_flavor_2',
            configs={
                'job_tracker': {
                    'heap_size': '1234'
                },
                'name_node': {
                    'heap_size': '2345'
                }
            }
        )))
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)
        node_template_id = data.pop(u'id')

        rv = self.app.get('/v0.1/node-templates/%s.json' % node_template_id)
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)
        del data[u'id']
        del data.get(u'node_type')[u'id']
        self.assertEquals(data, {
            u'job_tracker': {
                u'heap_size': u'1234'
            }, u'name': u'test_template_2',
            u'tenant_id': u'test_tenant_2',
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

        rv = self.app.delete('/v0.1/node-templates/%s.json' % node_template_id)
        self.assertEquals(rv.status_code, 204)

        rv = self.app.get('/v0.1/node-templates/%s.json' % node_template_id)
        self.assertEquals(rv.status_code, 500) #TODO(vrovachev):chagne sucsess code to 404

    def test_delete_cluster_for_id(self):
        rv = self.app.post('/v0.1/clusters.json', data=json.dumps(dict(
            name='test-cluster_2',
            base_image_id='base-image-id_2',
            tenant_id='tenant-id_2',
            templates={
                'jt_nn.xlarge': 1,
                'tt_dn.large': 5
            }
        )))
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)
        cluster_id = data.pop(u'id')

        rv = self.app.get('/v0.1/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)
        del data[u'id']
        self.assertEquals(data, {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'test-cluster_2',
            u'tenant_id': u'tenant-id_2',
            u'base_image_id': u'base-image-id_2',
            u'node_templates': {
                u'jt_nn.xlarge': 1,
                u'tt_dn.large': 5
            },
            u'nodes': []
        })

        rv = self.app.delete('/v0.1/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 204)

        rv = self.app.get('/v0.1/clusters/%s.json' % cluster_id)
        self.assertEquals(rv.status_code, 500) #TODO(vrovachev):chagne sucsess code to 404

    def _get_templates_stub_data(self):
        return {
            u'templates': [
                {
                    u'job_tracker': {
                        u'heap_size': u'896'
                    },
                    u'name': u'jt_nn.small',
                    u'tenant_id': u't_1',
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
                    u'tenant_id': u't_1',
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
                    u'tenant_id': u't_1',
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
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'job_tracker'
                        ],
                        u'name': u'JT'},
                    u'flavor_id': u'm1.medium'
                },
                {
                    u'name': u'nn.small',
                    u'tenant_id': u't_1',
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
                    u'tenant_id': u't_1',
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
                    u'tenant_id': u't_1',
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
                    u'tenant_id': u't_1',
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
