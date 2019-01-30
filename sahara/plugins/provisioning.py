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

import copy

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import base as plugins_base
from sahara.utils import resources


class ProvisioningPluginBase(plugins_base.PluginInterface):
    @plugins_base.required
    def get_versions(self):
        """Get available plugin versions

        :returns: A sequence of strings representing the versions

        For example:
            ["1.0.0", "1.0.1"]
        """
        pass

    @plugins_base.required
    def get_configs(self, hadoop_version):
        """Get default configuration for a given plugin version

        :param hadoop_version: String representing a plugin version
        :returns: A dict containing the configuration
        """
        pass

    @plugins_base.required_with_default
    def get_labels(self):
        versions = self.get_versions()
        default = {'enabled': {'status': True}}
        return {
            'plugin_labels': copy.deepcopy(default),
            'version_labels': {
                version: copy.deepcopy(default) for version in versions
            }
        }

    @plugins_base.required
    def get_node_processes(self, hadoop_version):
        """Get node processes of a given plugin version

        :param hadoop_version: String containing a plugin version
        :returns: A dict where the keys are the core components of the plugin
        and the value is a sequence of node processes for that component

        For example:
        {
            "HDFS": ["namenode", "datanode"],
            "Spark": ["master", "slave"]
        }

        """
        pass

    @plugins_base.required_with_default
    def get_required_image_tags(self, hadoop_version):
        return [self.name, hadoop_version]

    @plugins_base.required_with_default
    def validate(self, cluster):
        pass

    @plugins_base.required_with_default
    def validate_scaling(self, cluster, existing, additional):
        pass

    @plugins_base.required_with_default
    def update_infra(self, cluster):
        pass

    @plugins_base.required
    def configure_cluster(self, cluster):
        pass

    @plugins_base.required
    def start_cluster(self, cluster):
        pass

    @plugins_base.optional
    def scale_cluster(self, cluster, instances):
        pass

    @plugins_base.optional
    def get_edp_engine(self, cluster, job_type):
        pass

    @plugins_base.optional
    def get_edp_job_types(self, versions=None):
        return {}

    @plugins_base.optional
    def get_edp_config_hints(self, job_type, version):
        return {}

    @plugins_base.required_with_default
    def get_open_ports(self, node_group):
        return []

    @plugins_base.required_with_default
    def decommission_nodes(self, cluster, instances):
        pass

    @plugins_base.optional
    def get_image_arguments(self, hadoop_version):
        """Gets the argument set taken by the plugin's image generator

        Note: If the plugin can generate or validate an image but takes no
        arguments, please return an empty sequence rather than NotImplemented
        for all versions that support image generation or validation. This is
        used as a flag to determine whether the plugin has implemented this
        optional feature.

        :returns: A sequence with items of type
            sahara.plugins.images.ImageArgument
        """
        return NotImplemented

    @plugins_base.optional
    def pack_image(self, hadoop_version, remote,
                   test_only=False, image_arguments=None):
        """Packs an image for registration in Glance and use by Sahara

        :param remote: A remote (usually of type
            sahara.cli.image_pack.api.ImageRemote) that serves as a handle to
            the image to modify. Note that this image will be modified
            in-place, not copied.
        :param test_only: If set to True, this method will only test to
            ensure that the image already meets the plugin's requirements.
            This can be used to test images without modification. If set to
            False per the default, this method will modify the image if any
            requirements are not met.
        :param image_arguments: A dict of image argument name to argument
            value.
        :raises: sahara.plugins.exceptions.ImageValidationError: If the method
            fails to modify the image to specification (if test_only is False),
            or if the method finds that the image does not meet the
            specification (if test_only is True).
        :raises: sahara.plugins.exceptions.ImageValidationSpecificationError:
            If the specification for image generation or validation is itself
            in error and cannot be executed without repair.
        """
        pass

    @plugins_base.optional
    def validate_images(self, cluster, test_only=False, image_arguments=None):
        """Validates the image to be used by a cluster.

        :param cluster: The object handle to a cluster which has active
            instances ready to generate remote handles.
        :param test_only: If set to True, this method will only test to
            ensure that the image already meets the plugin's requirements.
            This can be used to test images without modification. If set to
            False per the default, this method will modify the image if any
            requirements are not met.
        :param image_arguments: A dict of image argument name to argument
            value.
        :raises: sahara.plugins.exceptions.ImageValidationError: If the method
            fails to modify the image to specification (if test_only is False),
            or if the method finds that the image does not meet the
            specification (if test_only is True).
        :raises: sahara.plugins.exceptions.ImageValidationSpecificationError:
            If the specification for image generation or validation is itself
            in error and cannot be executed without repair.
        """
        pass

    @plugins_base.required_with_default
    def on_terminate_cluster(self, cluster):
        pass

    @plugins_base.optional
    def recommend_configs(self, cluster, scaling=False):
        pass

    @plugins_base.required_with_default
    def get_health_checks(self, cluster):
        return []

    def get_all_configs(self, hadoop_version):
        common = list_of_common_configs()
        plugin_specific_configs = self.get_configs(hadoop_version)
        if plugin_specific_configs:
            common.extend(plugin_specific_configs)
        return common

    def get_version_details(self, version):
        details = {}
        configs = self.get_all_configs(version)
        details['configs'] = [c.dict for c in configs]
        details['node_processes'] = self.get_node_processes(version)
        details['required_image_tags'] = self.get_required_image_tags(version)
        return details

    def to_dict(self):
        res = super(ProvisioningPluginBase, self).to_dict()
        res['versions'] = self.get_versions()
        return res

    # Some helpers for plugins

    def _map_to_user_inputs(self, hadoop_version, configs):
        config_objs = self.get_all_configs(hadoop_version)

        # convert config objects to applicable_target -> config_name -> obj
        config_objs_map = {}
        for config_obj in config_objs:
            applicable_target = config_obj.applicable_target
            confs = config_objs_map.get(applicable_target, {})
            confs[config_obj.name] = config_obj
            config_objs_map[applicable_target] = confs

        # iterate over all configs and append UserInputs to result list
        result = []
        for applicable_target in configs:
            for config_name in configs[applicable_target]:
                confs = config_objs_map.get(applicable_target)
                if not confs:
                    raise ex.ConfigurationError(
                        _("Can't find applicable target "
                          "'%(applicable_target)s' for '%(config_name)s'")
                        % {"applicable_target": applicable_target,
                           "config_name": config_name})
                conf = confs.get(config_name)
                if not conf:
                    raise ex.ConfigurationError(
                        _("Can't find config '%(config_name)s' "
                          "in '%(applicable_target)s'")
                        % {"config_name": config_name,
                           "applicable_target": applicable_target})
                result.append(UserInput(
                    conf, configs[applicable_target][config_name]))

        return sorted(result)


class Config(resources.BaseResource):
    """Describes a single config parameter.

    Config type - could be 'str', 'integer', 'boolean', 'enum'.
    If config type is 'enum' then list of valid values should be specified in
    config_values property.

    Priority - integer parameter which helps to differentiate all
    configurations in the UI. Priority decreases from the lower values to
    higher values.

    For example:

        "some_conf", "map_reduce", "node", is_optional=True
    """

    def __init__(self, name, applicable_target, scope, config_type="string",
                 config_values=None, default_value=None, is_optional=False,
                 description=None, priority=2):
        self.name = name
        self.description = description
        self.config_type = config_type
        self.config_values = config_values
        self.default_value = default_value
        self.applicable_target = applicable_target
        self.scope = scope
        self.is_optional = is_optional
        self.priority = priority

    def to_dict(self):
        res = super(Config, self).to_dict()
        # TODO(slukjanov): all custom fields from res
        return res

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return '<Config %s in %s>' % (self.name, self.applicable_target)


class UserInput(object):
    """Value provided by the user for a specific config entry."""

    def __init__(self, config, value):
        self.config = config
        self.value = value

    def __eq__(self, other):
        return self.config == other.config and self.value == other.value

    def __lt__(self, other):
        return (self.config, self.value) < (other.config, other.value)

    def __repr__(self):
        return '<UserInput %s = %s>' % (self.config.name, self.value)


class ValidationError(object):
    """Describes what is wrong with one of the values provided by user."""

    def __init__(self, config, message):
        self.config = config
        self.message = message

    def __repr__(self):
        return "<ValidationError %s>" % self.config.name


# COMMON FOR ALL PLUGINS CONFIGS

XFS_ENABLED = Config(
    "Enable XFS", 'general', 'cluster', priority=1,
    default_value=True, config_type="bool", is_optional=True,
    description='Enables XFS for formatting'
)

DISKS_PREPARING_TIMEOUT = Config(
    "Timeout for disk preparing", 'general', 'cluster', priority=1,
    default_value=300, config_type="int", is_optional=True,
    description='Timeout for preparing disks, formatting and mounting'
)


NTP_URL = Config(
    "URL of NTP server", 'general', 'cluster', priority=1,
    default_value='', is_optional=True,
    description='URL of the NTP server for synchronization time on cluster'
                ' instances'
)

NTP_ENABLED = Config(
    "Enable NTP service", 'general', 'cluster', priority=1, default_value=True,
    config_type="bool",
    description='Enables NTP service for synchronization time on cluster '
                'instances'
)

HEAT_WAIT_CONDITION_TIMEOUT = Config(
    "Heat Wait Condition timeout", "general", "cluster", priority=1,
    config_type="int", default_value=3600, is_optional=True,
    description="The number of seconds to wait for the instance to boot")


def list_of_common_configs():
    return [DISKS_PREPARING_TIMEOUT, NTP_ENABLED, NTP_URL,
            HEAT_WAIT_CONDITION_TIMEOUT, XFS_ENABLED]
