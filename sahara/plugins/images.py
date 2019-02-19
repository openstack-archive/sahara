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

from oslo_utils import uuidutils

import abc
import collections
import copy
import functools
import itertools
from os import path

import jsonschema
import six
import yaml

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import exceptions as p_ex
from sahara.plugins import utils


def transform_exception(from_type, to_type, transform_func=None):
    """Decorator to transform exception types.

    :param from_type: The type of exception to catch and transform.
    :param to_type: The type of exception to raise instead.
    :param transform_func: A function to transform from_type into
        to_type, which must be of the form func(exc, to_type).
        Defaults to:
        lambda exc, new_type: new_type(exc.message)
    """
    if not transform_func:
        transform_func = lambda exc, new_type: new_type(exc.message)

    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except from_type as exc:
                raise transform_func(exc, to_type)
        return handler
    return decorator


def validate_instance(instance, validators, test_only=False, **kwargs):
    """Runs all validators against the specified instance.

    :param instance: An instance to validate.
    :param validators: A sequence of ImageValidators.
    :param test_only: If true, all validators will only verify that a
        desired state is present, and fail if it is not. If false, all
        validators will attempt to enforce the desired state if possible,
        and succeed if this enforcement succeeds.
    :raises ImageValidationError: If validation fails.
    """
    with instance.remote() as remote:
        for validator in validators:
            validator.validate(remote, test_only=test_only, **kwargs)


class ImageArgument(object):
    """An argument used by an image manifest."""

    SPEC_SCHEMA = {
        "type": "object",
        "items": {
            "type": "object",
            "properties": {
                "target_variable": {
                    "type": "string",
                    "minLength": 1
                },
                "description": {
                    "type": "string",
                    "minLength": 1
                },
                "default": {
                    "type": "string",
                    "minLength": 1
                },
                "required": {
                    "type": "boolean",
                    "minLength": 1
                },
                "choices": {
                    "type": "array",
                    "minLength": 1,
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
    }

    @classmethod
    def from_spec(cls, spec):
        """Constructs and returns a set of arguments from a specification.

        :param spec: The specification for the argument set.
        :return: A dict of arguments built to the specification.
        """

        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        arguments = {name: cls(name,
                               arg.get('description'),
                               arg.get('default'),
                               arg.get('required'),
                               arg.get('choices'))
                     for name, arg in six.iteritems(spec)}
        reserved_names = ['distro', 'test_only']
        for name, arg in six.iteritems(arguments):
            if name in reserved_names:
                raise p_ex.ImageValidationSpecificationError(
                    _("The following argument names are reserved: "
                      "{names}").format(reserved_names))
            if not arg.default and not arg.required:
                raise p_ex.ImageValidationSpecificationError(
                    _("Argument {name} is not required and must specify a "
                      "default value.").format(name=arg.name))
            if arg.choices and arg.default and arg.default not in arg.choices:
                raise p_ex.ImageValidationSpecificationError(
                    _("Argument {name} specifies a default which is not one "
                      "of its choices.").format(name=arg.name))
        return arguments

    def __init__(self, name, description=None, default=None, required=False,
                 choices=None):
        self.name = name
        self.description = description
        self.default = default
        self.required = required
        self.choices = choices


@six.add_metaclass(abc.ABCMeta)
class ImageValidator(object):
    """Validates the image spawned to an instance via a set of rules."""

    @abc.abstractmethod
    def validate(self, remote, test_only=False, **kwargs):
        """Validates the image.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :raises ImageValidationError: If validation fails.
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class SaharaImageValidatorBase(ImageValidator):
    """Base class for Sahara's native image validation."""

    DISTRO_KEY = 'distro'
    TEST_ONLY_KEY = 'test_only'

    ORDERED_VALIDATORS_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "minProperties": 1,
            "maxProperties": 1
        }
    }

    _DISTRO_FAMILES = {
        'centos': 'redhat',
        'centos7': 'redhat',
        'fedora': 'redhat',
        'redhat': 'redhat',
        'rhel': 'redhat',
        'redhatenterpriseserver': 'redhat',
        'ubuntu': 'debian'
    }

    @staticmethod
    def get_validator_map(custom_validator_map=None):
        """Gets the map of validator name token to validator class.

        :param custom_validator_map: A map of validator names and classes to
            add to the ones Sahara provides by default. These will take
            precedence over the base validators in case of key overlap.
        :return: A map of validator names and classes.
        """
        default_validator_map = {
            'package': SaharaPackageValidator,
            'script': SaharaScriptValidator,
            'copy_script': SaharaCopyScriptValidator,
            'any': SaharaAnyValidator,
            'all': SaharaAllValidator,
            'os_case': SaharaOSCaseValidator,
            'argument_case': SaharaArgumentCaseValidator,
            'argument_set': SaharaArgumentSetterValidator,
        }
        if custom_validator_map:
            default_validator_map.update(custom_validator_map)
        return default_validator_map

    @classmethod
    def from_yaml(cls, yaml_path, validator_map=None, resource_roots=None,
                  package='sahara'):
        """Constructs and returns a validator from the provided yaml file.

        :param yaml_path: The relative path to a yaml file.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A SaharaImageValidator built to the yaml specification.
        """
        validator_map = validator_map or {}
        resource_roots = resource_roots or []
        file_text = utils.get_file_text(yaml_path, package)
        spec = yaml.safe_load(file_text)
        validator_map = cls.get_validator_map(validator_map)
        return cls.from_spec(spec, validator_map, resource_roots, package)

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Constructs and returns a validator from a specification object.

        :param spec: The specification for the validator.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A validator built to the specification.
        """
        pass

    @classmethod
    def from_spec_list(cls, specs, validator_map, resource_roots,
                       package='sahara'):
        """Constructs a list of validators from a list of specifications.

        :param specs: A list of validator specifications, each of which
            will be a dict of size 1, where the key represents the validator
            type and the value respresents its specification.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A list of validators.
        """
        validators = []
        for spec in specs:
            validator_class, validator_spec = cls.get_class_from_spec(
                spec, validator_map)
            validators.append(validator_class.from_spec(
                validator_spec, validator_map, resource_roots, package))
        return validators

    @classmethod
    def get_class_from_spec(cls, spec, validator_map):
        """Gets the class and specification from a validator dict.

        :param spec: A validator specification including its type: a dict of
            size 1, where the key represents the validator type and the value
            respresents its configuration.
        :param validator_map: A map of validator name to class.
        :return: A tuple of validator class and configuration.
        """
        key, value = list(six.iteritems(spec))[0]
        validator_class = validator_map.get(key, None)
        if not validator_class:
            raise p_ex.ImageValidationSpecificationError(
                _("Validator type %s not found.") % validator_class)
        return validator_class, value

    class ValidationAttemptFailed(object):
        """An object representing a failed validation attempt.

        Primarily for use by the SaharaAnyValidator, which must aggregate
        failures for error exposition purposes.
        """
        def __init__(self, exception):
            self.exception = exception

        def __bool__(self):
            return False

        def __nonzero__(self):
            return False

    def try_validate(self, remote, test_only=False,
                     image_arguments=None, **kwargs):
        """Attempts to validate, but returns rather than raising on failure.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :return: True if successful, ValidationAttemptFailed object if failed.
        """
        try:
            self.validate(
                remote, test_only=test_only,
                image_arguments=image_arguments, **kwargs)
            return True
        except p_ex.ImageValidationError as exc:
            return self.ValidationAttemptFailed(exc)


class SaharaImageValidator(SaharaImageValidatorBase):
    """The root of any tree of SaharaImageValidators.

    This validator serves as the root of the tree for SaharaImageValidators,
    and provides any needed initialization (such as distro retrieval.)
    """

    SPEC_SCHEMA = {
        "title": "SaharaImageValidator",
        "type": "object",
        "properties": {
            "validators": SaharaImageValidatorBase.ORDERED_VALIDATORS_SCHEMA
        },
        "required": ["validators"]
    }

    def get_argument_list(self):
        return [argument for name, argument
                in six.iteritems(self.arguments)]

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Constructs and returns a validator from a specification object.

        :param spec: The specification for the validator: a dict containing
            the key "validators", which contains a list of validator
            specifications.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A SaharaImageValidator containing all specified validators.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        arguments_spec = spec.get('arguments', {})
        arguments = ImageArgument.from_spec(arguments_spec)
        validators_spec = spec['validators']
        validator = SaharaAllValidator.from_spec(
            validators_spec, validator_map, resource_roots, package)
        return cls(validator, arguments)

    def __init__(self, validator, arguments):
        """Constructor method.

        :param validator: A SaharaAllValidator containing the specified
            validators.
        """
        self.validator = validator
        self.validators = validator.validators
        self.arguments = arguments

    @transform_exception(ex.RemoteCommandException, p_ex.ImageValidationError)
    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate the image.

        Before deferring to contained validators, performs one-time setup
        steps such as distro discovery.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :raises ImageValidationError: If validation fails.
        """
        argument_values = {}
        for name, argument in six.iteritems(self.arguments):
            if name not in image_arguments:
                if argument.required:
                    raise p_ex.ImageValidationError(
                        _("Argument {name} is required for image "
                          "processing.").format(name=name))
                else:
                    argument_values[name] = argument.default
            else:
                value = image_arguments[name]
                choices = argument.choices
                if choices and value not in choices:
                    raise p_ex.ImageValidationError(
                        _("Value for argument {name} must be one of "
                          "{choices}.").format(name=name, choices=choices))
                else:
                    argument_values[name] = value
        argument_values[self.DISTRO_KEY] = remote.get_os_distrib()
        self.validator.validate(remote, test_only=test_only,
                                image_arguments=argument_values)


class SaharaPackageValidator(SaharaImageValidatorBase):
    """A validator that checks package installation state on the instance."""

    class Package(object):

        def __init__(self, name, version=None):
            self.name = name
            self.version = version

        def __str__(self):
            return ("%s-%s" % (self.name, self.version)
                    if self.version else self.name)

    _SINGLE_PACKAGE_SCHEMA = {
        "oneOf": [
            {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 1,
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "version": {
                            "type": "string",
                            "minLength": 1
                        },
                    }
                },
            },
            {
                "type": "string",
                "minLength": 1
            }
        ]
    }

    SPEC_SCHEMA = {
        "title": "SaharaPackageValidator",
        "oneOf": [
            _SINGLE_PACKAGE_SCHEMA,
            {
                "type": "array",
                "items": _SINGLE_PACKAGE_SCHEMA,
                "minLength": 1
            }
        ]
    }

    @classmethod
    def _package_from_spec(cls, spec):
        """Builds a single package object from a specification.

        :param spec: May be a string or single-length dictionary of name to
            configuration values.
        :return: A package object.
        """
        if isinstance(spec, six.string_types):
            return cls.Package(spec, None)
        else:
            package, properties = list(six.iteritems(spec))[0]
            version = properties.get('version', None)
            return cls.Package(package, version)

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds a package validator from a specification.

        :param spec: May be a string, a single-length dictionary of name to
            configuration values, or a list containing any number of either or
            both of the above. Configuration values may include:
            version: The version of the package to check and/or install.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A validator that will check that the specified package or
            packages are installed.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        packages = ([cls._package_from_spec(package_spec)
                     for package_spec in spec]
                    if isinstance(spec, list)
                    else [cls._package_from_spec(spec)])
        return cls(packages)

    def __init__(self, packages):
        self.packages = packages

    @transform_exception(ex.RemoteCommandException, p_ex.ImageValidationError)
    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate package installation on the image.

        Even if test_only=False, attempts to verify previous package
        installation offline before using networked tools to validate or
        install new packages.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :raises ImageValidationError: If validation fails.
        """
        env_distro = image_arguments[self.DISTRO_KEY]
        env_family = self._DISTRO_FAMILES[env_distro]
        check, install = self._DISTRO_TOOLS[env_family]
        if not env_family:
            raise p_ex.ImageValidationError(
                _("Unknown distro: cannot verify or install packages."))
        try:
            check(self, remote)
        except (ex.SubprocessException, ex.RemoteCommandException,
                RuntimeError):
            if not test_only:
                install(self, remote)
                check(self, remote)
            else:
                raise

    def _dpkg_check(self, remote):
        check_cmd = ("dpkg -s %s" %
                     " ".join(str(package) for package in self.packages))
        return _sudo(remote, check_cmd)

    def _rpm_check(self, remote):
        check_cmd = ("rpm -q %s" %
                     " ".join(str(package) for package in self.packages))
        return _sudo(remote, check_cmd)

    def _yum_install(self, remote):
        install_cmd = (
            "yum install -y %s" %
            " ".join(str(package) for package in self.packages))
        _sudo(remote, install_cmd)

    def _apt_install(self, remote):
        install_cmd = (
            "DEBIAN_FRONTEND=noninteractive apt-get -y install %s" %
            " ".join(str(package) for package in self.packages))
        return _sudo(remote, install_cmd)

    _DISTRO_TOOLS = {
        "redhat": (_rpm_check, _yum_install),
        "debian": (_dpkg_check, _apt_install)
    }


class SaharaScriptValidator(SaharaImageValidatorBase):
    """A validator that runs a script on the instance."""

    _DEFAULT_ENV_VARS = [SaharaImageValidatorBase.TEST_ONLY_KEY,
                         SaharaImageValidatorBase.DISTRO_KEY]

    SPEC_SCHEMA = {
        "title": "SaharaScriptValidator",
        "oneOf": [
            {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 1,
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "env_vars": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "output": {
                            "type": "string",
                            "minLength": 1
                        },
                        "inline": {
                            "type": "string",
                            "minLength": 1
                        }
                    },
                }
            },
            {
                "type": "string"
            }
        ]
    }

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds a script validator from a specification.

        :param spec: May be a string or a single-length dictionary of name to
            configuration values. Configuration values include:
            env_vars: A list of environment variable names to send to the
                script.
            output: A key into which to put the stdout of the script in the
                image_arguments of the validation run.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A validator that will run a script on the image.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)

        script_contents = None
        if isinstance(spec, six.string_types):
            script_path = spec
            env_vars, output_var = cls._DEFAULT_ENV_VARS, None
        else:
            script_path, properties = list(six.iteritems(spec))[0]
            env_vars = cls._DEFAULT_ENV_VARS + properties.get('env_vars', [])
            output_var = properties.get('output', None)
            script_contents = properties.get('inline')

        if not script_contents:
            for root in resource_roots:
                file_path = path.join(root, script_path)
                script_contents = utils.try_get_file_text(file_path, package)
                if script_contents:
                    break

        if not script_contents:
            raise p_ex.ImageValidationSpecificationError(
                _("Script %s not found in any resource roots.") % script_path)

        return SaharaScriptValidator(script_contents, env_vars, output_var)

    def __init__(self, script_contents, env_vars=None, output_var=None):
        """Constructor method.

        :param script_contents: A string representation of the script.
        :param env_vars: A list of environment variables to send to the
            script.
        :param output_var: A key into which to put the stdout of the script in
            the image_arguments of the validation run.
        :return: A SaharaScriptValidator.
        """
        self.script_contents = script_contents
        self.env_vars = env_vars or []
        self.output_var = output_var

    @transform_exception(ex.RemoteCommandException, p_ex.ImageValidationError)
    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate by running a script on the image.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
            Note that the key SIV_TEST_ONLY will be set to 1 if the script
            should test_only and 0 otherwise; all scripts should act on this
            input if possible. The key SIV_DISTRO will also contain the
            distro representation, per `lsb_release -is`.
        :raises ImageValidationError: If validation fails.
        """

        arguments = copy.deepcopy(image_arguments)
        arguments[self.TEST_ONLY_KEY] = 1 if test_only else 0
        script = "\n".join(["%(env_vars)s",
                            "%(script)s"])
        env_vars = "\n".join("export %s=%s" % (key, value) for (key, value)
                             in six.iteritems(arguments)
                             if key in self.env_vars)
        script = script % {"env_vars": env_vars,
                           "script": self.script_contents.decode('utf-8')}
        path = '/tmp/%s.sh' % uuidutils.generate_uuid()
        remote.write_file_to(path, script, run_as_root=True)
        _sudo(remote, 'chmod +x %s' % path)
        code, stdout = _sudo(remote, path)
        if self.output_var:
            image_arguments[self.output_var] = stdout


class SaharaCopyScriptValidator(SaharaImageValidatorBase):
    """A validator that copy a script to the instance."""

    SPEC_SCHEMA = {
        "title": "SaharaCopyScriptValidator",
        "oneOf": [
            {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 1,
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "minLength": 1
                        },
                        "inline": {
                            "type": "string",
                            "minLength": 1
                        }
                    },
                }
            },
            {
                "type": "string"
            }
        ]
    }

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds a copy script validator from a specification.

        :param spec: May be a string or a single-length dictionary of name to
            configuration values. Configuration values include:
            env_vars: A list of environment variable names to send to the
                script.
            output: A key into which to put the stdout of the script in the
                image_arguments of the validation run.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A validator that will copy a script to the image.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)

        script_contents = None
        if isinstance(spec, six.string_types):
            script_path = spec
            output_var = None
        else:
            script_path, properties = list(six.iteritems(spec))[0]
            output_var = properties.get('output', None)
            script_contents = properties.get('inline')

        if not script_contents:
            for root in resource_roots:
                file_path = path.join(root, script_path)
                script_contents = utils.try_get_file_text(file_path, package)
                if script_contents:
                    break
        script_name = script_path.split('/')[2]

        if not script_contents:
            raise p_ex.ImageValidationSpecificationError(
                _("Script %s not found in any resource roots.") % script_path)

        return SaharaCopyScriptValidator(script_contents, script_name,
                                         output_var)

    def __init__(self, script_contents, script_name, output_var=None):
        """Constructor method.

        :param script_contents: A string representation of the script.
        :param output_var: A key into which to put the stdout of the script in
            the image_arguments of the validation run.
        :return: A SaharaScriptValidator.
        """
        self.script_contents = script_contents
        self.script_name = script_name
        self.output_var = output_var

    @transform_exception(ex.RemoteCommandException, p_ex.ImageValidationError)
    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate by running a script on the image.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
            Note that the key SIV_TEST_ONLY will be set to 1 if the script
            should test_only and 0 otherwise; all scripts should act on this
            input if possible. The key SIV_DISTRO will also contain the
            distro representation, per `lsb_release -is`.
        :raises ImageValidationError: If validation fails.
        """

        arguments = copy.deepcopy(image_arguments)
        arguments[self.TEST_ONLY_KEY] = 1 if test_only else 0
        script = "\n".join(["%(script)s"])
        script = script % {"script": self.script_contents}
        path = '/tmp/%s' % self.script_name
        remote.write_file_to(path, script, run_as_root=True)


@six.add_metaclass(abc.ABCMeta)
class SaharaAggregateValidator(SaharaImageValidatorBase):
    """An abstract class representing an ordered list of other validators."""

    SPEC_SCHEMA = SaharaImageValidator.ORDERED_VALIDATORS_SCHEMA

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds the aggregate validator from a specification.

        :param spec: A list of validator definitions, each of which is a
            single-length dictionary of name to configuration values.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: An aggregate validator.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        validators = cls.from_spec_list(spec, validator_map, resource_roots,
                                        package)
        return cls(validators)

    def __init__(self, validators):
        self.validators = validators


class SaharaAnyValidator(SaharaAggregateValidator):
    """A list of validators, only one of which must succeed."""

    def _try_all(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        results = []
        for validator in self.validators:
            result = validator.try_validate(remote, test_only=test_only,
                                            image_arguments=image_arguments,
                                            **kwargs)
            results.append(result)
            if result:
                break
        return results

    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate any of the contained validators.

        Note that if test_only=False, this validator will first run all
        contained validators using test_only=True, and succeed immediately
        should any pass validation. If all fail, it will only then run them
        using test_only=False, and again succeed immediately should any pass.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :raises ImageValidationError: If validation fails.
        """
        results = self._try_all(remote, test_only=True,
                                image_arguments=image_arguments)
        if not test_only and not any(results):
            results = self._try_all(remote, test_only=False,
                                    image_arguments=image_arguments)
        if not any(results):
            raise p_ex.AllValidationsFailedError(result.exception for result
                                                 in results)


class SaharaAllValidator(SaharaAggregateValidator):
    """A list of validators, all of which must succeed."""

    def validate(self, remote, test_only=False, image_arguments=None,
                 **kwargs):
        """Attempts to validate all of the contained validators.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :raises ImageValidationError: If validation fails.
        """
        for validator in self.validators:
            validator.validate(remote, test_only=test_only,
                               image_arguments=image_arguments)


class SaharaOSCaseValidator(SaharaImageValidatorBase):
    """A validator which will take different actions depending on distro."""

    _distro_tuple = collections.namedtuple('Distro', ['distro', 'validator'])

    SPEC_SCHEMA = {
        "type": "array",
        "minLength": 1,
        "items": {
            "type": "object",
            "minProperties": 1,
            "maxProperties": 1,
            "additionalProperties":
                SaharaImageValidator.ORDERED_VALIDATORS_SCHEMA,
        }
    }

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds an os_case validator from a specification.

        :param spec: A list of single-length dictionaries. The key of each is
            a distro or family name and the value under each key is a list of
            validators (all of which must succeed.)
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A SaharaOSCaseValidator.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        distros = itertools.chain(*(six.iteritems(distro_spec)
                                    for distro_spec in spec))
        distros = [
            cls._distro_tuple(key, SaharaAllValidator.from_spec(
                value, validator_map, resource_roots, package))
            for (key, value) in distros]
        return cls(distros)

    def __init__(self, distros):
        """Constructor method.

        :param distros: A list of distro tuples (distro, list of validators).
        """
        self.distros = distros

    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate depending on distro.

        May match the OS by specific distro or by family (centos may match
        "centos" or "redhat", for instance.) If multiple keys match the
        distro, only the validators under the first matched key will be run.
        If no keys match, no validators are run, and validation proceeds.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :raises ImageValidationError: If validation fails.
        """
        env_distro = image_arguments[self.DISTRO_KEY]
        family = self._DISTRO_FAMILES.get(env_distro)
        matches = {env_distro, family} if family else {env_distro}
        for distro, validator in self.distros:
            if distro in matches:
                validator.validate(
                    remote, test_only=test_only,
                    image_arguments=image_arguments)
                break


class SaharaArgumentCaseValidator(SaharaImageValidatorBase):
    """A validator which will take different actions depending on distro."""

    SPEC_SCHEMA = {
        "type": "object",
        "properties": {
            "argument_name": {
                "type": "string",
                "minLength": 1
            },
            "cases": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties":
                    SaharaImageValidator.ORDERED_VALIDATORS_SCHEMA,
            },
        },
        "additionalProperties": False,
        "required": ["argument_name", "cases"]
    }

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds an argument_case validator from a specification.

        :param spec: A dictionary with two items: "argument_name", containing
            a string indicating the argument to be checked, and "cases", a
            dictionary. The key of each item in the dictionary is a value
            which may or may not match the argument value, and the value is
            a list of validators to be run in case it does.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A SaharaArgumentCaseValidator.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        argument_name = spec['argument_name']
        cases = {key: SaharaAllValidator.from_spec(
                 value, validator_map, resource_roots, package)
                 for key, value in six.iteritems(spec['cases'])}

        return cls(argument_name, cases)

    def __init__(self, argument_name, cases):
        """Constructor method.

        :param argument_name: The name of an argument.
        :param cases: A dictionary of possible argument value to a
            sub-validator to run in case of a match.
        """
        self.argument_name = argument_name
        self.cases = cases

    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate depending on argument value.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        :raises ImageValidationError: If validation fails.
        """
        arg = self.argument_name
        if arg not in image_arguments:
            raise p_ex.ImageValidationError(
                _("Argument {name} not found.").format(name=arg))
        value = image_arguments[arg]
        if value in self.cases:
            self.cases[value].validate(
                remote, test_only=test_only,
                image_arguments=image_arguments)


class SaharaArgumentSetterValidator(SaharaImageValidatorBase):
    """A validator which sets a specific argument to a specific value."""

    SPEC_SCHEMA = {
        "type": "object",
        "properties": {
            "argument_name": {
                "type": "string",
                "minLength": 1
            },
            "value": {
                "type": "string",
                "minLength": 1
            },
        },
        "additionalProperties": False,
        "required": ["argument_name", "value"]
    }

    @classmethod
    def from_spec(cls, spec, validator_map, resource_roots, package='sahara'):
        """Builds an argument_set validator from a specification.

        :param spec: A dictionary with two items: "argument_name", containing
            a string indicating the argument to be set, and "value", a value
            to which to set that argument.
        :param validator_map: A map of validator name to class.
        :param resource_roots: The roots from which relative paths to
            resources (scripts and such) will be referenced. Any resource will
            be pulled from the first path in the list at which a file exists.
        :return: A SaharaArgumentSetterValidator.
        """
        jsonschema.validate(spec, cls.SPEC_SCHEMA)
        argument_name = spec['argument_name']
        value = spec['value']

        return cls(argument_name, value)

    def __init__(self, argument_name, value):
        """Constructor method.

        :param argument_name: The name of an argument.
        :param value: A value to which to set that argument.
        """
        self.argument_name = argument_name
        self.value = value

    def validate(self, remote, test_only=False,
                 image_arguments=None, **kwargs):
        """Attempts to validate depending on argument value.

        :param remote: A remote socket to the instance.
        :param test_only: If true, all validators will only verify that a
            desired state is present, and fail if it is not. If false, all
            validators will attempt to enforce the desired state if possible,
            and succeed if this enforcement succeeds.
        :param image_arguments: A dictionary of image argument values keyed by
            argument name.
        """
        image_arguments[self.argument_name] = self.value


def _sudo(remote, cmd, **kwargs):
    return remote.execute_command(cmd, run_as_root=True, **kwargs)
