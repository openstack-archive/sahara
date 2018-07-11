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

from oslo_config import cfg
import six

from sahara import conductor as c
from sahara import context
from sahara.service.castellan import utils as key_manager
from sahara.service.edp.oozie.workflow_creator import hive_workflow
from sahara.service.edp.oozie.workflow_creator import java_workflow
from sahara.service.edp.oozie.workflow_creator import mapreduce_workflow
from sahara.service.edp.oozie.workflow_creator import pig_workflow
from sahara.service.edp.oozie.workflow_creator import shell_workflow
from sahara.service.edp import s3_common
from sahara.swift import swift_helper as sw
from sahara.swift import utils as su
from sahara.utils import edp
from sahara.utils import xmlutils


conductor = c.API
CONF = cfg.CONF


class BaseFactory(object):
    def _separate_edp_configs(self, job_dict):
        configs = {}
        edp_configs = {}
        if 'configs' in job_dict:
            for k, v in six.iteritems(job_dict['configs']):
                if k.startswith('edp.'):
                    edp_configs[k] = v
                elif not k.startswith('oozie.'):
                    # 'oozie.' configs have been written to the properties file
                    configs[k] = v
        return configs, edp_configs

    def _prune_edp_configs(self, job_dict):
        if job_dict is None:
            return {}, {}

        # Rather than copy.copy, we make this by hand
        # to avoid FrozenClassError when we update 'configs'
        pruned_job_dict = {}
        for k, v in six.iteritems(job_dict):
            pruned_job_dict[k] = v

        # Separate out "edp." configs into its own dictionary
        configs, edp_configs = self._separate_edp_configs(job_dict)

        # Prune the new job_dict so it does not hold "edp." configs
        pruned_job_dict['configs'] = configs

        return pruned_job_dict, edp_configs

    def _update_dict(self, dest, src):
        if src is not None:
            for key, value in six.iteritems(dest):
                if hasattr(value, "update"):
                    new_vals = src.get(key, {})
                    value.update(new_vals)

    def update_job_dict(self, job_dict, exec_dict):
        pruned_exec_dict, edp_configs = self._prune_edp_configs(exec_dict)
        self._update_dict(job_dict, pruned_exec_dict)

        # Add the separated "edp." configs to the job_dict
        job_dict['edp_configs'] = edp_configs

        # Args are listed, not named. Simply replace them.
        job_dict['args'] = pruned_exec_dict.get('args', [])

        # Find all swift:// paths in args, configs, and params and
        # add the .sahara suffix to the container if it is not there
        # already
        job_dict['args'] = [
            # TODO(tmckay) args for Pig can actually be -param name=value
            # and value could conceivably contain swift paths
            su.inject_swift_url_suffix(arg) for arg in job_dict['args']]

        for k, v in six.iteritems(job_dict.get('configs', {})):
            job_dict['configs'][k] = su.inject_swift_url_suffix(v)

        for k, v in six.iteritems(job_dict.get('params', {})):
            job_dict['params'][k] = su.inject_swift_url_suffix(v)

    def get_configs(self, input_data, output_data, proxy_configs=None):
        configs = {}

        if proxy_configs:
            configs[sw.HADOOP_SWIFT_USERNAME] = proxy_configs.get(
                'proxy_username')
            configs[sw.HADOOP_SWIFT_PASSWORD] = key_manager.get_secret(
                proxy_configs.get('proxy_password'))
            configs[sw.HADOOP_SWIFT_TRUST_ID] = proxy_configs.get(
                'proxy_trust_id')
            configs[sw.HADOOP_SWIFT_DOMAIN_NAME] = CONF.proxy_user_domain_name
            return configs

        for src in (input_data, output_data):
            if src.type == "swift" and hasattr(src, "credentials"):
                if "user" in src.credentials:
                    configs[sw.HADOOP_SWIFT_USERNAME] = src.credentials['user']
                if "password" in src.credentials:
                    configs[sw.HADOOP_SWIFT_PASSWORD] = (
                        key_manager.get_secret(src.credentials['password']))
                break
        for src in (input_data, output_data):
            if src.type == "s3" and hasattr(src, "credentials"):
                if "accesskey" in src.credentials:
                    configs[s3_common.S3_ACCESS_KEY_CONFIG] = (
                        src.credentials['accesskey'])
                if "secretkey" in src.credentials:
                    configs[s3_common.S3_SECRET_KEY_CONFIG] = (
                        key_manager.get_secret(src.credentials['secretkey']))
                if "endpoint" in src.credentials:
                    configs[s3_common.S3_ENDPOINT_CONFIG] = (
                        src.credentials['endpoint'])
                if "bucket_in_path" in src.credentials:
                    configs[s3_common.S3_BUCKET_IN_PATH_CONFIG] = (
                        src.credentials['bucket_in_path'])
                if "ssl" in src.credentials:
                    configs[s3_common.S3_SSL_CONFIG] = (
                        src.credentials['ssl'])
                break
        return configs

    def get_params(self, input_data, output_data, data_source_urls):
        return {'INPUT': data_source_urls[input_data.id],
                'OUTPUT': data_source_urls[output_data.id]}


class PigFactory(BaseFactory):
    def __init__(self, job):
        super(PigFactory, self).__init__()

        self.name = self.get_script_name(job)

    def get_script_name(self, job):
        return conductor.job_main_name(context.ctx(), job)

    def get_workflow_xml(self, cluster, job_configs, input_data, output_data,
                         hdfs_user, data_source_urls):
        proxy_configs = job_configs.get('proxy_configs')
        job_dict = {'configs': self.get_configs(input_data, output_data,
                                                proxy_configs),
                    'params': self.get_params(input_data, output_data,
                                              data_source_urls),
                    'args': []}
        self.update_job_dict(job_dict, job_configs)
        creator = pig_workflow.PigWorkflowCreator()
        creator.build_workflow_xml(self.name,
                                   configuration=job_dict['configs'],
                                   params=job_dict['params'],
                                   arguments=job_dict['args'])
        return creator.get_built_workflow_xml()


class HiveFactory(BaseFactory):
    def __init__(self, job):
        super(HiveFactory, self).__init__()

        self.name = self.get_script_name(job)

    def get_script_name(self, job):
        return conductor.job_main_name(context.ctx(), job)

    def get_workflow_xml(self, cluster, job_configs, input_data, output_data,
                         hdfs_user, data_source_urls):
        proxy_configs = job_configs.get('proxy_configs')
        job_dict = {'configs': self.get_configs(input_data, output_data,
                                                proxy_configs),
                    'params': self.get_params(input_data, output_data,
                                              data_source_urls)}
        self.update_job_dict(job_dict, job_configs)

        creator = hive_workflow.HiveWorkflowCreator()
        creator.build_workflow_xml(self.name,
                                   edp.get_hive_shared_conf_path(hdfs_user),
                                   configuration=job_dict['configs'],
                                   params=job_dict['params'])
        return creator.get_built_workflow_xml()


class MapReduceFactory(BaseFactory):

    def get_configs(self, input_data, output_data, proxy_configs,
                    data_source_urls):
        configs = super(MapReduceFactory, self).get_configs(input_data,
                                                            output_data,
                                                            proxy_configs)
        configs['mapred.input.dir'] = data_source_urls[input_data.id]
        configs['mapred.output.dir'] = data_source_urls[output_data.id]
        return configs

    def _get_streaming(self, job_dict):
        prefix = 'edp.streaming.'
        return {k[len(prefix):]: v for (k, v) in six.iteritems(
            job_dict['edp_configs']) if k.startswith(prefix)}

    def get_workflow_xml(self, cluster, job_configs, input_data, output_data,
                         hdfs_user, data_source_urls):
        proxy_configs = job_configs.get('proxy_configs')
        job_dict = {'configs': self.get_configs(input_data, output_data,
                                                proxy_configs,
                                                data_source_urls)}
        self.update_job_dict(job_dict, job_configs)
        creator = mapreduce_workflow.MapReduceWorkFlowCreator()
        creator.build_workflow_xml(configuration=job_dict['configs'],
                                   streaming=self._get_streaming(job_dict))
        return creator.get_built_workflow_xml()


class JavaFactory(BaseFactory):

    def _get_java_configs(self, job_dict):
        main_class = job_dict['edp_configs']['edp.java.main_class']
        java_opts = job_dict['edp_configs'].get('edp.java.java_opts', None)
        args = job_dict['args']
        if edp.is_adapt_for_oozie_enabled(job_dict['edp_configs']):
            if args:
                args = [main_class] + args
            else:
                args = [main_class]
            main_class = 'org.openstack.sahara.edp.MainWrapper'
        return main_class, java_opts, args

    def get_configs(self, proxy_configs=None):
        # TODO(jfreud): allow s3 and non-proxy swift configs here?
        configs = {}

        if proxy_configs:
            configs[sw.HADOOP_SWIFT_USERNAME] = proxy_configs.get(
                'proxy_username')
            configs[sw.HADOOP_SWIFT_PASSWORD] = key_manager.get_secret(
                proxy_configs.get('proxy_password'))
            configs[sw.HADOOP_SWIFT_TRUST_ID] = proxy_configs.get(
                'proxy_trust_id')
            configs[sw.HADOOP_SWIFT_DOMAIN_NAME] = CONF.proxy_user_domain_name
            return configs

        return configs

    def get_workflow_xml(self, cluster, job_configs, *args, **kwargs):
        proxy_configs = job_configs.get('proxy_configs')
        job_dict = {'configs': self.get_configs(proxy_configs=proxy_configs),
                    'args': []}
        self.update_job_dict(job_dict, job_configs)

        main_class, java_opts, args = self._get_java_configs(job_dict)
        creator = java_workflow.JavaWorkflowCreator()
        creator.build_workflow_xml(main_class,
                                   configuration=job_dict['configs'],
                                   java_opts=java_opts,
                                   arguments=args)
        return creator.get_built_workflow_xml()


class ShellFactory(BaseFactory):

    def __init__(self, job):
        self.name, self.file_names = self.get_file_names(job)

    def get_file_names(self, job):
        ctx = context.ctx()
        return (conductor.job_main_name(ctx, job),
                conductor.job_lib_names(ctx, job))

    def get_configs(self):
        return {'configs': {},
                'params': {},
                'args': []}

    def get_workflow_xml(self, cluster, job_configs, *args, **kwargs):
        job_dict = self.get_configs()
        self.update_job_dict(job_dict, job_configs)
        creator = shell_workflow.ShellWorkflowCreator()
        creator.build_workflow_xml(self.name,
                                   configuration=job_dict['configs'],
                                   env_vars=job_dict['params'],
                                   arguments=job_dict['args'],
                                   files=self.file_names)
        return creator.get_built_workflow_xml()


def _get_creator(job):

    def make_PigFactory():
        return PigFactory(job)

    def make_HiveFactory():
        return HiveFactory(job)

    def make_ShellFactory():
        return ShellFactory(job)

    type_map = {
        edp.JOB_TYPE_HIVE: make_HiveFactory,
        edp.JOB_TYPE_JAVA: JavaFactory,
        edp.JOB_TYPE_MAPREDUCE: MapReduceFactory,
        edp.JOB_TYPE_MAPREDUCE_STREAMING: MapReduceFactory,
        edp.JOB_TYPE_PIG: make_PigFactory,
        edp.JOB_TYPE_SHELL: make_ShellFactory
    }

    return type_map[job.type]()


def get_workflow_xml(job, cluster, job_configs, *args, **kwargs):
    return _get_creator(job).get_workflow_xml(
        cluster, job_configs, *args, **kwargs)


def get_possible_job_config(job_type):
    if not edp.compare_job_type(job_type, *edp.JOB_TYPES_ALL):
        return None

    if edp.compare_job_type(job_type, edp.JOB_TYPE_JAVA):
        return {'job_config': {'configs': [], 'args': []}}

    if edp.compare_job_type(job_type, edp.JOB_TYPE_SHELL):
        return {'job_config': {'configs': [], 'params': {}, 'args': []}}

    if edp.compare_job_type(job_type,
                            edp.JOB_TYPE_MAPREDUCE, edp.JOB_TYPE_PIG):
        cfg = xmlutils.load_hadoop_xml_defaults(
            'service/edp/resources/mapred-default.xml')
        if edp.compare_job_type(job_type, edp.JOB_TYPE_MAPREDUCE):
            cfg += get_possible_mapreduce_configs()
    elif edp.compare_job_type(job_type, edp.JOB_TYPE_HIVE):
        cfg = xmlutils.load_hadoop_xml_defaults(
            'service/edp/resources/hive-default.xml')

    config = {'configs': cfg}
    if edp.compare_job_type(job_type, edp.JOB_TYPE_PIG, edp.JOB_TYPE_HIVE):
        config.update({'params': {}})
    if edp.compare_job_type(job_type, edp.JOB_TYPE_PIG):
        config.update({'args': []})
    return {'job_config': config}


def get_possible_mapreduce_configs():
    '''return a list of possible configuration values for map reduce jobs.'''
    cfg = xmlutils.load_hadoop_xml_defaults(
        'service/edp/resources/mapred-job-config.xml')
    return cfg
