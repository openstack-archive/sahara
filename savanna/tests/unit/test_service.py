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

from mock import patch
import unittest

import savanna.service.api as api


class TestServiceLayer(unittest.TestCase):
    ## Node Template ops:

    @patch('savanna.storage.storage.get_node_template')
    def test_get_node_template(self, m):
        m.return_value = api.Resource("node_template", {
            "id": "template-id",
            "name": "jt_nn.small",
            "node_type": api.Resource("node_type", {
                "name": "JT+NN",
                "processes": [
                    api.Resource("process", {"name": "job_tracker"}),
                    api.Resource("process", {"name": "name_node"})
                ]
            }),
            "flavor_id": "flavor-id",
            "node_template_configs": [
                api.Resource("conf", {
                    "node_process_property": api.Resource("prop", {
                        "name": "heap_size",
                        "node_process": api.Resource("process", {
                            "name": "job_tracker"
                        })
                    }),
                    "value": "1234"
                }),
                api.Resource("conf", {
                    "node_process_property": api.Resource("prop", {
                        "name": "heap_size",
                        "node_process": api.Resource("process", {
                            "name": "name_node"
                        })
                    }),
                    "value": "5678"
                })
            ]
        })

        nt = api.get_node_template(id='template-id')
        self.assertEqual(nt, api.Resource("node_template", {
            'id': 'template-id',
            'name': 'jt_nn.small',
            'node_type': {
                'processes': ['job_tracker', 'name_node'],
                'name': 'JT+NN'
            },
            'flavor_id': 'flavor-id',
            'job_tracker': {'heap_size': '1234'},
            'name_node': {'heap_size': '5678'}
        }))
        m.assert_called_once_with(id='template-id')

    @patch('savanna.storage.storage.get_node_templates')
    def test_get_node_templates(self, m):
        # '_node_template' tested in 'test_get_node_template'
        api.get_node_templates(node_type='JT+NN')
        m.assert_called_once_with(node_type='JT+NN')

    @patch('savanna.service.api.get_node_template')
    @patch('savanna.storage.storage.create_node_template')
    @patch('savanna.storage.storage.get_node_type')
    def test_create_node_template(self, get_n_type, create_tmpl, get_tmpl):
        get_n_type.return_value = api.Resource(
            "node_type", {"id": "node-type-1"})
        create_tmpl.return_value = api.Resource(
            "node-template", {"id": "tmpl-1"})

        api.create_node_template(
            {
                "node_template": {
                    "name": "nt-1",
                    "node_type": "JT+NN",
                    "flavor_id": "flavor-1"
                }
            }, {"X-Tenant-Id": "tenant-01"})

        get_n_type.assert_called_once_with(name="JT+NN")
        create_tmpl.assert_called_once_with("nt-1", "node-type-1",
                                            "flavor-1", {})
        get_tmpl.assert_called_once_with(id="tmpl-1")

    @patch('savanna.storage.storage.terminate_node_template')
    def test_terminate_node_template(self, m):
        api.terminate_node_template(node_type='JT+NN')
        m.assert_called_once_with(node_type='JT+NN')

    ## Cluster ops:

    @patch('savanna.storage.storage.get_cluster')
    def test_get_cluster(self, m):
        m.return_value = api.Resource("cluster", {
            "id": "cluster-id",
            "name": "cluster-name",
            "base_image_id": "image-id",
            "status": "Active",
            "nodes": [
                api.Resource("node", {
                    "vm_id": "vm-1",
                    "node_template": api.Resource("node_template", {
                        "id": "jt_nn.small-id",
                        "name": "jt_nn.small"
                    })
                }),
                api.Resource("node", {
                    "vm_id": "vm-2",
                    "node_template": api.Resource("node_template", {
                        "id": "tt_dn.small-id",
                        "name": "tt_dn.small"
                    })
                }),
                api.Resource("node", {
                    "vm_id": "vm-3",
                    "node_template": api.Resource("node_template", {
                        "id": "tt_dn.small-id",
                        "name": "tt_dn.small"
                    })
                })
            ],
            "node_counts": [
                api.Resource("node_count", {
                    "node_template": api.Resource("node_template", {
                        "name": "jt_nn.small"
                    }),
                    "count": "1"
                }),
                api.Resource("node_count", {
                    "node_template": api.Resource("node_template", {
                        "name": "tt_dn.small"
                    }),
                    "count": "2"
                })
            ],
            "service_urls": [
                api.Resource("service_url", {
                    "name": "job_tracker",
                    "url": "some-url"
                }),
                api.Resource("service_url", {
                    "name": "name_node",
                    "url": "some-url-2"
                })
            ]
        })

        cluster = api.get_cluster(id="cluster-id")
        self.assertEqual(cluster, api.Resource("cluster", {
            'id': 'cluster-id',
            'name': 'cluster-name',
            'base_image_id': "image-id",
            'status': 'Active',
            'node_templates': {'jt_nn.small': '1', 'tt_dn.small': '2'},
            'nodes': [
                {
                    'node_template': {
                        'id': 'jt_nn.small-id', 'name': 'jt_nn.small'
                    }, 'vm_id': 'vm-1'
                },
                {
                    'node_template': {
                        'id': 'tt_dn.small-id', 'name': 'tt_dn.small'
                    }, 'vm_id': 'vm-2'
                },
                {
                    'node_template': {
                        'id': 'tt_dn.small-id', 'name': 'tt_dn.small'
                    }, 'vm_id': 'vm-3'
                }
            ],
            'service_urls': {
                'name_node': 'some-url-2',
                'job_tracker': 'some-url'
            }
        }))
        m.assert_called_once_with(id="cluster-id")

    @patch('savanna.storage.storage.get_clusters')
    def test_get_clusters(self, m):
        # '_clusters' tested in 'test_get_clusters'
        api.get_clusters(id="cluster-id")
        m.assert_called_once_with(id="cluster-id")

    @patch('eventlet.spawn')
    @patch('savanna.service.api.get_cluster')
    @patch('savanna.storage.storage.create_cluster')
    def test_create_cluster(self, create_c, get_c, spawn):
        create_c.return_value = api.Resource("cluster", {
            "id": "cluster-1"
        })

        api.create_cluster(
            {
                "cluster": {
                    "name": "cluster-1",
                    "base_image_id": "image-1",
                    "node_templates": {
                        "jt_nn.small": "1",
                        "tt_dn.small": "10"
                    }
                }
            }, {"X-Tenant-Id": "tenant-01"})

        create_c.assert_called_once_with("cluster-1", "image-1", "tenant-01", {
            "jt_nn.small": "1",
            "tt_dn.small": "10"
        })
        get_c.assert_called_once_with(id="cluster-1")
        spawn.assert_called_once_with(api._cluster_creation_job,
                                      {"X-Tenant-Id": "tenant-01"},
                                      "cluster-1")

    @patch('eventlet.spawn')
    @patch('savanna.storage.storage.update_cluster_status')
    def test_terminate_cluster(self, update_status, spawn):
        update_status.return_value = api.Resource("cluster", {
            "id": "cluster-id"
        })

        api.terminate_cluster({"X-Tenant-Id": "tenant-01"}, id="cluster-id")

        update_status.assert_called_once_with('Stopping', id="cluster-id")
        spawn.assert_called_once_with(api._cluster_termination_job,
                                      {"X-Tenant-Id": "tenant-01"},
                                      "cluster-id")
