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

import testtools

from sahara.conductor import resource as r
from sahara import exceptions as ex
from sahara.swift import swift_helper
from sahara.utils import edp


SAMPLE_DICT = {
    'first': [1, 2],
    'second': {'a': 1, 'b': 2}
}

SAMPLE_NESTED_LISTS_DICT = {
    'a': [[{'b': 123}]]
}

SAMPLE_CLUSTER_DICT = {
    'name': 'test-cluster',
    'cluster_configs': {
        'general': {
            'some_overridden_config': 'somevalue'
        }
    },
    'node_groups': [
        {
            'name': 'master',
            'id': 'some_id'
        },
        {
            'id': 'some_id',
            'name': 'worker',
            'node_processes': ['tasktracker', 'datanode'],
            'node_configs': {},
            'instances': [
                {
                    'name': 'test-cluster-001',
                    'ip': '1.1.1.1'
                }
            ]
        }
    ]
}

SAMPLE_JOB_BINARY_DICT = {
    "created_at": "2014-02-14 16:26:08.895897",
    "description": "a job",
    "extra": {
        "password": "password",
        "user": "user"
    },
    "id": "c0caf119-f380-4fab-a46e-0f28ebd23b5c",
    "name": "bob",
    "tenant_id": "6b859fb8d1f44e8eafdfb91f21309b5f",
    "updated_at": "null",
    "url": "swift://bob.sahara/job"
}

SAMPLE_JOB_BINARY_DICT2 = copy.copy(SAMPLE_JOB_BINARY_DICT)
SAMPLE_JOB_BINARY_DICT2["name"] = "bill"
SAMPLE_JOB_BINARY_DICT2["id"] = "c0caf119-1111-2222-a46e-0f28ebd23b5c"
SAMPLE_JOB_BINARY_DICT2["url"] = "swift://bill.sahara/job"

SAMPLE_JOB_DICT = {
    "tenant_id": "test_tenant",
    "name": "job_test",
    "description": "test_desc",
    "type": "Pig",
    "mains": [SAMPLE_JOB_BINARY_DICT],
    "libs": [SAMPLE_JOB_BINARY_DICT2]
}

SAMPLE_DATA_SOURCE = {
    'name': 'input',
    'description': 'some input',
    'type': 'swift',
    'url': 'swift://tmckay.sahara',
    'credentials': {
        'username': 'me',
        'password': 'password'
    }
}

SAMPLE_JOB_EXECUTION = {
    "cluster_id": "7ed1c016-a8a3-4209-9931-6e80f58eea80",
    "created_at": "2014-02-14 17:46:56.631209",
    "extra": {},
    "id": "1b0b1874-a261-4d1f-971a-a2cebadeba6c",
    "info": {
        "actions": [{"conf": "some stuff"},
                    {"conf": "more stuff"}],
        "status": edp.JOB_STATUS_PENDING
    },
    "input_id": "b5ddde55-594e-428f-9040-028be81eb3c2",
    "job_configs": {
        "args": [
            "bob",
            "bill"
        ],
        "configs": {
            swift_helper.HADOOP_SWIFT_PASSWORD: "openstack",
            swift_helper.HADOOP_SWIFT_USERNAME: "admin",
            "myfavoriteconfig": 1
        },
        "proxy_configs": {
            "proxy_username": "admin",
            "proxy_password": "openstack"
        },
        "trusts": {
            "input_id": "9c528755099149b8b7166f3d0fa3bf10",
            "output_id": "3f2bde9d43ec440381dc9f736481e2b0"
        }
    },
    "job_id": "d0f3e397-7bef-42f9-a4db-e5a96059246e",
    "output_id": "f4993830-aa97-4b0b-914a-ab6430f742b6",
    "tenant_id": "6b859fb8d1f44e8eafdfb91f21309b5f"
}


class TestResource(testtools.TestCase):
    def test_resource_creation(self):
        res = r.Resource(SAMPLE_DICT)

        self.assertIsInstance(res.first, list)
        self.assertEqual([1, 2], res.first)
        self.assertIsInstance(res.second, r.Resource)
        self.assertEqual(1, res.second.a)
        self.assertEqual(2, res.second.b)

    def test_resource_immutability(self):
        res = r.Resource(SAMPLE_DICT)

        with testtools.ExpectedException(ex.FrozenClassError):
            res.first.append(123)

        with testtools.ExpectedException(ex.FrozenClassError):
            res.first = 123

        with testtools.ExpectedException(ex.FrozenClassError):
            res.second.a = 123

    def test_nested_lists(self):
        res = r.Resource(SAMPLE_NESTED_LISTS_DICT)
        self.assertEqual(123, res.a[0][0].b)

    def test_cluster_resource(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)

        self.assertEqual('test-cluster', cluster.name)

        self.assertEqual('master', cluster.node_groups[0].name)
        self.assertIsInstance(cluster.node_groups[0], r.NodeGroupResource)
        self.assertEqual('test-cluster', cluster.node_groups[0].cluster.name)

        self.assertEqual('test-cluster-001',
                         cluster.node_groups[1].instances[0].name)
        self.assertIsInstance(cluster.node_groups[1].instances[0],
                              r.InstanceResource)
        self.assertEqual('worker',
                         cluster.node_groups[1].instances[0].node_group.name)

    def test_to_dict(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)
        self.assertEqual(SAMPLE_CLUSTER_DICT, cluster.to_dict())

    def test_to_dict_filtering(self):
        cluster_dict = copy.deepcopy(SAMPLE_CLUSTER_DICT)
        cluster_dict['management_private_key'] = 'abacaba'
        cluster_dict['node_groups'][0]['id'] = 'some_id'

        cluster = r.ClusterResource(cluster_dict)
        self.assertEqual(SAMPLE_CLUSTER_DICT, cluster.to_dict())

    def test_to_wrapped_dict(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)
        wrapped_dict = cluster.to_wrapped_dict()
        self.assertEqual(1, len(wrapped_dict))
        self.assertEqual(SAMPLE_CLUSTER_DICT, wrapped_dict['cluster'])

    def test_job_binary_filter_extra(self):
        job_binary = r.JobBinary(SAMPLE_JOB_BINARY_DICT)
        wrapped_dict = job_binary.to_wrapped_dict()
        self.assertNotIn('extra', wrapped_dict)

    def test_data_source_filter_credentials(self):
        data_source = r.DataSource(SAMPLE_DATA_SOURCE)
        wrapped_dict = data_source.to_wrapped_dict()
        self.assertNotIn('credentials', wrapped_dict)

    def test_job_filter_job_binary(self):
        job = r.Job(SAMPLE_JOB_DICT)
        wrapped_dict = job.to_wrapped_dict()
        self.assertIn('mains', wrapped_dict["job"])
        self.assertIn('libs', wrapped_dict["job"])
        self.assertNotIn('extra', wrapped_dict["job"]['mains'])
        self.assertNotIn('extra', wrapped_dict["job"]['libs'])

    def test_job_execution_filter_credentials(self):
        job_exec = r.JobExecution(SAMPLE_JOB_EXECUTION)
        self.assertIn('extra', job_exec)
        self.assertIn(swift_helper.HADOOP_SWIFT_PASSWORD,
                      job_exec['job_configs']['configs'])
        self.assertIn(swift_helper.HADOOP_SWIFT_USERNAME,
                      job_exec['job_configs']['configs'])
        for a in job_exec['info']['actions']:
            self.assertIn('conf', a)
        self.assertIn('trusts', job_exec['job_configs'])
        self.assertIn('input_id', job_exec['job_configs']['trusts'])
        self.assertIn('output_id', job_exec['job_configs']['trusts'])
        self.assertIn('proxy_configs', job_exec['job_configs'])
        self.assertIn('proxy_username',
                      job_exec['job_configs']['proxy_configs'])
        self.assertIn('proxy_password',
                      job_exec['job_configs']['proxy_configs'])

        wrapped_dict = job_exec.to_wrapped_dict()['job_execution']
        self.assertNotIn('extra', wrapped_dict)

        configs = wrapped_dict['job_configs']['configs']
        self.assertEqual("",
                         configs[swift_helper.HADOOP_SWIFT_PASSWORD])
        self.assertEqual("",
                         configs[swift_helper.HADOOP_SWIFT_USERNAME])

        for a in wrapped_dict['info']['actions']:
            self.assertNotIn('conf', a)

        self.assertNotIn('trusts', wrapped_dict['job_configs'])
        self.assertNotIn('proxy_configs', wrapped_dict['job_configs'])
