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
import uuid

from oslo.config import cfg
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

    def _get_oozie_job_params(self, hdfs_user, path_to_workflow):
        rm_path = self.get_resource_manager_uri(self.cluster)
        nn_path = self.get_name_node_uri(self.cluster)
        job_parameters = {
            "jobTracker": rm_path,
            "nameNode": nn_path,
            "user.name": hdfs_user,
            "oozie.wf.application.path": "%s%s" % (nn_path, path_to_workflow),
            "oozie.use.system.libpath": "true"}
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
        proxy_configs = job_execution.job_configs.get('proxy_configs')

        for data_source in [input_source, output_source]:
            if data_source and data_source.type == 'hdfs':
                h.configure_cluster_for_hdfs(self.cluster, data_source)
                break

        hdfs_user = self.get_hdfs_user()

        # TODO(tmckay): this should probably be "get_namenode"
        # but that call does not exist in the oozie engine api now.
        oozie_server = self.get_oozie_server(self.cluster)

        wf_dir = self._create_hdfs_workflow_dir(oozie_server, job)
        self._upload_job_files_to_hdfs(oozie_server, wf_dir, job,
                                       proxy_configs)

        wf_xml = workflow_factory.get_workflow_xml(
            job, self.cluster, job_execution, input_source, output_source,
            hdfs_user)

        path_to_workflow = self._upload_workflow_file(oozie_server, wf_dir,
                                                      wf_xml, hdfs_user)

        job_params = self._get_oozie_job_params(hdfs_user,
                                                path_to_workflow)

        client = self._get_client()
        oozie_job_id = client.add_job(x.create_hadoop_xml(job_params),
                                      job_execution)
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
        # All types except Java require input and output objects
        # and Java require main class
        if job.type in [edp.JOB_TYPE_JAVA]:
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
                edp.JOB_TYPE_PIG]

    def _upload_job_files_to_hdfs(self, where, job_dir, job,
                                  proxy_configs=None):
        mains = job.mains or []
        libs = job.libs or []
        uploaded_paths = []
        hdfs_user = self.get_hdfs_user()

        with remote.get_remote(where) as r:
            for main in mains:
                raw_data = dispatch.get_raw_binary(main, proxy_configs)
                h.put_file_to_hdfs(r, raw_data, main.name, job_dir, hdfs_user)
                uploaded_paths.append(job_dir + '/' + main.name)
            for lib in libs:
                raw_data = dispatch.get_raw_binary(lib, proxy_configs)
                # HDFS 2.2.0 fails to put file if the lib dir does not exist
                self.create_hdfs_dir(r, job_dir + "/lib")
                h.put_file_to_hdfs(r, raw_data, lib.name, job_dir + "/lib",
                                   hdfs_user)
                uploaded_paths.append(job_dir + '/lib/' + lib.name)
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
