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

from sahara.plugins import utils as pu
from sahara.tests.unit import base as b


class FakeInstace(object):
    def __init__(self, node_processes):
        self.node_processes = node_processes

    @property
    def node_group(self):
        return self


class TestPluginUtils(b.SaharaTestCase):
    def test_instances_with_services(self):
        inst = [FakeInstace(["1", "2", "3"]), FakeInstace(["1", "3"]),
                FakeInstace(["1"]), FakeInstace(["3"])]

        self.assertEqual(4, len(pu.instances_with_services(inst, ["1", "3"])))
        self.assertEqual(1, len(pu.instances_with_services(inst, ["2"])))
        self.assertEqual(3, len(pu.instances_with_services(inst, ["3"])))
        self.assertEqual(0, len(pu.instances_with_services(inst, ["5"])))
