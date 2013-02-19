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
            SQLALCHEMY_DATABASE_URI='sqlite:///' + self.db_path
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
        del data.get(u'templates')[0][u'id']
        del data.get(u'templates')[0][u'node_type'][u'id']
        self.assertEquals(data, {
            u'templates': [
                {
                    u'flavor_id': u'f_1',
                    # u'id': u'<random id>',
                    u'job_tracker': {
                        u'heap_size': u'1024'
                    },
                    u'name': u'tmpl_1',
                    u'name_node': {
                        u'heap_size': u'512'
                    },
                    u'node_type': {
                        # u'id': u'<random id>',
                        u'name': u'jt+nn',
                        u'processes': [
                            u'job_tracker',
                            u'name_node'
                        ]
                    },
                    u'tenant_id': u't_1'
                }
            ]
        })

    def test_list_clusters(self):
        rv = self.app.get('/v0.1/clusters.json')
        self.assertEquals(rv.status_code, 200)
        data = json.loads(rv.data)
        del data.get(u'clusters')[0][u'id']
        self.assertEquals(data, {
            u'clusters': [
                {u'base_image_id': u'base_image_1',
                 # u'id': u'random id',
                 u'name': u'cluster_1',
                 u'node_templates': {u'tmpl_1': 100},
                 u'nodes': [],
                 u'service_urls': {},
                 u'status': None,
                 u'tenant_id': u'tenant_1'}
            ]
        })


if __name__ == '__main__':
    unittest.main()
