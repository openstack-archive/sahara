# Copyright (c) 2016 Mirantis Inc.
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
from oslo_serialization import jsonutils

from sahara.plugins.ambari import deploy
from sahara.tests.unit import base


class TestDeploy(base.SaharaTestCase):
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.plugins.ambari.client.AmbariClient.get')
    @mock.patch('sahara.plugins.ambari.client.AmbariClient.delete')
    def test_cleanup_config_groups(self, client_delete, client_get,
                                   get_instance):
        def response(data):
            fake = mock.Mock()
            fake.text = jsonutils.dumps(data)
            fake.raise_for_status.return_value = True
            return fake

        fake_config_groups = {
            'items': [
                {'ConfigGroup': {'id': "1"}},
                {'ConfigGroup': {'id': "2"}}
            ]
        }

        config_group1 = {
            'ConfigGroup': {'id': '1', 'group_name': "test:fakename"}}
        config_group2 = {
            'ConfigGroup': {'id': '2', 'group_name': "test:toremove"}}

        fake_ambari = mock.Mock()
        fake_ambari.management_ip = "127.0.0.1"
        get_instance.return_value = fake_ambari

        inst1 = mock.Mock()
        inst1.instance_name = "toremove"

        cl = mock.Mock(extra={'ambari_password': "SUPER_STRONG"})
        cl.name = "test"

        client_get.side_effect = [
            response(fake_config_groups), response(config_group1),
            response(config_group2)
        ]
        client_delete.side_effect = [response({})]

        deploy.cleanup_config_groups(cl, [inst1])
        get_calls = [
            mock.call(
                'http://127.0.0.1:8080/api/v1/clusters/test/config_groups'),
            mock.call(
                'http://127.0.0.1:8080/api/v1/clusters/test/config_groups/1'),
            mock.call(
                'http://127.0.0.1:8080/api/v1/clusters/test/config_groups/2')
        ]

        self.assertEqual(get_calls, client_get.call_args_list)

        delete_calls = [
            mock.call(
                'http://127.0.0.1:8080/api/v1/clusters/test/config_groups/2')
        ]

        self.assertEqual(delete_calls, client_delete.call_args_list)
