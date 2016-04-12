# Copyright (c) 2016 Red Hat, Inc.
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

from sahara import conductor as c
from sahara.utils.openstack import base as b
from sahara.utils.openstack import nova


conductor = c.API


# Image Registry


def get_images(name, tags):
    return b.execute_with_retries(
        nova.client().images.list_registered, name, tags)


def get_image(**kwargs):
    if len(kwargs) == 1 and 'id' in kwargs:
        return b.execute_with_retries(nova.client().images.get, kwargs['id'])
    else:
        return b.execute_with_retries(nova.client().images.find, **kwargs)


def get_registered_image(id):
    return b.execute_with_retries(
        nova.client().images.get_registered_image, id)


def register_image(image_id, username, description=None):
    client = nova.client()
    b.execute_with_retries(
        client.images.set_description, image_id, username, description)
    return b.execute_with_retries(client.images.get, image_id)


def unregister_image(image_id):
    client = nova.client()
    b.execute_with_retries(client.images.unset_description, image_id)
    return b.execute_with_retries(client.images.get, image_id)


def add_image_tags(image_id, tags):
    client = nova.client()
    b.execute_with_retries(client.images.tag, image_id, tags)
    return b.execute_with_retries(client.images.get, image_id)


def remove_image_tags(image_id, tags):
    client = nova.client()
    b.execute_with_retries(client.images.untag, image_id, tags)
    return b.execute_with_retries(client.images.get, image_id)
