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

import functools

import six

from sahara.conductor import resource
from sahara import exceptions as exc
from sahara.utils.openstack import glance


PROP_DESCR = '_sahara_description'
PROP_USERNAME = '_sahara_username'
PROP_TAG = '_sahara_tag_'
PROP_ALL_TAGS = '_all_tags'


def image_manager():
    return SaharaImageManager()


def wrap_entity(func):
    @functools.wraps(func)
    def handle(*args, **kwargs):
        res = func(*args, **kwargs)
        if isinstance(res, list):
            images = []
            for image in res:
                image = _transform_image_props(image)
                images.append(resource.ImageResource(image))
            return images
        else:
            res = _transform_image_props(res)
            return resource.ImageResource(res)
    return handle


def _get_all_tags(image_props):
    tags = []
    for key, value in image_props.iteritems():
        if key.startswith(PROP_TAG) and value:
            tags.append(key)
    return tags


def _get_meta_prop(image_props, prop, default=None):
    if PROP_ALL_TAGS == prop:
        return _get_all_tags(image_props)
    return image_props.get(prop, default)


def _parse_tags(image_props):
    tags = _get_meta_prop(image_props, PROP_ALL_TAGS)
    return [t.replace(PROP_TAG, "") for t in tags]


def _serialize_metadata(image):
    data = {}
    for key, value in image.iteritems():
        if key.startswith('_sahara') and value:
            data[key] = value
    return data


def _get_compat_values(image):
    data = {}
    # TODO(vgridnev): Drop these values from APIv2
    data["OS-EXT-IMG-SIZE:size"] = image.size
    data['metadata'] = _serialize_metadata(image)
    data["minDisk"] = getattr(image, 'min_disk', 0)
    data["minRam"] = getattr(image, 'min_ram', 0)
    data["progress"] = getattr(image, 'progress', 100)
    data["status"] = image.status.upper()
    data['created'] = image.created_at
    data['updated'] = image.updated_at
    return data


def _transform_image_props(image):
    data = _get_compat_values(image)
    data['username'] = _get_meta_prop(image, PROP_USERNAME, "")
    data['description'] = _get_meta_prop(image, PROP_DESCR, "")
    data['tags'] = _parse_tags(image)
    data['id'] = image.id
    data["name"] = image.name
    return data


def _ensure_tags(tags):
    if not tags:
        return []
    return [tags] if isinstance(tags, six.string_types) else tags


class SaharaImageManager(object):
    """SaharaImageManager

    This class is intermediate layer between sahara and glanceclient.v2.images.
    It provides additional sahara properties for image such as description,
    image tags and image username.
    """
    def __init__(self):
        self.client = glance.client().images

    @wrap_entity
    def get(self, image_id):
        image = self.client.get(image_id)
        return image

    @wrap_entity
    def find(self, **kwargs):
        images = self.client.list(**kwargs)
        num_matches = len(images)
        if num_matches == 0:
            raise exc.NotFoundException(kwargs, "No images matching %s.")
        elif num_matches > 1:
            raise exc.NoUniqueMatchException(response=images, query=kwargs)
        else:
            return images[0]

    @wrap_entity
    def list(self):
        return list(self.client.list())

    def set_meta(self, image_id, meta):
        self.client.update(image_id, remove_props=None, **meta)

    def delete_meta(self, image_id, meta_list):
        self.client.update(image_id, remove_props=meta_list)

    def set_image_info(self, image_id, username, description=None):
        """Sets human-readable information for image.

        For example:
            Ubuntu 15 x64 with Java 1.7 and Apache Hadoop 2.1, ubuntu
        """
        meta = {PROP_USERNAME: username}
        if description:
            meta[PROP_DESCR] = description
        self.set_meta(image_id, meta)

    def unset_image_info(self, image_id):
        """Unsets all Sahara-related information.

        It removes username, description and tags from the specified image.
        """
        image = self.get(image_id)
        meta = [PROP_TAG + tag for tag in image.tags]
        if image.description is not None:
            meta += [PROP_DESCR]
        if image.username is not None:
            meta += [PROP_USERNAME]
        self.delete_meta(image_id, meta)

    def tag(self, image_id, tags):
        """Adds tags to the specified image."""
        tags = _ensure_tags(tags)
        self.set_meta(image_id, {PROP_TAG + tag: 'True' for tag in tags})

    def untag(self, image_id, tags):
        """Removes tags from the specified image."""
        tags = _ensure_tags(tags)
        self.delete_meta(image_id, [PROP_TAG + tag for tag in tags])

    def list_by_tags(self, tags):
        """Returns images having all of the specified tags."""
        tags = _ensure_tags(tags)
        return [i for i in self.list() if set(tags).issubset(i.tags)]

    def list_registered(self, name=None, tags=None):
        tags = _ensure_tags(tags)
        images_list = [i for i in self.list()
                       if i.username and set(tags).issubset(i.tags)]
        if name:
            return [i for i in images_list if name in i.name]
        else:
            return images_list

    def get_registered_image(self, image_id):
        img = self.get(image_id)
        if img.username:
            return img
        else:
            raise exc.ImageNotRegistered(image_id)
