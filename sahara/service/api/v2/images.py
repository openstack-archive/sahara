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
from sahara.utils.openstack import images as sahara_images


conductor = c.API


# Image Registry


def get_images(name, tags):
    return b.execute_with_retries(
        sahara_images.image_manager().list_registered, name, tags)


def get_image(**kwargs):
    if len(kwargs) == 1 and 'id' in kwargs:
        return b.execute_with_retries(
            sahara_images.image_manager().get, kwargs['id'])
    else:
        return b.execute_with_retries(
            sahara_images.image_manager().find, **kwargs)


def get_registered_image(id):
    return b.execute_with_retries(
        sahara_images.image_manager().get_registered_image, id)


def register_image(image_id, username, description=None):
    manager = sahara_images.image_manager()
    b.execute_with_retries(
        manager.set_image_info, image_id, username, description)
    return b.execute_with_retries(manager.get, image_id)


def unregister_image(image_id):
    manager = sahara_images.image_manager()
    b.execute_with_retries(manager.unset_image_info, image_id)
    return b.execute_with_retries(manager.get, image_id)


def get_image_tags(image_id):
    return b.execute_with_retries(
        sahara_images.image_manager().get, image_id).tags


def set_image_tags(image_id, tags):
    manager = sahara_images.image_manager()
    image_obj = b.execute_with_retries(manager.get, image_id)
    org_tags = frozenset(image_obj.tags)
    new_tags = frozenset(tags)

    to_add = list(new_tags - org_tags)
    to_remove = list(org_tags - new_tags)

    if to_add:
        b.execute_with_retries(manager.tag, image_id, to_add)

    if to_remove:
        b.execute_with_retries(manager.untag, image_id, to_remove)

    return b.execute_with_retries(manager.get, image_id)


def remove_image_tags(image_id):
    manager = sahara_images.image_manager()
    image_obj = b.execute_with_retries(manager.get, image_id)
    tags = image_obj.tags
    b.execute_with_retries(manager.untag, image_id, tags)
    return b.execute_with_retries(manager.get, image_id)
