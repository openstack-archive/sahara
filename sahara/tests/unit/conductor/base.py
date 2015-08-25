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

import copy

from sahara.conductor import manager
from sahara.tests.unit import base


class ConductorManagerTestCase(base.SaharaWithDbTestCase):

    def __init__(self, *args, **kwargs):
        """List of check callables could be specified.

        All return values from callables will be stored in setUp and checked
        in tearDown.
        """
        self._checks = kwargs.pop("checks", [])
        super(ConductorManagerTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        super(ConductorManagerTestCase, self).setUp()
        self.api = manager.ConductorManager()

        self._results = []
        for check in self._checks:
            self._results.append(copy.deepcopy(check()))

    def tearDown(self):
        for idx, check in enumerate(self._checks):
            check_val = check()
            self.assertEqual(self._results[idx], check_val,
                             message="Check '%s' failed" % idx)
        super(ConductorManagerTestCase, self).tearDown()

    def assert_protected_resource_exception(self, ex):
        self.assertIn("marked as protected", str(ex))

    def assert_created_in_another_tenant_exception(self, ex):
        self.assertIn("wasn't created in this tenant", str(ex))
