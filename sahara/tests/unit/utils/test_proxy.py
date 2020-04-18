# Copyright (c) 2014 Red Hat, Inc.
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


from unittest import mock

from oslo_utils import uuidutils

from sahara.service.edp import job_utils
from sahara.tests.unit import base
from sahara.utils import proxy as p


class TestProxyUtils(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestProxyUtils, self).setUp()

    @mock.patch('sahara.service.castellan.utils.store_secret')
    @mock.patch('sahara.context.ctx')
    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.service.trusts.create_trust')
    @mock.patch('sahara.utils.openstack.keystone.auth_for_proxy')
    @mock.patch('sahara.utils.openstack.keystone.auth')
    @mock.patch('sahara.utils.proxy.proxy_user_create')
    def test_create_proxy_user_for_job_execution(self, proxy_user, trustor,
                                                 trustee, trust,
                                                 job_execution_update,
                                                 context_current, passwd):
        job_execution = mock.Mock(id=1,
                                  output_id=2,
                                  job_id=3,
                                  job_configs=None)
        job_execution.job_configs = mock.Mock(to_dict=mock.Mock(
            return_value={}
        ))
        proxy_user.return_value = "proxy_user"
        passwd.return_value = "test_password"
        trustor.return_value = "test_trustor"
        trustee.return_value = "test_trustee"
        trust.return_value = "123456"
        ctx = mock.Mock()
        context_current.return_value = ctx
        p.create_proxy_user_for_job_execution(job_execution)
        update = {'job_configs': {'proxy_configs': None}}
        update['job_configs']['proxy_configs'] = {
            'proxy_username': 'job_1',
            'proxy_password': 'test_password',
            'proxy_trust_id': '123456'
        }
        job_execution_update.assert_called_with(ctx, job_execution, update)

    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.conductor.API.data_source_get')
    @mock.patch('sahara.conductor.API.data_source_count')
    @mock.patch('sahara.context.ctx')
    def test_job_execution_requires_proxy_user(self,
                                               ctx,
                                               data_source_count,
                                               data_source,
                                               job):

        self.override_config('use_domain_for_proxy_users', True)
        job_execution = mock.Mock(input_id=1,
                                  output_id=2,
                                  job_id=3,
                                  job_configs={})
        data_source.return_value = mock.Mock(url='swift://container/object')
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))

        data_source.return_value = mock.Mock(url='')
        job.return_value = mock.Mock(
            mains=[mock.Mock(url='swift://container/object')])
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))

        job.return_value = mock.Mock(
            mains=[],
            libs=[mock.Mock(url='swift://container/object')])
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))

        job_execution.job_configs = {'args': ['swift://container/object']}
        job.return_value = mock.Mock(
            mains=[],
            libs=[])
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))

        job_execution.job_configs = {
            'configs': {'key': 'swift://container/object'}}
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))

        job_execution.job_configs = {
            'params': {'key': 'swift://container/object'}}
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))

        data_source_count.return_value = 0
        job_execution.job_configs = {
            'configs': {job_utils.DATA_SOURCE_SUBST_NAME: True}}
        job.return_value = mock.Mock(
            mains=[],
            libs=[])
        self.assertFalse(p.job_execution_requires_proxy_user(job_execution))

        ctx.return_value = 'dummy'
        data_source_count.return_value = 1
        job_execution.job_configs = {
            'configs': {job_utils.DATA_SOURCE_SUBST_NAME: True},
            'args': [job_utils.DATA_SOURCE_PREFIX+'somevalue']}
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))
        data_source_count.assert_called_with('dummy',
                                             name=('somevalue',),
                                             url='swift://%')
        data_source_count.reset_mock()
        data_source_count.return_value = 1
        myid = uuidutils.generate_uuid()
        job_execution.job_configs = {
            'configs': {job_utils.DATA_SOURCE_SUBST_UUID: True},
            'args': [myid]}
        job.return_value = mock.Mock(
            mains=[],
            libs=[])
        self.assertTrue(p.job_execution_requires_proxy_user(job_execution))
        data_source_count.assert_called_with('dummy',
                                             id=(myid,),
                                             url='swift://%')
