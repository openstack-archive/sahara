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

import time

from oslo_utils import timeutils
from saharaclient.api import base as sab
from tempest import config
from tempest import exceptions
from tempest.scenario.data_processing.client_tests import base
from tempest.scenario.data_processing import config as sahara_test_config
from tempest import test
from tempest_lib.common.utils import data_utils
from tempest_lib import decorators

CONF = sahara_test_config.SAHARA_TEST_CONF
TEMPEST_CONF = config.CONF


class JobExecutionTest(base.BaseDataProcessingTest):
    def _check_register_image(self, image_id):
        self.client.images.update_image(
            image_id, CONF.data_processing.ssh_username, '')
        reg_image = self.client.images.get(image_id)

        self.assertDictContainsSubset(
            {'_sahara_username': CONF.data_processing.ssh_username},
            reg_image.metadata)

    def _check_image_get(self, image_id):
        image = self.client.images.get(image_id)

        self.assertEqual(image_id, image.id)

    def _check_image_list(self, image_id):
        # check for image in list
        image_list = self.client.images.list()
        images_info = [image.id for image in image_list]

        self.assertIn(image_id, images_info)

    def _check_adding_tags(self, image_id):
        # adding new tags
        self.client.images.update_tags(image_id, ['fake', '0.1'])
        image = self.client.images.get(image_id)

        self.assertDictContainsSubset({'_sahara_tag_fake': 'True',
                                       '_sahara_tag_0.1': 'True'},
                                      image.metadata)

    def _check_deleting_tags(self, image_id):
        # deleting tags
        self.client.images.update_tags(image_id, [])
        image = self.client.images.get(image_id)

        self.assertNotIn('_sahara_tag_fake', image.metadata)
        self.assertNotIn('_sahara_tag_0.1', image.metadata)

    def _check_unregister_image(self, image_id):
        # unregister image
        self.client.images.unregister_image(image_id)

        # check that image really unregistered
        image_list = self.client.images.list()
        self.assertNotIn(image_id, [image.id for image in image_list])

    def _check_cluster_create(self):
        worker = self.create_node_group_template(
            data_utils.rand_name('sahara-ng-template'), **self.worker_template)

        master = self.create_node_group_template(
            data_utils.rand_name('sahara-ng-template'), **self.master_template)

        cluster_templ = self.cluster_template.copy()
        cluster_templ['node_groups'] = [
            {
                'name': 'master',
                'node_group_template_id': master.id,
                'count': 1
            },
            {
                'name': 'worker',
                'node_group_template_id': worker.id,
                'count': 3
            }
        ]
        if TEMPEST_CONF.service_available.neutron:
            cluster_templ['net_id'] = self.get_private_network_id()

        cluster_template = self.create_cluster_template(
            data_utils.rand_name('sahara-cluster-template'), **cluster_templ)
        cluster_name = data_utils.rand_name('sahara-cluster')
        self.cluster_info = {
            'name': cluster_name,
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'cluster_template_id': cluster_template.id,
            'default_image_id': CONF.data_processing.fake_image_id
        }

        # create cluster
        cluster = self.create_cluster(**self.cluster_info)

        # wait until cluster moves to active state
        self.check_cluster_active(cluster.id)

        # check that cluster created successfully
        self.assertEqual(cluster_name, cluster.name)
        self.assertDictContainsSubset(self.cluster_info, cluster.__dict__)

        return cluster.id, cluster.name

    def _check_cluster_list(self, cluster_id, cluster_name):
        # check for cluster in list
        cluster_list = self.client.clusters.list()
        clusters_info = [(clust.id, clust.name) for clust in cluster_list]
        self.assertIn((cluster_id, cluster_name), clusters_info)

    def _check_cluster_get(self, cluster_id, cluster_name):
        # check cluster fetch by id
        cluster = self.client.clusters.get(cluster_id)
        self.assertEqual(cluster_name, cluster.name)
        self.assertDictContainsSubset(self.cluster_info, cluster.__dict__)

    def _check_cluster_scale(self, cluster_id):
        big_worker = self.create_node_group_template(
            data_utils.rand_name('sahara-ng-template'), **self.worker_template)

        scale_body = {
            'resize_node_groups': [
                {
                    'count': 2,
                    'name': 'worker'
                },
                {
                    "count": 2,
                    "name": 'master'
                }
            ],
            'add_node_groups': [
                {
                    'count': 1,
                    'name': 'big-worker',
                    'node_group_template_id': big_worker.id

                }
            ]
        }

        self.client.clusters.scale(cluster_id, scale_body)
        self.check_cluster_active(cluster_id)

        cluster = self.client.clusters.get(cluster_id)
        for ng in cluster.node_groups:
            if ng['name'] == scale_body['resize_node_groups'][0]['name']:
                self.assertDictContainsSubset(
                    scale_body['resize_node_groups'][0], ng)
            elif ng['name'] == scale_body['resize_node_groups'][1]['name']:
                self.assertDictContainsSubset(
                    scale_body['resize_node_groups'][1], ng)
            elif ng['name'] == scale_body['add_node_groups'][0]['name']:
                self.assertDictContainsSubset(
                    scale_body['add_node_groups'][0], ng)

    def _check_cluster_delete(self, cluster_id):
        self.client.clusters.delete(cluster_id)

        # check that cluster moved to deleting state
        cluster = self.client.clusters.get(cluster_id)
        self.assertEqual(cluster.status, 'Deleting')

        timeout = CONF.data_processing.cluster_timeout
        s_time = timeutils.utcnow()
        while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
            try:
                self.client.clusters.get(cluster_id)
            except sab.APIException:
                # cluster is deleted
                return
            time.sleep(CONF.data_processing.request_timeout)

        raise exceptions.TimeoutException('Cluster failed to terminate'
                                          'in %d seconds.' % timeout)

    def _check_job_execution_create(self, cluster_id):
        # create swift container
        container_name = data_utils.rand_name('test-container')
        self.create_container(container_name)

        # create input data source
        input_file_name = data_utils.rand_name('input')
        self.object_client.create_object(container_name, input_file_name,
                                         'some-data')

        input_file_url = 'swift://%s/%s' % (container_name, input_file_name)
        input_source_name = data_utils.rand_name('input-data-source')
        input_source = self.create_data_source(
            input_source_name, input_file_url, '', 'swift',
            {'user': 'test', 'password': '123'})

        # create output data source
        output_dir_name = data_utils.rand_name('output')
        output_dir_url = 'swift://%s/%s' % (container_name, output_dir_name)
        output_source_name = data_utils.rand_name('output-data-source')
        output_source = self.create_data_source(
            output_source_name, output_dir_url, '', 'swift',
            {'user': 'test', 'password': '123'})

        job_binary = {
            'name': data_utils.rand_name('sahara-job-binary'),
            'url': input_file_url,
            'description': 'Test job binary',
            'extra': {
                'user': 'test',
                'password': '123'
            }
        }
        # create job_binary
        job_binary = self.create_job_binary(**job_binary)

        # create job
        job_name = data_utils.rand_name('test-job')
        job = self.create_job(job_name, 'Pig', [job_binary.id])

        self.job_exec_info = {
            'job_id': job.id,
            'cluster_id': cluster_id,
            'input_id': input_source.id,
            'output_id': output_source.id,
            'configs': {}
        }
        # create job execution
        job_execution = self.create_job_execution(**self.job_exec_info)

        return job_execution.id

    def _check_job_execution_list(self, job_exec_id):
        # check for job_execution in list
        job_exec_list = self.client.job_executions.list()
        self.assertIn(job_exec_id, [job_exec.id for job_exec in job_exec_list])

    def _check_job_execution_get(self, job_exec_id):
        # check job_execution fetch by id
        job_exec = self.client.job_executions.get(job_exec_id)
        # Create extra cls.swift_job_binary variable to use for comparison to
        # job binary response body because response body has no 'extra' field.
        job_exec_info = self.job_exec_info.copy()
        del job_exec_info['configs']
        self.assertDictContainsSubset(job_exec_info, job_exec.__dict__)

    def _check_job_execution_delete(self, job_exec_id):
        # delete job_execution by id
        self.client.job_executions.delete(job_exec_id)
        # check that job_execution really deleted
        job_exec_list = self.client.jobs.list()
        self.assertNotIn(job_exec_id, [job_exec.id for
                                       job_exec in job_exec_list])

    @decorators.skip_because(bug="1430252")
    @test.attr(type='slow')
    @test.services('data_processing')
    def test_job_executions(self):
        image_id = CONF.data_processing.fake_image_id
        self._check_register_image(image_id)
        self._check_image_get(image_id)
        self._check_image_list(image_id)
        self._check_adding_tags(image_id)

        cluster_id, cluster_name = self._check_cluster_create()
        self._check_cluster_list(cluster_id, cluster_name)
        self._check_cluster_get(cluster_id, cluster_name)
        self._check_cluster_scale(cluster_id)

        job_exec_id = self._check_job_execution_create(cluster_id)
        self._check_job_execution_list(job_exec_id)
        self._check_job_execution_get(job_exec_id)

        self._check_job_execution_delete(job_exec_id)
        self._check_cluster_delete(cluster_id)
        self._check_deleting_tags(image_id)
        self._check_unregister_image(image_id)

    @classmethod
    def tearDownClass(cls):
        image_list = cls.client.images.list()
        image_id = CONF.data_processing.fake_image_id
        if image_id in [image.id for image in image_list]:
            cls.client.images.unregister_image(image_id)
        super(JobExecutionTest, cls).tearDownClass()
