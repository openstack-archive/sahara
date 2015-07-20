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

import mock

from sahara.service import trusts
from sahara.tests.unit import base


class FakeTrust(object):

    def __init__(self, id):
        self.id = id


class TestTrusts(base.SaharaTestCase):

    def _trustor(self):
        create = mock.Mock()
        create.return_value = FakeTrust("trust_id")
        trustor_trusts = mock.Mock(create=create)
        trustor = mock.Mock(user_id="trustor_id", tenant_id="tenant_id",
                            trusts=trustor_trusts)
        return trustor

    def test_create_trust(self):
        trustor = self._trustor()
        trustee = mock.Mock(user_id="trustee_id")
        trust_id = trusts.create_trust(trustor, trustee,
                                       "role_names", expires=True)
        trustor.trusts.create.assert_called_with(
            trustor_user="trustor_id",
            trustee_user="trustee_id",
            impersonation=True,
            role_names="role_names",
            project="tenant_id",
            expires_at=mock.ANY
        )
        self.assertEqual("trust_id", trust_id)

    @mock.patch('sahara.utils.openstack.keystone.client_for_admin')
    @mock.patch('sahara.utils.openstack.keystone.client')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.context.current')
    def test_create_trust_for_cluster(self, m_current, m_cluster_update,
                                      m_client, m_client_for_admin):
        ctx = mock.Mock(roles="role_names")
        trustee = mock.Mock(user_id="trustee_id")
        trustor = self._trustor()

        m_current.return_value = ctx
        m_client_for_admin.return_value = trustee
        m_client.return_value = trustor

        trusts.create_trust_for_cluster("cluster")

        trustor.trusts.create.assert_called_with(
            trustor_user="trustor_id",
            trustee_user="trustee_id",
            impersonation=True,
            role_names="role_names",
            project="tenant_id",
            expires_at=mock.ANY
        )
        m_cluster_update.assert_called_with(ctx, "cluster",
                                            {"trust_id": "trust_id"})
