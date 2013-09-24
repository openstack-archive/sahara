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

import six

from savanna import conductor as c
from savanna import context
from savanna.plugins import base as plugin_base
from savanna.plugins.general import utils as u
from savanna.service.edp import hdfs_helper as h
from savanna.service.edp.workflow_creator import hive_workflow
from savanna.service.edp.workflow_creator import mapreduce_workflow
from savanna.service.edp.workflow_creator import pig_workflow
from savanna.utils import remote

conductor = c.API

swift_username = 'fs.swift.service.savanna.username'
swift_password = 'fs.swift.service.savanna.password'


class BaseFactory(object):
    def configure_workflow_if_needed(self, *args, **kwargs):
        pass

    def get_configs(self, input_data, output_data):
        configs = {}
        if input_data.type == "swift" and hasattr(input_data, "credentials"):
            if "user" in input_data.credentials:
                configs[swift_username] = input_data.credentials['user']
            if "password" in input_data.credentials:
                configs[swift_password] = input_data.credentials['password']
        return configs

    def get_params(self, input_data, output_data):
        return {'INPUT': input_data.url,
                'OUTPUT': output_data.url}

    def get_args(self):
        return {}

    def update_configs(self, configs, execution_configs):
        if execution_configs is not None:
            for key, value in six.iteritems(configs):
                new_vals = execution_configs.get(key, {})
                value.update(new_vals)


class PigFactory(BaseFactory):
    def __init__(self, job):
        super(PigFactory, self).__init__()

        self.name = self.get_script_name(job)

    def get_script_name(self, job):
        return conductor.job_main_name(context.ctx(), job)

    def get_workflow_xml(self, execution_configs, input_data, output_data):
        configs = {'configs': self.get_configs(input_data, output_data),
                   'params': self.get_params(input_data, output_data),
                   'args': self.get_args()}
        self.update_configs(configs, execution_configs)
        creator = pig_workflow.PigWorkflowCreator()
        creator.build_workflow_xml(self.name,
                                   configuration=configs['configs'],
                                   params=configs['params'],
                                   arguments=configs['args'])
        return creator.get_built_workflow_xml()


class HiveFactory(BaseFactory):
    def __init__(self, job):
        super(HiveFactory, self).__init__()

        self.name = self.get_script_name(job)
        self.job_xml = "hive-site.xml"

    def get_script_name(self, job):
        return conductor.job_main_name(context.ctx(), job)

    def get_workflow_xml(self, execution_configs, input_data, output_data):
        configs = {'configs': self.get_configs(input_data, output_data),
                   'params': self.get_params(input_data, output_data)}
        self.update_configs(configs, execution_configs)
        creator = hive_workflow.HiveWorkflowCreator()
        creator.build_workflow_xml(self.name,
                                   self.job_xml,
                                   configuration=configs['configs'],
                                   params=configs['params'])
        return creator.get_built_workflow_xml()

    def configure_workflow_if_needed(self, cluster, wf_dir):
        h_s = u.get_hiveserver(cluster)
        plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
        h.copy_from_local(remote.get_remote(h_s),
                          plugin.get_hive_config_path(), wf_dir)


class MapReduceFactory(BaseFactory):

    def get_configs(self, input_data, output_data):
        configs = super(MapReduceFactory, self).get_configs(input_data,
                                                            output_data)
        configs['mapred.input.dir'] = input_data.url
        configs['mapred.output.dir'] = output_data.url
        return configs

    def get_workflow_xml(self, execution_configs, input_data, output_data):
        configs = {'configs': self.get_configs(input_data, output_data)}
        self.update_configs(configs, execution_configs)
        creator = mapreduce_workflow.MapReduceWorkFlowCreator()
        creator.build_workflow_xml(configuration=configs['configs'])
        return creator.get_built_workflow_xml()


def get_creator(job):

    def make_PigFactory():
        return PigFactory(job)

    def make_HiveFactory():
        return HiveFactory(job)

    type_map = {"Pig": make_PigFactory,
                "Hive": make_HiveFactory,
                "Jar": MapReduceFactory}

    return type_map[job.type]()
