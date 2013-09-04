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
from savanna.openstack.common import uuidutils
from savanna.plugins import base as plugin_base
from savanna.plugins.general import utils as u
from savanna.service.edp import hdfs_helper as h
from savanna.service.edp import oozie as o
from savanna.service.edp.workflow_creator import hive_workflow as hive_flow
from savanna.service.edp.workflow_creator import mapreduce_workflow as mr_flow
from savanna.service.edp.workflow_creator import pig_workflow as pig_flow
from savanna.utils import remote
from savanna.utils import xmlutils as x

opts = [
    cfg.StrOpt('job_workflow_postfix',
               default='',
               help='Postfix for storing jobs in hdfs. Will be '
                    'added to /user/hadoop/')
]

CONF = cfg.CONF
CONF.register_opts(opts)

conductor = c.API

main_res_names = {'Pig': 'script.pig',
                  'Jar': 'main.jar',
                  'Hive': 'script.q'}


def get_job_status(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)

    if cluster.status != 'Active':
        return job_execution.status

    client = o.OozieClient(cluster['info']['JobFlow']['Oozie'] + "/oozie/")
    job_info = client.get_job_status(job_execution.oozie_job_id)
    job_execution = conductor.job_execution_update(ctx, job_execution,
                                                   {"info": job_info})
    return job_execution


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


def run_job(ctx, job_execution):
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster.status != 'Active':
        return job_execution

    job = conductor.job_get(ctx, job_execution.job_id)
    job_origin = conductor.job_origin_get(context.ctx(), job.job_origin_id)
    input_source = conductor.data_source_get(ctx,  job_execution.input_id)
    output_source = conductor.data_source_get(ctx,  job_execution.output_id)
    #TODO(nprivalova): should be removed after all features implemented
    validate(input_source, output_source, job)

    wf_dir = create_workflow_dir(u.get_jobtracker(cluster), job)
    upload_job_file(u.get_jobtracker(cluster), wf_dir, job_origin, job)

    if job.type == 'Hive':
        upload_hive_site(cluster, wf_dir)

    wf_xml = build_workflow_for_job(job.type, job_execution, input_source,
                                    output_source)
    path_to_workflow = upload_workflow_file(u.get_jobtracker(cluster),
                                            wf_dir, wf_xml)

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


def upload_job_file(where, job_dir, job_origin, job):
    main_binary = conductor.job_binary_get_raw_data(context.ctx(),
                                                    job_origin.url)
    if job.type == 'Jar':
        job_dir += '/lib'
    with remote.get_remote(where) as r:
        h.put_file_to_hdfs(r, main_binary, main_res_names[job.type], job_dir)

    return "%s/%s" % (job_dir, main_res_names[job.type])


def upload_workflow_file(where, job_dir, wf_xml):
    with remote.get_remote(where) as r:
        h.put_file_to_hdfs(r, wf_xml, "workflow.xml", job_dir)

    return "%s/workflow.xml" % job_dir


def upload_hive_site(cluster, wf_dir):
    h_s = u.get_hiveserver(cluster)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    h.copy_from_local(remote.get_remote(h_s),
                      plugin.get_hive_config_path(), wf_dir)


def create_workflow_dir(where, job):
    constructed_dir = '/user/hadoop/'
    constructed_dir = _add_postfix(constructed_dir)
    constructed_dir += '%s/%s' % (job.name, uuidutils.generate_uuid())
    with remote.get_remote(where) as r:
        h.create_dir(r, constructed_dir)

    return constructed_dir


def build_workflow_for_job(job_type, job_execution, input_data, output_data):

    configs = {'fs.swift.service.savanna.username':
               input_data.credentials['user'],
               'fs.swift.service.savanna.password':
               input_data.credentials['password']}

    j_e_conf = job_execution.job_configs
    if j_e_conf:
        configs.update(j_e_conf)

    if job_type == 'Pig':
        creator = pig_flow.PigWorkflowCreator()
        creator.build_workflow_xml(main_res_names['Pig'],
                                   configuration=configs,
                                   params={'INPUT': input_data.url,
                                           'OUTPUT': output_data.url})
    if job_type == 'Hive':
        creator = hive_flow.HiveWorkflowCreator()
        creator.build_workflow_xml(main_res_names['Hive'],
                                   job_xml="hive-site.xml",
                                   configuration=configs,
                                   params={'INPUT': input_data.url,
                                           'OUTPUT': output_data.url})

    if job_type == 'Jar':
        creator = mr_flow.MapReduceWorkFlowCreator()
        configs['mapred.input.dir'] = input_data.url
        configs['mapred.output.dir'] = output_data.url
        creator.build_workflow_xml(configuration=configs)

    return creator.get_built_workflow_xml()


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
