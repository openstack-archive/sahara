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

import unittest2

from savanna.db import models as m


class VolumesSupportTest(unittest2.TestCase):
    def test_instance_storage_paths_wo_volumes(self):
        i = m.NodeGroup('ng-1', 'f-1', [], 1)

        self.assertEqual(
            [
                '/mnt',
            ],
            i.storage_paths)

    def test_instance_storage_paths(self):
        i = m.NodeGroup('ng-1', 'f-1', [], 1, volumes_per_node=3)

        self.assertEqual(
            [
                '/volumes/disk1',
                '/volumes/disk2',
                '/volumes/disk3',
            ],
            i.storage_paths)

    def test_instance_storage_paths_custem_prefix(self):
        i = m.NodeGroup('ng-1', 'f-1', [], 1,
                        volumes_per_node=3,
                        volume_mount_prefix='/foo')

        self.assertEqual(
            [
                '/foo1',
                '/foo2',
                '/foo3',
            ],
            i.storage_paths)
