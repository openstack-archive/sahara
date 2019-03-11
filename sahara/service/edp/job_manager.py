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

from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from sahara import conductor as c
from sahara import context
from sahara import exceptions as e
from sahara.i18n import _
from sahara.service.edp import job_utils
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.service.edp.spark import engine as spark_engine
from sahara.service.edp.storm import engine as storm_engine
from sahara.utils import cluster as c_u
from sahara.utils import edp
from sahara.utils import proxy as p


LOG = log.getLogger(__name__)

CONF = cfg.CONF

conductor = c.API

ENGINES = [oozie_engine.OozieJobEngine,
           spark_engine.SparkJobEngine,
           storm_engine.StormJobEngine,
           storm_engine.StormPyleusJobEngine]


def _get_job_type(job_execution):
    return conductor.job_get(context.ctx(), job_execution.job_id).type


def get_job_engine(cluster, job_execution):
    return job_utils.get_plugin(cluster).get_edp_engine(cluster,
                                                        _get_job_type(
                                                            job_execution))


def _write_job_status(job_execution, job_info):
    update = {"info": job_info}
    if job_info['status'] in edp.JOB_STATUSES_TERMINATED:
        update['end_time'] = datetime.datetime.now()
        job_configs = p.delete_proxy_user_for_job_execution(job_execution)
        if job_configs:
            update['job_configs'] = job_configs
    return conductor.job_execution_update(context.ctx(),
                                          job_execution,
                                          update)


def _update_job_status(engine, job_execution):
    job_info = engine.get_job_status(job_execution)
    if job_info is not None:
        job_execution = _write_job_status(job_execution, job_info)
    return job_execution


def _update_job_execution_extra(cluster, job_execution):
    # tmckay-fp we can make this slightly more efficient in
    # the use_namespaces case by asking the engine if it knows
    # the submission machine, and checking if that machine has
    # a floating ip.
    if (CONF.use_namespaces or CONF.proxy_command):
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
    if cluster is None or cluster.status != c_u.CLUSTER_STATUS_ACTIVE:
        LOG.info("Can not run this job on a non-existant cluster or a "
                 "inactive cluster.")
        return

    eng = get_job_engine(cluster, job_execution)
    if eng is None:
        raise e.EDPError(_("Cluster does not support job type %s")
                         % _get_job_type(job_execution))
    job_execution = _update_job_execution_extra(cluster, job_execution)

    # Job id is a string
    # Status is a string
    # Extra is a dictionary to add to extra in the job_execution
    if job_execution.job_configs.job_execution_info.get('job_execution_type'
                                                        ) == 'scheduled':
        jid, status, extra = eng.run_scheduled_job(job_execution)
    else:
        jid, status, extra = eng.run_job(job_execution)

    # Set the job id and the start time
    # Optionally, update the status and the 'extra' field
    update_dict = {'engine_job_id': jid,
                   'start_time': datetime.datetime.now()}
    if status:
        update_dict['info'] = {'status': status}
    if extra:
        curr_extra = job_execution.extra.copy()
        if 'neutron' in curr_extra:
            curr_extra['neutron'] = curr_extra['neutron'].copy()
        curr_extra.update(extra)
        update_dict['extra'] = curr_extra

    job_execution = conductor.job_execution_update(
        ctx, job_execution, update_dict)


def run_job(job_execution_id):
    try:
        _run_job(job_execution_id)
    except Exception as ex:
        LOG.exception("Can't run job execution (reason: {reason})".format(
                      reason=ex))

        job_execution = conductor.job_execution_get(
            context.ctx(), job_execution_id)

        if job_execution.engine_job_id is not None:
            cancel_job(job_execution_id)

        conductor.job_execution_update(
            context.ctx(), job_execution_id,
            {'info': {'status': edp.JOB_STATUS_FAILED},
             'start_time': datetime.datetime.now(),
             'end_time': datetime.datetime.now()})


def cancel_job(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    if job_execution.info['status'] in edp.JOB_STATUSES_TERMINATED:
        LOG.info("Job execution is already finished and shouldn't be canceled")
        return job_execution
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster is None:
        LOG.info("Can not cancel this job on a non-existant cluster.")
        return job_execution
    engine = get_job_engine(cluster, job_execution)
    if engine is not None:
        job_execution = conductor.job_execution_update(
            ctx, job_execution_id,
            {'info': {'status': edp.JOB_STATUS_TOBEKILLED}})

        timeout = CONF.job_canceling_timeout
        s_time = timeutils.utcnow()
        while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
            if job_execution.info['status'] not in edp.JOB_STATUSES_TERMINATED:
                try:
                    job_info = engine.cancel_job(job_execution)
                except Exception as ex:
                    job_info = None
                    LOG.warning("Error during cancel of job execution: "
                                "{error}".format(error=ex))
                if job_info is not None:
                    job_execution = _write_job_status(job_execution, job_info)
                    LOG.info("Job execution was canceled successfully")
                    return job_execution
                context.sleep(3)
                job_execution = conductor.job_execution_get(
                    ctx, job_execution_id)
                if not job_execution:
                    LOG.info("Job execution was deleted. "
                             "Canceling current operation.")
                    return job_execution
            else:
                LOG.info("Job execution status: {status}").format(
                    status=job_execution.info['status'])
                return job_execution
        else:
            raise e.CancelingFailed(_('Job execution %s was not canceled')
                                    % job_execution.id)


def get_job_status(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if (cluster is not None and
            cluster.status == c_u.CLUSTER_STATUS_ACTIVE):
        engine = get_job_engine(cluster, job_execution)
        if engine is not None:
            job_execution = _update_job_status(engine,
                                               job_execution)
    return job_execution


def update_job_status(job_execution_id):
    try:
        get_job_status(job_execution_id)
    except Exception as e:
        LOG.exception("Error during update job execution {job}: {error}"
                      .format(job=job_execution_id, error=e))


def update_job_statuses(cluster_id=None):
    ctx = context.ctx()
    kwargs = {'end_time': None}
    if cluster_id:
        kwargs.update({'cluster_id': cluster_id})
    for je in conductor.job_execution_get_all(ctx, **kwargs):
        update_job_status(je.id)


def get_job_config_hints(job_type):
    for eng in ENGINES:
        if job_type in eng.get_supported_job_types():
            return eng.get_possible_job_config(job_type)


def suspend_job(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    if job_execution.info['status'] not in edp.JOB_STATUSES_SUSPENDIBLE:
        raise e.SuspendingFailed(_("Suspending operation can not be performed"
                                 " on status: {status}")).format(
                                     status=job_execution.info['status'])
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    engine = get_job_engine(cluster, job_execution)
    job_execution = conductor.job_execution_update(
        ctx, job_execution_id, {
            'info': {'status': edp.JOB_STATUS_TOBESUSPENDED}})
    try:
        job_info = engine.suspend_job(job_execution)
    except Exception as ex:
        job_info = None
        conductor.job_execution_update(
            ctx, job_execution_id, {'info': {
                'status': edp.JOB_STATUS_SUSPEND_FAILED}})
        raise e.SuspendingFailed(_("Error during suspending of job execution: "
                                   "{error}")).format(error=ex)
    if job_info is not None:
        job_execution = _write_job_status(job_execution, job_info)
        LOG.info("Job execution was suspended successfully")
        return job_execution

    conductor.job_execution_update(
        ctx, job_execution_id, {'info': {
            'status': edp.JOB_STATUS_SUSPEND_FAILED}})
    raise e.SuspendingFailed(_("Failed to suspend job execution "
                               "{jid}")).format(jid=job_execution_id)
