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

import re

import jsonschema
from oslo_utils import uuidutils
import six

from sahara.service.edp.job_binaries import manager as jb_manager


@jsonschema.FormatChecker.cls_checks('valid_name_hostname')
def validate_name_hostname_format(entry):
    if not isinstance(entry, six.string_types) or not entry:
        # should fail type or length validation
        return True

    res = re.match(r"^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]"
                   r"*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z]"
                   r"[A-Za-z0-9\-]*[A-Za-z0-9])$", entry)
    return res is not None


@jsonschema.FormatChecker.cls_checks('valid_name')
def validate_name_format(entry):
    if not isinstance(entry, six.string_types):
        # should fail type validation
        return True

    res = re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-_\.]*$", entry)
    return res is not None


@jsonschema.FormatChecker.cls_checks('valid_keypair_name')
def validate_keypair_name_format(entry):
    if not isinstance(entry, six.string_types):
        # should fail type validation
        return True

    # this follows the validation put forth by nova for keypair names
    res = re.match(r'^[a-zA-Z0-9\-_ ]+$', entry)
    return res is not None


@jsonschema.FormatChecker.cls_checks('valid_job_location')
def validate_job_location_format(entry):
    if not isinstance(entry, six.string_types):
        # should fail type validation
        return True

    return jb_manager.JOB_BINARIES \
                     .get_job_binary_by_url(entry) \
                     .validate_job_location_format(entry)


@jsonschema.FormatChecker.cls_checks('valid_tag')
def validate_valid_tag_format(entry):
    if not isinstance(entry, six.string_types):
        # should fail type validation
        return True

    res = re.match(r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-_]"
                   r"*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9]"
                   r"[A-Za-z0-9\-_]*[A-Za-z0-9])$", entry)
    return res is not None


@jsonschema.FormatChecker.cls_checks('uuid')
def validate_uuid_format(entry):
    if not isinstance(entry, six.string_types):
        # should fail type validation
        return True

    return uuidutils.is_uuid_like(entry)


@jsonschema.FormatChecker.cls_checks('posix_path')
def validate_posix_path(entry):
    if not isinstance(entry, six.string_types):
        # should fail type validation
        return True

    res = re.match("^(/([A-Z]|[a-z]|[0-9]|\-|_)+)+$", entry)
    return res is not None


class ConfigTypeMeta(type):
    def __instancecheck__(cls, instance):
        # configs should be dict
        if not isinstance(instance, dict):
            return False

        # check dict content
        for applicable_target, configs in six.iteritems(instance):
            # upper-level dict keys (applicable targets) should be strings
            if not isinstance(applicable_target, six.string_types):
                return False

            # upper-level dict values should be dicts
            if not isinstance(configs, dict):
                return False

            # check internal dict content
            for config_name, config_value in six.iteritems(configs):
                # internal dict keys should be strings
                if not isinstance(config_name, six.string_types):
                    return False

                # internal dict values should be strings or integers or bools
                if not isinstance(config_value,
                                  (six.string_types, six.integer_types)):
                    return False

        return True


class SimpleConfigTypeMeta(type):
    def __instancecheck__(cls, instance):
        # configs should be dict
        if not isinstance(instance, dict):
            return False

        # check dict content
        for conf_name, conf_value in six.iteritems(instance):
            # keys should be strings, values should be int, string or bool
            if not isinstance(conf_name, six.string_types):
                return False
            if not isinstance(conf_value,
                              (six.string_types, six.integer_types)):
                return False
        return True


@six.add_metaclass(ConfigTypeMeta)
class ConfigsType(dict):
    pass


@six.add_metaclass(SimpleConfigTypeMeta)
class SimpleConfigsType(dict):
    pass


class FlavorTypeMeta(type):
    def __instancecheck__(cls, instance):
        try:
            int(instance)
        except (ValueError, TypeError):
            return (isinstance(instance, six.string_types)
                    and uuidutils.is_uuid_like(instance))
        return (isinstance(instance, six.integer_types + six.string_types)
                and type(instance) != bool)


@six.add_metaclass(FlavorTypeMeta)
class FlavorType(object):
    pass


class ApiValidator(jsonschema.Draft4Validator):
    def __init__(self, schema):
        format_checker = jsonschema.FormatChecker()
        super(ApiValidator, self).__init__(
            schema, format_checker=format_checker, types={
                "configs": ConfigsType,
                "flavor": FlavorType,
                "simple_config": SimpleConfigsType,
            })
