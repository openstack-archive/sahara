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


from sahara import exceptions as ex
from sahara.plugins import base as plugins_base
from sahara.utils import resources


class ProvisioningPluginBase(plugins_base.PluginInterface):
    @plugins_base.required
    def get_versions(self):
        pass

    @plugins_base.required
    def get_configs(self, hadoop_version):
        pass

    @plugins_base.optional
    def get_hdfs_user(self):
        pass

    @plugins_base.required
    def get_node_processes(self, hadoop_version):
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
    def get_name_node_uri(self, cluster):
        pass

    @plugins_base.optional
    def get_oozie_server(self, cluster):
        pass

    @plugins_base.optional
    def get_oozie_server_uri(self, cluster):
        pass

    @plugins_base.optional
    def validate_edp(self, cluster):
        pass

    @plugins_base.required_with_default
    def get_edp_engine(self, cluster, job_type, default_engines):
        '''Default implementation to select an EDP job engine

        This method chooses an EDP implementation based on job type. It should
        be overloaded by a plugin to allow different behavior or the selection
        of a custom EDP implementation.

        The default_engines parameter is a list of default EDP implementations.
        Each item in the list is a dictionary, and each dictionary has the
        following elements:

        name (a simple name for the implementation)
        job_types (a list of EDP job types supported by the implementation)
        engine (a class derived from sahara.service.edp.base_engine.JobEngine)

        This method will choose the first engine that it finds which lists the
        job_type value in the job_types element. An instance of that engine
        will be allocated and returned.

        :param cluster: a Sahara cluster object
        :param job_type: an EDP job type string
        :param default_engines: a list of dictionaries describing the default
        implementations.
        :returns: an instance of a class derived from
        sahara.service.edp.base_engine.JobEngine or None
        '''
        for eng in default_engines:
            if job_type in eng["job_types"]:
                return eng["engine"](cluster)

    @plugins_base.optional
    def get_resource_manager_uri(self, cluster):
        pass

    @plugins_base.required_with_default
    def decommission_nodes(self, cluster, instances):
        pass

    @plugins_base.optional
    def convert(self, config, plugin_name, version, template_name,
                cluster_template_create):
        pass

    @plugins_base.required_with_default
    def on_terminate_cluster(self, cluster):
        pass

    def to_dict(self):
        res = super(ProvisioningPluginBase, self).to_dict()
        res['versions'] = self.get_versions()
        return res

    # Some helpers for plugins

    def _map_to_user_inputs(self, hadoop_version, configs):
        config_objs = self.get_configs(hadoop_version)

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
                        "Can't find applicable target '%s' for '%s'"
                        % (applicable_target, config_name))
                conf = confs.get(config_name)
                if not conf:
                    raise ex.ConfigurationError(
                        "Can't find config '%s' in '%s'"
                        % (config_name, applicable_target))
                result.append(UserInput(
                    conf, configs[applicable_target][config_name]))

        return result


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

    def __repr__(self):
        return '<Config %s in %s>' % (self.name, self.applicable_target)


class UserInput(object):
    """Value provided by the user for a specific config entry."""

    def __init__(self, config, value):
        self.config = config
        self.value = value

    def __eq__(self, other):
        return self.config == other.config and self.value == other.value

    def __repr__(self):
        return '<UserInput %s = %s>' % (self.config.name, self.value)


class ValidationError(object):
    """Describes what is wrong with one of the values provided by user."""

    def __init__(self, config, message):
        self.config = config
        self.message = message

    def __repr__(self):
        return "<ValidationError %s>" % self.config.name
