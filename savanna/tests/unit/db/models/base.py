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

import datetime
import os
import tempfile
import unittest2

from savanna import context
from savanna.db import api as db_api
from savanna.openstack.common.db.sqlalchemy import session
from savanna.openstack.common import timeutils
from savanna.openstack.common import uuidutils


class ModelTestCase(unittest2.TestCase):
    def setUp(self):
        context.set_ctx(
            context.Context('test_user', 'test_tenant', 'test_auth_token', {}))
        self.db_fd, self.db_path = tempfile.mkstemp()
        session.set_defaults('sqlite:///' + self.db_path, self.db_path)
        db_api.configure_db()

    def tearDown(self):
        db_api.clear_db()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        context.set_ctx(None)

    def assertIsValidModelObject(self, res):
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.dict)
        self.assertTrue(uuidutils.is_uuid_like(res.id))

        # check created/updated
        delta = datetime.timedelta(seconds=2)
        now = timeutils.utcnow()

        self.assertAlmostEqual(res.created, now, delta=delta)
        self.assertAlmostEqual(res.updated, now, delta=delta)

    def get_clean_dict(self, res):
        res_dict = res.dict
        del res_dict['created']
        del res_dict['updated']
        del res_dict['id']
        if 'tenant_id' in res_dict:
            del res_dict['tenant_id']

        return res_dict
