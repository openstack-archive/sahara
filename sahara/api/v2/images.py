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
@acl.enforce("data-processing:image:list")
@v.validate_request_params(['name', 'tags', 'username'])
def images_list():
    tags = u.get_request_args().getlist('tags')
    name = u.get_request_args().get('name', None)
    return u.render(images=[i.dict for i in api.get_images(name, tags)])


@rest.get('/images/<image_id>')
@acl.enforce("data-processing:image:get")
@v.check_exists(api.get_image, id='image_id')
@v.validate_request_params([])
def images_get(image_id):
    return u.render(api.get_registered_image(id=image_id).wrapped_dict)


@rest.post('/images/<image_id>')
@acl.enforce("data-processing:image:register")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_register_schema, v_images.check_image_register)
@v.validate_request_params([])
def images_set(image_id, data):
    return u.render(api.register_image(image_id, **data).wrapped_dict)


@rest.delete('/images/<image_id>')
@acl.enforce("data-processing:image:unregister")
@v.check_exists(api.get_image, id='image_id')
@v.validate_request_params([])
def images_unset(image_id):
    api.unregister_image(image_id)
    return u.render()


@rest.get('/images/<image_id>/tags')
@acl.enforce("data-processing:image:get-tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate_request_params([])
def image_tags_get(image_id):
    return u.render(api.get_image_tags(image_id))


@rest.put('/images/<image_id>/tags', status_code=200)
@acl.enforce("data-processing:image:set-tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema, v_images.check_tags)
@v.validate_request_params([])
def image_tags_update(image_id, data):
    return u.render(api.set_image_tags(image_id, **data).wrapped_dict)


@rest.delete('/images/<image_id>/tags')
@acl.enforce("data-processing:image:remove-tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate_request_params([])
def image_tags_delete(image_id):
    api.remove_image_tags(image_id)
    return u.render()
