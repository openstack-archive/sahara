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

from unittest import mock

from sahara.service import trusts
from sahara.tests.unit import base


class FakeTrust(object):

    def __init__(self, id):
        self.id = id


class TestTrusts(base.SaharaTestCase):

    def _client(self):
        create = mock.Mock()
        create.return_value = FakeTrust("trust_id")
        client_trusts = mock.Mock(create=create)
        client = mock.Mock(trusts=client_trusts)
        return client

    @mock.patch('sahara.utils.openstack.keystone.client_from_auth')
    @mock.patch('sahara.utils.openstack.keystone.project_id_from_auth')
    @mock.patch('sahara.utils.openstack.keystone.user_id_from_auth')
    def test_create_trust(self, user_id_from_auth, project_id_from_auth,
                          client_from_auth):
        project_id_from_auth.return_value = 'tenant_id'
        user_id_from_auth.side_effect = ['trustor_id', 'trustee_id']
        trustor = 'trustor_id'
        trustee = 'trustee_id'
        client = self._client()
        client_from_auth.return_value = client
        trust_id = trusts.create_trust(trustor, trustee,
                                       "role_names")
        client.trusts.create.assert_called_with(
            trustor_user="trustor_id",
            trustee_user="trustee_id",
            impersonation=True,
            role_names="role_names",
            project="tenant_id",
            allow_redelegation=False,
        )
        self.assertEqual("trust_id", trust_id)

        user_id_from_auth.side_effect = ['trustor_id', 'trustee_id']
        client = self._client()
        client_from_auth.return_value = client
        trust_id = trusts.create_trust(trustor, trustee, "role_names",
                                       project_id='injected_project')
        client.trusts.create.assert_called_with(trustor_user="trustor_id",
                                                trustee_user="trustee_id",
                                                impersonation=True,
                                                role_names="role_names",
                                                project="injected_project",
                                                allow_redelegation=False)
        self.assertEqual("trust_id", trust_id)

    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.service.trusts.create_trust')
    @mock.patch('sahara.utils.openstack.keystone.auth_for_admin')
    @mock.patch('sahara.context.current')
    def test_create_trust_for_cluster(self, context_current, auth_for_admin,
                                      create_trust, cluster_update, cl_get):
        self.override_config('project_name', 'admin_project', group='trustee')
        trustor_auth = mock.Mock()
        fake_cluster = mock.Mock(trust_id=None)
        cl_get.return_value = fake_cluster
        ctx = mock.Mock(roles="role_names", auth_plugin=trustor_auth)
        context_current.return_value = ctx
        trustee_auth = mock.Mock()
        auth_for_admin.return_value = trustee_auth
        create_trust.return_value = 'trust_id'

        trusts.create_trust_for_cluster("cluster")

        auth_for_admin.assert_called_with(project_name='admin_project')
        create_trust.assert_called_with(trustor=trustor_auth,
                                        trustee=trustee_auth,
                                        role_names='role_names',
                                        allow_redelegation=True)

        cluster_update.assert_called_with(ctx, fake_cluster,
                                          {"trust_id": "trust_id"})

    @mock.patch('sahara.utils.openstack.keystone.client_from_auth')
    @mock.patch('sahara.utils.openstack.keystone.auth_for_admin')
    @mock.patch('sahara.service.trusts.create_trust')
    def test_delete_trust(self, trust, auth_for_admin,
                          client_from_auth):
        client = self._client()
        client_from_auth.return_value = client
        trust.return_value = 'test_id'
        trustor_auth = mock.Mock()
        trustee_auth = mock.Mock()
        auth_for_admin.return_value = trustee_auth
        trust_id = trusts.create_trust(trustor_auth, trustee_auth,
                                       "role_names")

        trusts.delete_trust(trustee_auth, trust_id)
        client.trusts.delete.assert_called_with(trust_id)

    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.utils.openstack.keystone.auth_for_admin')
    @mock.patch('sahara.service.trusts.delete_trust')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.context.current')
    def test_delete_trust_from_cluster(self, context_current, cl_get,
                                       delete_trust, auth_for_admin,
                                       cluster_update):
        fake_cluster = mock.Mock(trust_id='test_id')
        cl_get.return_value = fake_cluster
        trustor_auth = mock.Mock()
        trustee_auth = mock.Mock()
        auth_for_admin.return_value = trustee_auth
        ctx = mock.Mock(roles="role_names", auth_plugin=trustor_auth)
        context_current.return_value = ctx
        trusts.delete_trust_from_cluster("cluster")

        delete_trust.assert_called_with(trustee_auth, 'test_id')
        cluster_update.assert_called_with(ctx, fake_cluster,
                                          {"trust_id": None})
