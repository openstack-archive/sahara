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

from sahara import conductor as c
from sahara import context
from sahara.openstack.common import log
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.service.edp.spark import engine as spark_engine


LOG = log.getLogger(__name__)

CONF = cfg.CONF

conductor = c.API

terminated_job_states = ['DONEWITHERROR', 'FAILED', 'KILLED', 'SUCCEEDED']


def _get_job_engine(cluster):
    # TODO(tmckay): The selection of a job engine can be more
    # complicated in the future.  It can consider things like
    # whether or not an Oozie process is present, or what the
    # hadoop version is, or the job type, etc.
    if cluster.plugin_name == 'spark':
        return spark_engine.SparkJobEngine(cluster)
    return oozie_engine.OozieJobEngine(cluster)


def _update_job_status(engine, job_execution):
    job_info = engine.get_job_status(job_execution)
    if job_info is not None:
        update = {"info": job_info}
        if job_info['status'] in terminated_job_states:
            update['end_time'] = datetime.datetime.now()
        job_execution = conductor.job_execution_update(context.ctx(),
                                                       job_execution,
                                                       update)
    return job_execution


def _update_job_execution_extra(cluster, job_execution):
    if CONF.use_namespaces and not CONF.use_floating_ips:
        info = cluster.node_groups[0].instances[0].remote().get_neutron_info()
        extra = job_execution.extra.copy()
        extra['neutron'] = info

        job_execution = conductor.job_execution_update(
            context.ctx(), job_execution.id, {'extra': extra})
    return job_execution


def _run_job(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster.status != 'Active':
        return

    job_execution = _update_job_execution_extra(cluster, job_execution)
    jid = _get_job_engine(cluster).run_job(job_execution)

    job_execution = conductor.job_execution_update(
        ctx, job_execution, {'oozie_job_id': jid,
                             'start_time': datetime.datetime.now()})


def run_job(job_execution_id):
    try:
        _run_job(job_execution_id)
    except Exception as ex:
        LOG.exception("Can't run job execution '%s' (reason: %s)",
                      job_execution_id, ex)

        conductor.job_execution_update(
            context.ctx(), job_execution_id,
            {'info': {'status': 'FAILED'},
             'start_time': datetime.datetime.now(),
             'end_time': datetime.datetime.now()})


def cancel_job(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster is not None:
        engine = _get_job_engine(cluster)
        try:
            engine.cancel_job(job_execution)
        except Exception as e:
            LOG.exception("Error during cancel of job execution %s: %s" %
                          (job_execution.id, e))
        job_execution = _update_job_status(engine, job_execution)
    return job_execution


def get_job_status(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster is not None and cluster.status == 'Active':
        job_execution = _update_job_status(_get_job_engine(cluster),
                                           job_execution)
    return job_execution


def update_job_statuses():
    ctx = context.ctx()
    for je in conductor.job_execution_get_all(ctx, end_time=None):
        try:
            get_job_status(je.id)
        except Exception as e:
            LOG.exception("Error during update job execution %s: %s" %
                          (je.id, e))


def get_job_config_hints(job_type):
    # TODO(tmckay) We need plugin-specific config hints
    # (not a new problem) so this will need to change.  However,
    # at the moment we don't have a plugin or cluster argument
    # in this call so we will have to just use the configs for
    # Oozie
    return oozie_engine.get_possible_job_config(job_type)
