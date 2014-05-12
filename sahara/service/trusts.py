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

import json

from oslo.config import cfg

from sahara import conductor as c
from sahara import context
from sahara.utils.openstack import keystone


conductor = c.API
CONF = cfg.CONF


def create_trust(cluster):
    client = keystone.client()

    ctx = context.current()

    trustee_id = keystone.client_for_admin().user_id

    trust = client.trusts.create(trustor_user=client.user_id,
                                 trustee_user=trustee_id,
                                 impersonation=True,
                                 role_names=ctx.roles,
                                 project=client.tenant_id)
    conductor.cluster_update(ctx,
                             cluster,
                             {'trust_id': trust.id})


def use_os_admin_auth_token(cluster):
    if cluster.trust_id:
        ctx = context.current()
        ctx.username = CONF.os_admin_username
        ctx.tenant_id = cluster.tenant_id
        client = keystone.client_for_trusts(cluster.trust_id)
        ctx.token = client.auth_token
        ctx.service_catalog = json.dumps(
            client.service_catalog.catalog['catalog'])


def delete_trust(cluster):
    if cluster.trust_id:
        keystone_client = keystone.client_for_trusts(cluster.trust_id)
        keystone_client.trusts.delete(cluster.trust_id)
