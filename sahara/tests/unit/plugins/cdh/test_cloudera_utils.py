# Copyright (c) 2014 Mirantis Inc.
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

import mock

from sahara.plugins.cdh.v5_3_0 import cloudera_utils as cu
from sahara.tests.unit import base
from sahara.tests.unit.plugins.cdh import utils as ctu


CU = cu.ClouderaUtilsV530()


class ClouderaUtilsTestCase(base.SaharaTestCase):
    @mock.patch('sahara.plugins.cdh.v5_3_0.cloudera_utils.ClouderaUtilsV530.'
                'get_cloudera_cluster')
    def test_get_service(self, mock_get_cl_cluster):
        self.assertRaises(ValueError, CU.get_service_by_role, 'NAMENODE')

        cluster = ctu.get_fake_cluster()
        inst = cluster.node_groups[0].instances[0]
        mock_get_cl_cluster.return_value = None

        self.assertRaises(ValueError, CU.get_service_by_role, 'spam',
                          cluster)
        self.assertRaises(ValueError, CU.get_service_by_role, 'spam',
                          instance=inst)

        mock_get_cl_cluster.reset_mock()

        mock_get_service = mock.MagicMock()
        mock_get_service.get_service.return_value = mock.Mock()
        mock_get_cl_cluster.return_value = mock_get_service

        CU.get_service_by_role('NAMENODE', cluster)
        args = ((CU.HDFS_SERVICE_NAME,),)
        self.assertEqual(args, mock_get_service.get_service.call_args)

        mock_get_service.reset_mock()
        CU.get_service_by_role('JOBHISTORY', instance=inst)
        args = ((CU.YARN_SERVICE_NAME,),)
        self.assertEqual(args, mock_get_service.get_service.call_args)

        mock_get_service.reset_mock()
        CU.get_service_by_role('OOZIE_SERVER', cluster)
        args = ((CU.OOZIE_SERVICE_NAME,),)
        self.assertEqual(args, mock_get_service.get_service.call_args)

    def test_get_role_name(self):
        inst_mock = mock.Mock()
        inst_mock.hostname.return_value = 'spam-host'

        self.assertEqual('eggs_spam_host',
                         CU.pu.get_role_name(inst_mock, 'eggs'))
