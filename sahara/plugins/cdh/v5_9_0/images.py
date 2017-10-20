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

from sahara.plugins import images
from sahara.plugins import utils as plugin_utils


_validator = images.SaharaImageValidator.from_yaml(
    'plugins/cdh/v5_9_0/resources/images/image.yaml',
    resource_roots=['plugins/cdh/v5_9_0/resources/images'])


def get_image_arguments():
    return _validator.get_argument_list()


def pack_image(remote, test_only=False, image_arguments=None):
    _validator.validate(remote, test_only=test_only,
                        image_arguments=image_arguments)


def validate_images(cluster, test_only=False, image_arguments=None):
    image_arguments = get_image_arguments()
    if not test_only:
        instances = plugin_utils.get_instances(cluster)
    else:
        instances = plugin_utils.get_instances(cluster)[0]
    for instance in instances:
        with instance.remote() as r:
            _validator.validate(r, test_only=test_only,
                                image_arguments=image_arguments)
