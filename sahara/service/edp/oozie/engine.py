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


from oslo.config import cfg

from sahara import conductor as c
from sahara import context
from sahara.service.edp import base_engine
from sahara.service.edp import hdfs_helper as h
from sahara.service.edp import job_utils
from sahara.service.edp.oozie import oozie as o
from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.utils import remote
from sahara.utils import xmlutils as x

CONF = cfg.CONF

conductor = c.API


class OozieJobEngine(base_engine.JobEngine):
    def __init__(self, cluster):

        self.cluster = cluster
        self.plugin = job_utils.get_plugin(self.cluster)

    def _get_client(self):
        return o.OozieClient(self.plugin.get_oozie_server_uri(self.cluster),
                             self.plugin.get_oozie_server(self.cluster))

    def _get_oozie_job_params(self, hdfs_user, path_to_workflow):
        rm_path = self.plugin.get_resource_manager_uri(self.cluster)
        nn_path = self.plugin.get_name_node_uri(self.cluster)
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

        for data_source in [input_source, output_source]:
            if data_source and data_source.type == 'hdfs':
                h.configure_cluster_for_hdfs(self.cluster, data_source)
                break

        hdfs_user = self.plugin.get_hdfs_user()

        # TODO(tmckay): this should probably be "get_namenode"
        # but that call does not exist in the plugin api now.
        # However, other engines may need it.
        oozie_server = self.plugin.get_oozie_server(self.cluster)

        wf_dir = job_utils.create_hdfs_workflow_dir(oozie_server,
                                                    job, hdfs_user)
        job_utils.upload_job_files_to_hdfs(oozie_server, wf_dir,
                                           job, hdfs_user)

        wf_xml = workflow_factory.get_workflow_xml(
            job, self.cluster, job_execution, input_source, output_source)

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


def get_possible_job_config(job_type):
    # TODO(tmckay): when config hints are fixed to be relative
    # to the plugin, this may move into the job engines as
    # an abstract method
    return workflow_factory.get_possible_job_config(job_type)
