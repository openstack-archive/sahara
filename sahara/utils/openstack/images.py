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

import copy

from glanceclient.v2 import images
from glanceclient.v2 import schemas
import six

from sahara import exceptions as exc


PROP_DESCR = '_sahara_description'
PROP_USERNAME = '_sahara_username'
PROP_TAG = '_sahara_tag_'
PROP_TAGS = '_all_tags'


def _get_all_tags(image_props):
    tags = []
    for key, value in image_props.iteritems():
        if key.startswith(PROP_TAG) and value:
            tags.append(key)
    return tags


def _ensure_tags(tags):
    if not tags:
        return []
    return [tags] if isinstance(tags, six.string_types) else tags


class SaharaImageModel(schemas.SchemaBasedModel):

    def __init__(self, *args, **kwargs):
        super(SaharaImageModel, self).__init__(*args, **kwargs)
        self.username = self._get_meta_prop(PROP_USERNAME, "")
        self.description = self._get_meta_prop(PROP_DESCR, "")
        self.tags = self._parse_tags()

    def _get_meta_prop(self, prop, default=None):
        if PROP_TAGS == prop:
            return _get_all_tags(self)
        return self.get(prop, default)

    def _parse_tags(self):
        tags = self._get_meta_prop(PROP_TAGS)
        return [t.replace(PROP_TAG, "") for t in tags]

    @property
    def dict(self):
        return self.to_dict()

    @property
    def wrapped_dict(self):
        return {'image': self.dict}

    def to_dict(self):
        result = copy.deepcopy(dict(self))
        if 'links' in result:
            del result['links']
        return result


class SaharaImageManager(images.Controller):
    """Manage :class:`SaharaImageModel` resources.

    This is an extended version of glance client's Controller with support of
    additional description and image tags stored as image properties.
    """
    def __init__(self, glance_client):
        schemas.SchemaBasedModel = SaharaImageModel
        super(SaharaImageManager, self).__init__(glance_client.http_client,
                                                 glance_client.schemas)

    def set_meta(self, image_id, meta):
        self.update(image_id, remove_props=None, **meta)

    def delete_meta(self, image_id, meta_list):
        self.update(image_id, remove_props=meta_list)

    def set_description(self, image_id, username, description=None):
        """Sets human-readable information for image.

        For example:
            Ubuntu 15 x64 with Java 1.7 and Apache Hadoop 2.1, ubuntu
        """
        meta = {PROP_USERNAME: username}
        if description:
            meta[PROP_DESCR] = description
        self.set_meta(image_id, meta)

    def unset_description(self, image_id):
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
            return [i for i in images_list if i.name == name]
        else:
            return images_list

    def get_registered_image(self, image_id):
        img = self.get(image_id)
        if img.username:
            return img
        else:
            raise exc.ImageNotRegistered(image_id)
