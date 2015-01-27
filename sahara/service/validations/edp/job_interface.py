# Copyright (c) 2015 Red Hat, Inc.
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

from oslo_utils import uuidutils
import six
from six.moves.urllib import parse as urlparse

import sahara.exceptions as e
from sahara.i18n import _
from sahara.service.validations.edp import base as b
from sahara.utils import edp


DATA_TYPE_STRING = "string"
DATA_TYPE_NUMBER = "number"
DATA_TYPE_DATA_SOURCE = "data_source"

DATA_TYPES = [DATA_TYPE_STRING,
              DATA_TYPE_NUMBER,
              DATA_TYPE_DATA_SOURCE]
DEFAULT_DATA_TYPE = DATA_TYPE_STRING


INTERFACE_ARGUMENT_SCHEMA = {
    "type": ["array", "null"],
    "uniqueItems": True,
    "items": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1
            },
            "description": {
                "type": ["string", "null"]
            },
            "mapping_type": {
                "type": "string",
                "enum": ["args", "configs", "params"]
            },
            "location": {
                "type": "string",
                "minLength": 1
            },
            "value_type": {
                "type": "string",
                "enum": DATA_TYPES,
                "default": "string"
            },
            "required": {
                "type": "boolean"
            },
            "default": {
                "type": ["string", "null"]
            }
        },
        "additionalProperties": False,
        "required": ["name", "mapping_type", "location", "required"]
    }
}


def _check_job_interface(data, interface):
    names = set(arg["name"] for arg in interface)
    if len(names) != len(interface):
        raise e.InvalidDataException(
            _("Name must be unique within the interface for any job."))

    mapping_types = set(arg["mapping_type"] for arg in interface)
    acceptable_types = edp.JOB_TYPES_ACCEPTABLE_CONFIGS[data["type"]]
    if any(m_type not in acceptable_types for m_type in mapping_types):
        args = {"mapping_types": str(list(acceptable_types)),
                "job_type": data["type"]}
        raise e.InvalidDataException(
            _("Only mapping types %(mapping_types)s are allowed for job type "
              "%(job_type)s.") % args)

    positional_args = [arg for arg in interface
                       if arg["mapping_type"] == "args"]
    if not all(six.text_type(arg["location"]).isnumeric()
               for arg in positional_args):
        raise e.InvalidDataException(
            _("Locations of positional arguments must be an unbroken integer "
              "sequence ascending from 0."))
    locations = set(int(arg["location"]) for arg in positional_args)
    if not all(i in locations for i in range(len(locations))):
        raise e.InvalidDataException(
            _("Locations of positional arguments must be an unbroken integer "
              "sequence ascending from 0."))

    not_required = (arg for arg in positional_args if not arg["required"])
    if not all(arg.get("default", None) for arg in not_required):
        raise e.InvalidDataException(
            _("Positional arguments must be given default values if they are "
              "not required."))

    mappings = ((arg["mapping_type"], arg["location"]) for arg in interface)
    if len(set(mappings)) != len(interface):
        raise e.InvalidDataException(
            _("The combination of mapping type and location must be unique "
              "within the interface for any job."))

    for arg in interface:
        if "value_type" not in arg:
            arg["value_type"] = DEFAULT_DATA_TYPE
        default = arg.get("default", None)
        if default is not None:
            _validate_value(arg["value_type"], default)


def check_job_interface(data, **kwargs):
    interface = data.get("interface", [])
    if interface:
        _check_job_interface(data, interface)


def _validate_data_source(value):
    if uuidutils.is_uuid_like(value):
        b.check_data_source_exists(value)
    else:
        if not urlparse.urlparse(value).scheme:
            raise e.InvalidDataException(
                _("Data source value '%s' is neither a valid data source ID "
                  "nor a valid URL.") % value)


def _validate_number(value):
    if not six.text_type(value).isnumeric():
        raise e.InvalidDataException(
            _("Value '%s' is not a valid number.") % value)


def _validate_string(value):
    if not isinstance(value, six.string_types):
        raise e.InvalidDataException(
            _("Value '%s' is not a valid string.") % value)


_value_type_validators = {
    DATA_TYPE_STRING: _validate_string,
    DATA_TYPE_NUMBER: _validate_number,
    DATA_TYPE_DATA_SOURCE: _validate_data_source
}


def _validate_value(type, value):
    _value_type_validators[type](value)


def check_execution_interface(data, job):
    job_int = {arg.name: arg for arg in job.interface}
    execution_int = data.get("interface", None)

    if not (job_int or execution_int):
        return
    if job_int and execution_int is None:
        raise e.InvalidDataException(
            _("An interface was specified with the template for this job. "
              "Please pass an interface map with this job (even if empty)."))

    execution_names = set(execution_int.keys())

    definition_names = set(job_int.keys())
    not_found_names = execution_names - definition_names
    if not_found_names:
        raise e.InvalidDataException(
            _("Argument names: %s were not found in the interface for this "
              "job.") % str(list(not_found_names)))

    required_names = {arg.name for arg in job.interface if arg.required}
    unset_names = required_names - execution_names
    if unset_names:
        raise e.InvalidDataException(_("Argument names: %s are required for "
                                       "this job.") % str(list(unset_names)))

    nonexistent = object()
    for name, value in six.iteritems(execution_int):
        arg = job_int[name]
        _validate_value(arg.value_type, value)
        if arg.mapping_type == "args":
            continue
        typed_configs = data.get("job_configs", {}).get(arg.mapping_type, {})
        config_value = typed_configs.get(arg.location, nonexistent)
        if config_value is not nonexistent and config_value != value:
            args = {"name": name,
                    "mapping_type": arg.mapping_type,
                    "location": arg.location}
            raise e.InvalidDataException(
                _("Argument '%(name)s' was passed both through the interface "
                  "and in location '%(mapping_type)s'.'%(location)s'. Please "
                  "pass this through either the interface or the "
                  "configuration maps, not both.") % args)
