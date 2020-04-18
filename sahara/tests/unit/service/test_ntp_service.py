# Copyright (c) 2015 Mirantis Inc.
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

from sahara.service import ntp_service as ntp
from sahara.tests.unit import base as test_base


class FakeRemote(object):
    def __init__(self, effects):
        self.effects = effects
        self.idx = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # validate number of executions
        if self.idx != len(self.effects):
            raise ValueError()

    def _get_effect(self):
        self.idx += 1
        return self.effects[self.idx - 1]

    def execute_command(self, cmd, run_as_root=False):
        effect = self._get_effect()
        if isinstance(effect, RuntimeError):
            raise effect
        return 0, effect

    def append_to_file(self, file, text, run_as_root=False):
        return self.execute_command(file, run_as_root)

    def prepend_to_file(self, file, text, run_as_root=False):
        return self.execute_command(file, run_as_root)

    def get_os_distrib(self):
        return self.execute_command('get_os_distrib')


class FakeInstance(object):
    def __init__(self, effects, id):
        self.id = id
        self.instance_name = id
        self.instance_id = id
        self.effects = effects

    def remote(self):
        return FakeRemote(self.effects)


class NTPServiceTest(test_base.SaharaTestCase):
    @mock.patch('sahara.service.ntp_service.LOG.warning')
    @mock.patch('sahara.service.ntp_service.conductor.cluster_get')
    def test_configuring_ntp_unable_to_configure(self, cl_get, logger):
        instance = FakeInstance(["ubuntu", RuntimeError()], "1")
        ng = mock.Mock(instances=[instance])
        cl_get.return_value = mock.Mock(
            node_groups=[ng], cluster_configs={})
        ntp.configure_ntp('1')
        self.assertEqual(
            [mock.call("Unable to configure NTP service")],
            logger.call_args_list)

    @mock.patch('sahara.service.ntp_service.LOG.info')
    @mock.patch('sahara.service.ntp_service.conductor.cluster_get')
    def test_configuring_success(self, cl_get, logger):
        instance = FakeInstance(
            ['centos', "cat", "batman", "vs", "superman", "boom"], "1")
        ng = mock.Mock(instances=[instance])
        cl_get.return_value = mock.Mock(node_groups=[ng], cluster_configs={})
        ntp.configure_ntp('1')
        self.assertEqual([mock.call("NTP successfully configured")],
                         logger.call_args_list)

    def test_retrieve_url(self):
        cl = mock.Mock(
            cluster_configs={'general': {"URL of NTP server": "batman.org"}})
        self.assertEqual("batman.org", ntp.retrieve_ntp_server_url(cl))
        self.override_config('default_ntp_server', "superman.org")
        cl = mock.Mock(cluster_configs={'general': {}})
        self.assertEqual("superman.org", ntp.retrieve_ntp_server_url(cl))

    @mock.patch('sahara.service.ntp_service.conductor.cluster_get')
    @mock.patch('sahara.service.ntp_service.retrieve_ntp_server_url')
    def test_is_ntp_enabled(self, ntp_url, cl_get):
        cl = mock.Mock(
            cluster_configs={'general': {"Enable NTP service": False}})
        cl_get.return_value = cl
        ntp.configure_ntp('1')
        self.assertEqual(0, ntp_url.call_count)
