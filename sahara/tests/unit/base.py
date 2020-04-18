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

from unittest import mock

from oslotest import base

from sahara import context
from sahara.db import api as db_api
from sahara import main
from sahara.utils import rpc


class SaharaTestCase(base.BaseTestCase):

    def setUp(self):
        super(SaharaTestCase, self).setUp()
        self.setup_context()
        rpc.setup('all-in-one')

    def setup_context(self, username="test_user", tenant_id="tenant_1",
                      auth_token="test_auth_token", tenant_name='test_tenant',
                      service_catalog=None, **kwargs):
        self.addCleanup(context.set_ctx,
                        context.ctx() if context.has_ctx() else None)

        context.set_ctx(context.Context(
            username=username, tenant_id=tenant_id,
            auth_token=auth_token, service_catalog=service_catalog or {},
            tenant_name=tenant_name, **kwargs))

    def override_config(self, name, override, group=None):
        main.CONF.set_override(name, override, group)
        self.addCleanup(main.CONF.clear_override, name, group)


class SaharaWithDbTestCase(SaharaTestCase):
    def setUp(self):
        super(SaharaWithDbTestCase, self).setUp()

        self.override_config('connection', "sqlite://", group='database')
        db_api.setup_db()
        self.addCleanup(db_api.drop_db)


class _ConsecutiveThreadGroup(context.ThreadGroup):
    def __init__(self, _thread_pool_size=1000):
        pass

    def spawn(self, thread_description, func, *args, **kwargs):
        func(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *ex):
        pass


def mock_thread_group(func):
    return mock.patch('sahara.context.ThreadGroup',
                      new=_ConsecutiveThreadGroup)(func)
