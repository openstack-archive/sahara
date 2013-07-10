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

from savanna import exceptions as ex
import savanna.openstack.common.exception as os_ex
from savanna.utils import api as u
from savanna.utils import api_validator


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
            except jsonschema.ValidationError, e:
                e.code = "VALIDATION_ERROR"
                return u.bad_request(e)
            except ex.SavannaException, e:
                return u.bad_request(e)
            except os_ex.MalformedRequestBody, e:
                e.code = "MALFORMED_REQUEST_BODY"
                return u.bad_request(e)
            except Exception, e:
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
            except Exception, e:
                if 'notfound' not in e.__class__.__name__.lower():
                    raise e
            if obj is None:
                e = ex.NotFoundException(get_kwargs,
                                         'Object with %s not found')
                return u.not_found(e)

            return func(*args, **kwargs)

        return handler

    return decorator
