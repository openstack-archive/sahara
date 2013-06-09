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

from novaclient.v1_1 import images


PROP_DESCR = '_savanna_description'
PROP_USERNAME = '_savanna_username'
PROP_TAG = '_savanna_tag_'


def _iter_tags(meta):
    for key in meta:
        if key.startswith(PROP_TAG) and meta[key]:
            yield key[len(PROP_TAG):]


def _ensure_tags(tags):
    if not tags:
        return []
    return [tags] if type(tags) in [str, unicode] else tags


class SavannaImage(images.Image):
    def __init__(self, manager, info, loaded=False):
        info['description'] = info.get('metadata', {}).get(PROP_DESCR)
        info['username'] = info.get('metadata', {}).get(PROP_USERNAME)
        info['tags'] = [tag for tag in _iter_tags(info.get('metadata', {}))]
        super(SavannaImage, self).__init__(manager, info, loaded)

    def tag(self, tags):
        self.manager.tag(self, tags)

    def untag(self, tags):
        self.manager.untag(self, tags)

    def set_description(self, description=None, username=None):
        self.manager.set_description(self, description, username)

    @property
    def dict(self):
        return self.to_dict()

    @property
    def wrapped_dict(self):
        return {'image': self.dict}

    def to_dict(self):
        result = self._info.copy()
        del result['links']
        return result


class SavannaImageManager(images.ImageManager):
    """Manage :class:`SavannaImage` resources.

    This is an extended version of nova client's ImageManager with support of
    additional description and image tags stored in images' meta.
    """
    resource_class = SavannaImage

    def set_description(self, image, description, username):
        """Sets human-readable information for image.

        For example:

            Ubuntu 13.04 x64 with Java 1.7u21 and Apache Hadoop 1.1.1, ubuntu
        """
        self.set_meta(image, {
            PROP_DESCR: description,
            PROP_USERNAME: username,
        })

    def tag(self, image, tags):
        """Adds tags to the specified image."""
        tags = _ensure_tags(tags)

        self.set_meta(image, dict((PROP_TAG + tag, True) for tag in tags))

    def untag(self, image, tags):
        """Removes tags from the specified image."""
        tags = _ensure_tags(tags)

        self.delete_meta(image, [PROP_TAG + tag for tag in tags])

    def list_by_tags(self, tags):
        """Returns images having all of the specified tags."""
        tags = _ensure_tags(tags)
        return [i for i in self.list() if set(tags).issubset(i.tags)]

    def list_registered(self, tags=None):
        tags = _ensure_tags(tags)
        return [i for i in self.list()
                if i.username and set(tags).issubset(i.tags)]
