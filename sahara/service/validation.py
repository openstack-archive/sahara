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

from oslo_utils import reflection

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.utils import api as u
from sahara.utils import api_validator
from sahara.utils import types


def _get_path(path):
    if path:
        path_string = path[0]
        for x in path[1:]:
            path_string += '[%s]' % str(x)
        return path_string + ': '
    return ''


def _generate_error(errors):
    message = [_get_path(list(e.path)) + e.message for e in errors]
    if message:
        return ex.SaharaException('\n'.join(message), "VALIDATION_ERROR")


def validate_pagination_limit():
    request_args = u.get_request_args()
    if 'limit' in request_args:
        if types.is_int(request_args['limit']):
            if not int(request_args['limit']) > 0:
                raise ex.SaharaException(
                    _("'limit' must be positive integer"), 400)
        else:
            raise ex.SaharaException(
                _("'limit' must be positive integer"), 400)


def get_sorting_field():
    request_args = u.get_request_args()
    if 'sort_by' in request_args:
        sort_by = request_args['sort_by']
        if sort_by:
            sort_by = sort_by[1:] if sort_by[0] == '-' else sort_by
            return sort_by
    return None


def validate_sorting_clusters():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'plugin_name', 'hadoop_version',
                     'status']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_cluster_templates():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'plugin_name', 'hadoop_version',
                     'created_at', 'updated_at']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_node_group_templates():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'plugin_name', 'hadoop_version',
                     'created_at', 'updated_at']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_job_binaries():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'created_at', 'updated_at']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_job_binary_internals():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'created_at', 'updated_at']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_data_sources():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'type', 'created_at', 'updated_at']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_jobs():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'name', 'type', 'created_at', 'updated_at']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate_sorting_job_executions():
    field = get_sorting_field()
    if field is None:
        return
    if field not in ['id', 'job_template', 'cluster', 'status']:
        raise ex.SaharaException(
            _("Unknown field for sorting %s") % field, 400)


def validate(schema, *validators):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            request_data = u.request_data()
            try:
                if schema:
                    validator = api_validator.ApiValidator(schema)
                    errors = validator.iter_errors(request_data)
                    error = _generate_error(errors)
                    if error:
                        return u.bad_request(error)
                if validators:
                    for validator in validators:
                        validator(**kwargs)
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

            if 'marker' in id_prop:
                if 'marker' not in u.get_request_args():
                    return func(*args, **kwargs)
                kwargs['marker'] = u.get_request_args()['marker']

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
            if 'marker' in kwargs:
                del(kwargs['marker'])
            return func(*args, **kwargs)

        return handler

    return decorator


def validate_request_params(supported_params):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            pagination_params = ['marker', 'limit', 'sort_by']
            func_name = func.__name__
            params = u.get_request_args()
            for param in params.keys():
                if (param not in supported_params and
                        param not in pagination_params):
                    return u.invalid_param_error(
                        400,
                        'The only valid params for %s are %s and %s' % (
                            func_name, supported_params, pagination_params))
            return func(*args, **kwargs)
        return handler
    return decorator
