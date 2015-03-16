# Copyright (c) 2014 OpenStack Foundation
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

import abc
import os
import uuid

from oslo_config import cfg
import six

from sahara import conductor as c
from sahara import context
from sahara.service.edp import base_engine
from sahara.service.edp.binary_retrievers import dispatch
from sahara.service.edp import hdfs_helper as h
from sahara.service.edp import job_utils
from sahara.service.edp.oozie import oozie as o
from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.service.validations.edp import job_execution as j
from sahara.utils import edp
from sahara.utils import remote
from sahara.utils import xmlutils as x


CONF = cfg.CONF

conductor = c.API


@six.add_metaclass(abc.ABCMeta)
class OozieJobEngine(base_engine.JobEngine):

    def __init__(self, cluster):
        self.cluster = cluster
        self.plugin = job_utils.get_plugin(self.cluster)

    def _get_client(self):
        return o.OozieClient(self.get_oozie_server_uri(self.cluster),
                             self.get_oozie_server(self.cluster))

    def _get_oozie_job_params(self, hdfs_user, path_to_workflow, oozie_params,
                              use_hbase_lib):
        app_path = "oozie.wf.application.path"
        oozie_libpath_key = "oozie.libpath"
        oozie_libpath = ""
        rm_path = self.get_resource_manager_uri(self.cluster)
        nn_path = self.get_name_node_uri(self.cluster)
        hbase_common_lib_path = "%s%s" % (nn_path, h.HBASE_COMMON_LIB_PATH)

        if use_hbase_lib:
            if oozie_libpath_key in oozie_params:
                oozie_libpath = "%s,%s" % (oozie_params.get(oozie_libpath_key,
                                           ""), hbase_common_lib_path)
            else:
                oozie_libpath = hbase_common_lib_path

        job_parameters = {
            "jobTracker": rm_path,
            "nameNode": nn_path,
            "user.name": hdfs_user,
            oozie_libpath_key: oozie_libpath,
            app_path: "%s%s" % (nn_path, path_to_workflow),
            "oozie.use.system.libpath": "true"}

        # Don't let the application path be overwritten, that can't
        # possibly make any sense
        if app_path in oozie_params:
            del oozie_params[app_path]
        if oozie_libpath_key in oozie_params:
            del oozie_params[oozie_libpath_key]

        job_parameters.update(oozie_params)
        return job_parameters

    def _upload_workflow_file(self, where, job_dir, wf_xml, hdfs_user):
        with remote.get_remote(where) as r:
            h.put_file_to_hdfs(r, wf_xml, "workflow.xml", job_dir, hdfs_user)
        return "%s/workflow.xml" % job_dir

    def cancel_job(self, job_execution):
        if job_execution.oozie_job_id is not None:
            client = self._get_client()
            client.kill_job(job_execution)
            return client.get_job_status(job_execution)

    def get_job_status(self, job_execution):
        if job_execution.oozie_job_id is not None:
            return self._get_client().get_job_status(job_execution)

    def run_job(self, job_execution):
        ctx = context.ctx()

        job = conductor.job_get(ctx, job_execution.job_id)
        input_source, output_source = job_utils.get_data_sources(job_execution,
                                                                 job)

        # Updated_job_configs will be a copy of job_execution.job_configs with
        # any name or uuid references to data_sources resolved to paths
        # assuming substitution is enabled.
        # If substitution is not enabled then updated_job_configs will
        # just be a reference to job_execution.job_configs to avoid a copy.
        # Additional_sources will be a list of any data_sources found.
        additional_sources, updated_job_configs = (
            job_utils.resolve_data_source_references(job_execution.job_configs)
        )

        proxy_configs = updated_job_configs.get('proxy_configs')
        configs = updated_job_configs.get('configs', {})
        use_hbase_lib = configs.get('edp.hbase_common_lib', {})

        # Extract all the 'oozie.' configs so that they can be set in the
        # job properties file. These are config values for Oozie itself,
        # not the job code
        oozie_params = {}
        for k in list(configs):
            if k.startswith('oozie.'):
                oozie_params[k] = configs[k]

        for data_source in [input_source, output_source] + additional_sources:
            if data_source and data_source.type == 'hdfs':
                h.configure_cluster_for_hdfs(self.cluster, data_source)
                break

        hdfs_user = self.get_hdfs_user()

        # TODO(tmckay): this should probably be "get_namenode"
        # but that call does not exist in the oozie engine api now.
        oozie_server = self.get_oozie_server(self.cluster)

        wf_dir = self._create_hdfs_workflow_dir(oozie_server, job)
        self._upload_job_files_to_hdfs(oozie_server, wf_dir, job, configs,
                                       proxy_configs)

        wf_xml = workflow_factory.get_workflow_xml(
            job, self.cluster, updated_job_configs,
            input_source, output_source,
            hdfs_user)

        path_to_workflow = self._upload_workflow_file(oozie_server, wf_dir,
                                                      wf_xml, hdfs_user)

        job_params = self._get_oozie_job_params(hdfs_user,
                                                path_to_workflow,
                                                oozie_params,
                                                use_hbase_lib)

        client = self._get_client()
        oozie_job_id = client.add_job(x.create_hadoop_xml(job_params),
                                      job_execution)
        job_execution = conductor.job_execution_get(ctx, job_execution.id)
        if job_execution.info['status'] == edp.JOB_STATUS_TOBEKILLED:
            return (None, edp.JOB_STATUS_KILLED, None)
        client.run_job(job_execution, oozie_job_id)
        try:
            status = client.get_job_status(job_execution,
                                           oozie_job_id)['status']
        except Exception:
            status = None
        return (oozie_job_id, status, None)

    @abc.abstractmethod
    def get_hdfs_user(self):
        pass

    @abc.abstractmethod
    def create_hdfs_dir(self, remote, dir_name):
        pass

    @abc.abstractmethod
    def get_oozie_server_uri(self, cluster):
        pass

    @abc.abstractmethod
    def get_oozie_server(self, cluster):
        pass

    @abc.abstractmethod
    def get_name_node_uri(self, cluster):
        pass

    @abc.abstractmethod
    def get_resource_manager_uri(self, cluster):
        pass

    def validate_job_execution(self, cluster, job, data):
        # Shell job type requires no specific fields
        if job.type == edp.JOB_TYPE_SHELL:
            return
        # All other types except Java require input and output
        # objects and Java require main class
        if job.type == edp.JOB_TYPE_JAVA:
            j.check_main_class_present(data, job)
        else:
            j.check_data_sources(data, job)

            job_type, subtype = edp.split_job_type(job.type)
            if job_type == edp.JOB_TYPE_MAPREDUCE and (
                    subtype == edp.JOB_SUBTYPE_STREAMING):
                j.check_streaming_present(data, job)

    @staticmethod
    def get_possible_job_config(job_type):
        return workflow_factory.get_possible_job_config(job_type)

    @staticmethod
    def get_supported_job_types():
        return [edp.JOB_TYPE_HIVE,
                edp.JOB_TYPE_JAVA,
                edp.JOB_TYPE_MAPREDUCE,
                edp.JOB_TYPE_MAPREDUCE_STREAMING,
                edp.JOB_TYPE_PIG,
                edp.JOB_TYPE_SHELL]

    def _upload_job_files_to_hdfs(self, where, job_dir, job, configs,
                                  proxy_configs=None):
        mains = job.mains or []
        libs = job.libs or []
        builtin_libs = edp.get_builtin_binaries(job, configs)
        uploaded_paths = []
        hdfs_user = self.get_hdfs_user()
        job_dir_suffix = 'lib' if job.type != edp.JOB_TYPE_SHELL else ''
        lib_dir = os.path.join(job_dir, job_dir_suffix)

        with remote.get_remote(where) as r:
            for main in mains:
                raw_data = dispatch.get_raw_binary(main, proxy_configs)
                h.put_file_to_hdfs(r, raw_data, main.name, job_dir, hdfs_user)
                uploaded_paths.append(job_dir + '/' + main.name)
            if len(libs) and job_dir_suffix:
                # HDFS 2.2.0 fails to put file if the lib dir does not exist
                self.create_hdfs_dir(r, lib_dir)
            for lib in libs:
                raw_data = dispatch.get_raw_binary(lib, proxy_configs)
                h.put_file_to_hdfs(r, raw_data, lib.name, lib_dir, hdfs_user)
                uploaded_paths.append(lib_dir + '/' + lib.name)
            for lib in builtin_libs:
                h.put_file_to_hdfs(r, lib['raw'], lib['name'], lib_dir,
                                   hdfs_user)
                uploaded_paths.append(lib_dir + '/' + lib['name'])
        return uploaded_paths

    def _create_hdfs_workflow_dir(self, where, job):
        constructed_dir = '/user/%s/' % self.get_hdfs_user()
        constructed_dir = self._add_postfix(constructed_dir)
        constructed_dir += '%s/%s' % (job.name, six.text_type(uuid.uuid4()))
        with remote.get_remote(where) as r:
            self.create_hdfs_dir(r, constructed_dir)

        return constructed_dir

    def _add_postfix(self, constructed_dir):
        def _append_slash_if_needed(path):
            if path[-1] != '/':
                path += '/'
            return path

        constructed_dir = _append_slash_if_needed(constructed_dir)
        if CONF.job_workflow_postfix:
            constructed_dir = ''.join([str(constructed_dir),
                                       str(CONF.job_workflow_postfix)])
        return _append_slash_if_needed(constructed_dir)
