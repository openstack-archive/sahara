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

from sahara.cli import sahara_all
from sahara.cli import sahara_api
from sahara.cli import sahara_engine
from sahara.tests.unit import base


class TestSaharaCLI(base.SaharaTestCase):

    def setUp(self):
        super(TestSaharaCLI, self).setUp()

        modules = [
            'sahara.main.setup_common',
            'oslo_service.wsgi.Server.__init__',
            'oslo_service.wsgi.Loader'
        ]

        self.patchers = []
        for module in modules:
            patch = mock.patch(module)
            patch.start()
            self.patchers.append(patch)

        mock_get_pl_patch = mock.patch('sahara.main.get_process_launcher')
        self.patchers.append(mock_get_pl_patch)
        self.mock_get_pl = mock_get_pl_patch.start()

        mock_start_server_patch = mock.patch(
            'sahara.main.SaharaWSGIService.start')
        self.patchers.append(mock_start_server_patch)
        self.mock_start_server = mock_start_server_patch.start()

    def tearDown(self):
        super(TestSaharaCLI, self).tearDown()
        for patcher in reversed(self.patchers):
            patcher.stop()

    @mock.patch('oslo_config.cfg.ConfigOpts.find_file')
    @mock.patch('sahara.main.setup_sahara_api')
    def test_main_start_api(self, mock_setup_sahara_api, mock_config):
        mock_config.return_value = '/etc/sahara/'
        sahara_api.main()

        self.mock_start_server.assert_called_once_with()
        self.mock_get_pl.return_value.wait.assert_called_once_with()

    @mock.patch('sahara.utils.rpc.RPCServer.get_service')
    @mock.patch('oslo_service.service.ProcessLauncher')
    @mock.patch('sahara.main._get_ops_driver')
    @mock.patch('sahara.service.ops.OpsServer')
    def test_main_start_engine(self, mock_ops_server, mock_get_ops_driver,
                               mock_pl, mock_get_service):

        self.mock_get_pl.return_value = mock_pl
        mock_ops_server.return_value.get_service.return_value = (
            mock_get_service)

        sahara_engine.main()

        mock_pl.launch_service.assert_called_once_with(mock_get_service)
        mock_pl.wait.assert_called_once_with()

    @mock.patch('oslo_config.cfg.ConfigOpts.find_file')
    def test_main_start_all(self, mock_config):
        mock_config.return_value = '/etc/sahara/'
        sahara_all.main()

        self.mock_start_server.assert_called_once_with()
        self.mock_get_pl.return_value.wait.assert_called_once_with()
