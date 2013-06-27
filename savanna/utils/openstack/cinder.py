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

from cinderclient.v1 import client as cinder_client

from savanna import context
from savanna.utils.openstack import base


def client():
    headers = context.current().headers
    username = headers['X-User-Name']
    token = headers['X-Auth-Token']
    tenant = headers['X-Tenant-Id']
    volume_url = base.url_for(headers, 'volume')

    cinder = cinder_client.Client(username, token, tenant, volume_url)

    cinder.client.auth_token = token
    cinder.client.management_url = volume_url

    return cinder


def get_volumes():
    return [volume.id for volume in client().volumes.list()]


def get_volume(volume_id):
    return client().volumes.get(volume_id)
