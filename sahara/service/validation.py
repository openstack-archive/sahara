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

import jsonschema
from oslo_utils import reflection

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.utils import api as u
from sahara.utils import api_validator


def validate(schema, *validators):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            request_data = u.request_data()
            try:
                if schema:
                    validator = api_validator.ApiValidator(schema)
                    validator.validate(request_data)
                if validators:
                    for validator in validators:
                        validator(**kwargs)
            except jsonschema.ValidationError as e:
                e.code = "VALIDATION_ERROR"
                return u.bad_request(e)
            except ex.SaharaException as e:
                return u.bad_request(e)
            except Exception as e:
                return u.internal_error(
                    500, "Error occurred during validation", e)

            return func(*args, **kwargs)

        return handler

    return decorator


def check_exists(get_func, *id_prop, **get_args):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            if id_prop and not get_args:
                get_args['id'] = id_prop[0]

            get_kwargs = {}
            for get_arg in get_args:
                get_kwargs[get_arg] = kwargs[get_args[get_arg]]

            obj = None
            try:
                obj = get_func(**get_kwargs)
            except Exception as e:
                cls_name = reflection.get_class_name(e, fully_qualified=False)
                if 'notfound' not in cls_name.lower():
                    raise e
            if obj is None:
                e = ex.NotFoundException(get_kwargs,
                                         _('Object with %s not found'))
                return u.not_found(e)

            return func(*args, **kwargs)

        return handler

    return decorator
