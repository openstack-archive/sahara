# Copyright (c) 2015 Red Hat, Inc.
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

from keystoneclient import session as keystone

from sahara import exceptions as ex
from sahara.service import sessions
from sahara.tests.unit import base


class TestSessionCache(base.SaharaTestCase):

    def test_get_session(self):
        sc = sessions.cache()

        session = sc.get_session()
        self.assertTrue(isinstance(session, keystone.Session))

        self.assertRaises(ex.SaharaException,
                          sc.get_session,
                          session_type='bad service')
