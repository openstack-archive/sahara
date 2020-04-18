# Copyright (c) 2015 Red Hat, Inc.
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

from sahara.service.edp.binary_retrievers import dispatch
from sahara.tests.unit import base


class TestDispatch(base.SaharaTestCase):
    def setUp(self):
        super(TestDispatch, self).setUp()

    @mock.patch('sahara.service.edp.s3_common.get_raw_job_binary_data')
    @mock.patch('sahara.service.edp.binary_retrievers.'
                'manila_share.get_file_info')
    @mock.patch(
        'sahara.service.edp.binary_retrievers.internal_swift.'
        'get_raw_data_with_context')
    @mock.patch(
        'sahara.service.edp.binary_retrievers.internal_swift.get_raw_data')
    @mock.patch('sahara.service.edp.binary_retrievers.sahara_db.get_raw_data')
    @mock.patch('sahara.context.ctx')
    def test_get_raw_binary(self, ctx, db_get_raw_data, i_s_get_raw_data,
                            i_s_get_raw_data_with_context, m_s_get_file_info,
                            s3_get_raw_jb_data):
        ctx.return_value = mock.Mock()

        job_binary = mock.Mock()
        job_binary.url = 'internal-db://somebinary'

        dispatch.get_raw_binary(job_binary)
        self.assertEqual(1, db_get_raw_data.call_count)

        job_binary.url = 'swift://container/object'
        proxy_configs = dict(proxy_username='proxytest',
                             proxy_password='proxysecret',
                             proxy_trust_id='proxytrust')
        dispatch.get_raw_binary(job_binary, proxy_configs)
        dispatch.get_raw_binary(job_binary, proxy_configs, with_context=True)
        dispatch.get_raw_binary(job_binary, with_context=True)
        self.assertEqual(1, i_s_get_raw_data.call_count)
        self.assertEqual(2, i_s_get_raw_data_with_context.call_count)

        job_binary.url = 'manila://the_share_id/the_path'
        remote = mock.Mock()
        remote.instance.node_group.cluster.shares = []
        remote.instance.node_group.shares = []
        dispatch.get_raw_binary(job_binary, remote=remote)
        self.assertEqual(1, m_s_get_file_info.call_count)

        job_binary.url = 's3://bucket/object.jar'
        dispatch.get_raw_binary(job_binary)
        self.assertEqual(1, s3_get_raw_jb_data.call_count)
