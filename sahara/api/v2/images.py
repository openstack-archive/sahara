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

from sahara.api import acl
from sahara.service.api.v2 import images as api
from sahara.service import validation as v
from sahara.service.validations import images as v_images
import sahara.utils.api as u


rest = u.RestV2('images', __name__)


@rest.get('/images')
@acl.enforce("data-processing:images:get_all")
def images_list():
    tags = u.get_request_args().getlist('tags')
    name = u.get_request_args().get('name', None)
    return u.render(images=[i.dict for i in api.get_images(name, tags)])


@rest.get('/images/<image_id>')
@acl.enforce("data-processing:images:get")
@v.check_exists(api.get_image, id='image_id')
def images_get(image_id):
    return u.render(api.get_registered_image(id=image_id).wrapped_dict)


@rest.post('/images/<image_id>')
@acl.enforce("data-processing:images:register")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_register_schema, v_images.check_image_register)
def images_set(image_id, data):
    return u.render(api.register_image(image_id, **data).wrapped_dict)


@rest.delete('/images/<image_id>')
@acl.enforce("data-processing:images:unregister")
@v.check_exists(api.get_image, id='image_id')
def images_unset(image_id):
    api.unregister_image(image_id)
    return u.render()


@rest.post('/images/<image_id>/tag')
@acl.enforce("data-processing:images:add_tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema, v_images.check_tags)
def image_tags_add(image_id, data):
    return u.render(api.add_image_tags(image_id, **data).wrapped_dict)


@rest.post('/images/<image_id>/untag')
@acl.enforce("data-processing:images:remove_tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema)
def image_tags_delete(image_id, data):
    return u.render(api.remove_image_tags(image_id, **data).wrapped_dict)
