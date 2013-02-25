import json
import tempfile
import unittest

from eho.server.main import make_app
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

        self.assertEquals(data, {
            u'templates': [
                {
                    u'job_tracker': {
                        u'heap_size': u'3072'
                    },
                    u'name': u'jt_nn.large',
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'job_tracker',
                            u'name_node'
                        ],
                        u'name': u'JT+NN'
                    },
                    u'flavor_id': u'm1.large',
                    u'name_node': {
                        u'heap_size': u'3072'
                    }
                },
                {
                    u'job_tracker': {
                        u'heap_size': u'6144'
                    },
                    u'name': u'jt_nn.xlarge',
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'job_tracker',
                            u'name_node'
                        ],
                        u'name': u'JT+NN'
                    },
                    u'flavor_id': u'm1.xlarge',
                    u'name_node': {
                        u'heap_size': u'6144'
                    }
                },
                {
                    u'job_tracker': {
                        u'heap_size': u'3072'
                    },
                    u'name': u'jt.large',
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'job_tracker'
                        ],
                        u'name': u'JT'
                    },
                    u'flavor_id': u'm1.large'
                },
                {
                    u'job_tracker': {
                        u'heap_size': u'6144'
                    },
                    u'name': u'jt.xlarge',
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'job_tracker'
                        ],
                        u'name': u'JT'
                    },
                    u'flavor_id': u'm1.xlarge'
                },
                {
                    u'name': u'nn.large',
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'name_node'
                        ],
                        u'name': u'NN'
                    },
                    u'flavor_id': u'm1.large',
                    u'name_node': {
                        u'heap_size': u'3072'
                    }
                },
                {
                    u'name': u'nn.xlarge',
                    u'tenant_id': u't_1',
                    u'node_type': {
                        u'processes': [
                            u'name_node'
                        ],
                        u'name': u'NN'
                    }, u'flavor_id': u'm1.xlarge',
                    u'name_node': {
                        u'heap_size': u'6144'
                    }
                },
                {
                    u'name': u'tt_dn.medium',
                    u'task_tracker': {
                        u'heap_size': u'1536'
                    },
                    u'tenant_id': u't_1',
                    u'data_node': {
                        u'heap_size': u'1536'
                    },
                    u'node_type': {
                        u'processes': [
                            u'task_tracker',
                            u'data_node'
                        ],
                        u'name': u'TT+DN'
                    },
                    u'flavor_id': u'm1.medium'
                },
                {
                    u'name': u'tt_dn.large',
                    u'task_tracker': {
                        u'heap_size': u'3072'
                    },
                    u'tenant_id': u't_1',
                    u'data_node': {
                        u'heap_size': u'3072'
                    },
                    u'node_type': {
                        u'processes': [
                            u'task_tracker',
                            u'data_node'
                        ],
                        u'name': u'TT+DN'
                    },
                    u'flavor_id': u'm1.large'
                },
                {
                    u'name': u'tt_dn.xlarge',
                    u'task_tracker': {
                        u'heap_size': u'6144'
                    },
                    u'tenant_id': u't_1',
                    u'data_node': {
                        u'heap_size': u'6144'
                    },
                    u'node_type': {
                        u'processes': [
                            u'task_tracker',
                            u'data_node'
                        ],
                        u'name': u'TT+DN'},
                    u'flavor_id': u'm1.xlarge'
                }]})

    def test_list_clusters(self):
        rv = self.app.get('/v0.1/clusters.json')
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)

        self.assertEquals(data, {
            u'clusters': []
        })


if __name__ == '__main__':
    unittest.main()
