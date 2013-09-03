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

from keystoneclient.v2_0 import client as keystone_client

from savanna import context
from savanna.utils.openstack import base


def client():
    ctx = context.current()
    identity_url = base.url_for(ctx.service_catalog, 'identity')

    keystone = keystone_client.Client(username=ctx.username,
                                      user_id=ctx.user_id,
                                      token=ctx.token,
                                      tenant_name=ctx.tenant_name,
                                      tenant_id=ctx.tenant_id,
                                      auth_url=identity_url)

    return keystone
