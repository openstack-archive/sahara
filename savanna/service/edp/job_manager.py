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

import datetime

from oslo.config import cfg

from savanna import conductor as c
from savanna import context
from savanna.openstack.common import log
from savanna.openstack.common import uuidutils
from savanna.plugins import base as plugin_base
from savanna.plugins.general import utils as u
from savanna.service.edp.binary_retrievers import dispatch
from savanna.service.edp import hdfs_helper as h
from savanna.service.edp import oozie as o
from savanna.service.edp.workflow_creator import workflow_factory
from savanna.utils import remote
from savanna.utils import xmlutils as x


LOG = log.getLogger(__name__)

opts = [
    cfg.StrOpt('job_workflow_postfix',
               default='',
               help='Postfix for storing jobs in hdfs. Will be '
                    'added to /user/hadoop/')
]

CONF = cfg.CONF
CONF.register_opts(opts)

conductor = c.API

terminated_job_states = ['DONEWITHERROR', 'FAILED', 'KILLED', 'SUCCEEDED']


def get_job_status(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)

    if cluster is None or cluster.status != 'Active':
        return job_execution

    client = o.OozieClient(cluster['info']['JobFlow']['Oozie'] + "/oozie")
    job_info = client.get_job_status(job_execution.oozie_job_id)
    update = {"info": job_info}
    if job_info['status'] in terminated_job_states:
        update['end_time'] = datetime.datetime.now()

    job_execution = conductor.job_execution_update(ctx, job_execution,
                                                   update)
    return job_execution


def update_job_statuses():
    ctx = context.ctx()
    for je in conductor.job_execution_get_all(ctx, end_time=None):
        try:
            get_job_status(je.id)
        except Exception as e:
            LOG.exception("Error during update job execution %s: %s" %
                          (je.id, e))


def cancel_job(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)

    client = o.OozieClient(cluster['info']['JobFlow']['Oozie'] + "/oozie/")
    client.kill_job(job_execution.oozie_job_id)

    job_info = client.get_job_status(job_execution.oozie_job_id)
    update = {"info": job_info,
              "end_time": datetime.datetime.now()}
    job_execution = conductor.job_execution_update(ctx, job_execution,
                                                   update)

    return job_execution


def run_job(job_execution):
    ctx = context.ctx()

    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster.status != 'Active':
        return job_execution

    job = conductor.job_get(ctx, job_execution.job_id)
    input_source = conductor.data_source_get(ctx,  job_execution.input_id)
    output_source = conductor.data_source_get(ctx,  job_execution.output_id)
    #TODO(nprivalova): should be removed after all features implemented
    validate(input_source, output_source, job)

    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    hdfs_user = plugin.get_hdfs_user()
    wf_dir = create_workflow_dir(u.get_jobtracker(cluster), job, hdfs_user)
    upload_job_files(u.get_jobtracker(cluster), wf_dir, job, hdfs_user)

    creator = workflow_factory.get_creator(job)

    # Do other job type specific setup here, for example
    # uploading hive configuration
    creator.configure_workflow_if_needed(cluster, wf_dir)

    wf_xml = creator.get_workflow_xml(job_execution.job_configs,
                                      input_source, output_source)

    path_to_workflow = upload_workflow_file(u.get_jobtracker(cluster),
                                            wf_dir, wf_xml, hdfs_user)

    jt_path = '%s:8021' % u.get_jobtracker(cluster).hostname
    nn_path = 'hdfs://%s:8020' % u.get_namenode(cluster).hostname

    client = o.OozieClient(cluster['info']['JobFlow']['Oozie'] + "/oozie/")
    job_parameters = {"jobTracker": jt_path,
                      "nameNode": nn_path,
                      "user.name": "hadoop",
                      "oozie.wf.application.path":
                      "%s%s" % (nn_path, path_to_workflow),
                      "oozie.use.system.libpath": "true"}

    oozie_job_id = client.add_job(x.create_hadoop_xml(job_parameters))
    client.run_job(oozie_job_id)
    job_execution = conductor.job_execution_update(ctx, job_execution,
                                                   {'oozie_job_id':
                                                    oozie_job_id,
                                                    'start_time':
                                                    datetime.datetime.now()})

    return job_execution


def upload_job_files(where, job_dir, job, hdfs_user):

    mains = job.mains or []
    libs = job.libs or []
    uploaded_paths = []

    with remote.get_remote(where) as r:
        for main in mains:
            raw_data = dispatch.get_raw_binary(main)
            h.put_file_to_hdfs(r, raw_data, main.name, job_dir, hdfs_user)
            uploaded_paths.append(job_dir + '/' + main.name)
        for lib in libs:
            raw_data = dispatch.get_raw_binary(lib)
            h.put_file_to_hdfs(r, raw_data, lib.name, job_dir + "/lib",
                               hdfs_user)
            uploaded_paths.append(job_dir + '/lib/' + lib.name)
    return uploaded_paths


def upload_workflow_file(where, job_dir, wf_xml, hdfs_user):
    with remote.get_remote(where) as r:
        h.put_file_to_hdfs(r, wf_xml, "workflow.xml", job_dir, hdfs_user)

    return "%s/workflow.xml" % job_dir


def create_workflow_dir(where, job, hdfs_user):
    constructed_dir = '/user/hadoop/'
    constructed_dir = _add_postfix(constructed_dir)
    constructed_dir += '%s/%s' % (job.name, uuidutils.generate_uuid())
    with remote.get_remote(where) as r:
        h.create_dir(r, constructed_dir, hdfs_user)

    return constructed_dir


def _add_postfix(constructed_dir):
    constructed_dir = _append_slash_if_needed(constructed_dir)
    if CONF.job_workflow_postfix:
        constructed_dir = ''.join([str(constructed_dir),
                                   str(CONF.job_workflow_postfix)])
    return _append_slash_if_needed(constructed_dir)


def _append_slash_if_needed(path):
    if path[-1] != '/':
        path += '/'
    return path


#TODO(nprivalova): this validation should be removed after implementing
#  all features
def validate(input_data, output_data, job):
    if input_data.type != 'swift' or output_data.type != 'swift':
        raise RuntimeError
    if job.type not in ['Pig', 'Jar', 'Hive']:
        raise RuntimeError
