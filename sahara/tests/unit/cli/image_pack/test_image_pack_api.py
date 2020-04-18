# Copyright (c) 2016 Red Hat, Inc.
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

import sys
guestfs = mock.Mock()
sys.modules['guestfs'] = guestfs

from sahara.cli.image_pack import api
from sahara.tests.unit import base


class TestSaharaImagePackAPI(base.SaharaTestCase):

    def setUp(self):
        super(TestSaharaImagePackAPI, self).setUp()

    def tearDown(self):
        super(TestSaharaImagePackAPI, self).tearDown()

    @mock.patch('sahara.cli.image_pack.api.guestfs')
    @mock.patch('sahara.cli.image_pack.api.plugins_base')
    @mock.patch('sahara.cli.image_pack.api.LOG')
    def test_pack_image_call(self, mock_log, mock_plugins_base, mock_guestfs):
        guest = mock.Mock()
        mock_guestfs.GuestFS = mock.Mock(return_value=guest)
        guest.inspect_os = mock.Mock(return_value=['/dev/something1'])
        plugin = mock.Mock()
        mock_plugins_base.PLUGINS = mock.Mock(
            get_plugin=mock.Mock(return_value=plugin))

        api.pack_image(
            "image_path", "plugin_name", "plugin_version",
            {"anarg": "avalue"}, root_drive=None, test_only=False)

        guest.add_drive_opts.assert_called_with("image_path", format="qcow2")
        guest.set_network.assert_called_with(True)
        guest.launch.assert_called_once_with()
        guest.mount.assert_called_with('/dev/something1', '/')
        guest.sh.assert_called_with("echo Testing sudo without tty...")
        guest.sync.assert_called_once_with()
        guest.umount_all.assert_called_once_with()
        guest.close.assert_called_once_with()

    @mock.patch('sahara.cli.image_pack.api.plugins_base')
    def test_get_plugin_arguments(self, mock_plugins_base):
        api.setup_plugins()
        mock_plugins_base.setup_plugins.assert_called_once_with()
        mock_PLUGINS = mock.Mock()
        mock_plugins_base.PLUGINS = mock_PLUGINS
        mock_plugin = mock.Mock()
        mock_plugin.get_versions = mock.Mock(return_value=['1'])
        mock_plugin.get_image_arguments = mock.Mock(
            return_value=["Argument!"])
        mock_PLUGINS.get_plugin = mock.Mock(return_value=mock_plugin)
        result = api.get_plugin_arguments('Plugin!')
        mock_plugin.get_versions.assert_called_once_with()
        mock_plugin.get_image_arguments.assert_called_once_with('1')
        self.assertEqual(result, {'1': ['Argument!']})
