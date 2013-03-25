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

import logging

from novaclient.v1_1 import client as nova_client

from savanna.utils.openstack.base import url_for


def novaclient(headers):
    username = headers['X-User-Name']
    token = headers['X-Auth-Token']
    tenant = headers['X-Tenant-Id']
    compute_url = url_for(headers, 'compute')

    logging.debug('novaclient connection created using token '
                  '"%s", tenant "%s" and url "%s"',
                  token, tenant, compute_url)

    nova = nova_client.Client(username, token, tenant,
                              auth_url=compute_url)

    nova.client.auth_token = token
    nova.client.management_url = compute_url

    return nova


def get_flavors(headers):
    flavors = [flavor.name for flavor
               in novaclient(headers).flavors.list()]
    return flavors


def get_images(headers):
    images = [image.name for image
              in novaclient(headers).images.list()]
    return images
