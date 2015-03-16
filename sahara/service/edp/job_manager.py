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
from sahara.i18n import _LE
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.service.edp import job_utils
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.service.edp.spark import engine as spark_engine
from sahara.utils import edp
from sahara.utils import proxy as p


LOG = log.getLogger(__name__)

CONF = cfg.CONF

conductor = c.API

ENGINES = [oozie_engine.OozieJobEngine,
           spark_engine.SparkJobEngine]


def _get_job_type(job_execution):
    return conductor.job_get(context.ctx(), job_execution.job_id).type


def _get_job_engine(cluster, job_execution):
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
    if ((CONF.use_namespaces and not CONF.use_floating_ips) or
            CONF.proxy_command):
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

    eng = _get_job_engine(cluster, job_execution)
    if eng is None:
        raise e.EDPError(_("Cluster does not support job type %s")
                         % _get_job_type(job_execution))
    job_execution = _update_job_execution_extra(cluster, job_execution)

    # Job id is a string
    # Status is a string
    # Extra is a dictionary to add to extra in the job_execution
    jid, status, extra = eng.run_job(job_execution)

    # Set the job id and the start time
    # Optionally, update the status and the 'extra' field
    update_dict = {'oozie_job_id': jid,
                   'start_time': datetime.datetime.now()}
    if status:
        update_dict['info'] = {'status': status}
    if extra:
        curr_extra = job_execution.extra.copy()
        curr_extra.update(extra)
        update_dict['extra'] = curr_extra

    job_execution = conductor.job_execution_update(
        ctx, job_execution, update_dict)


def run_job(job_execution_id):
    try:
        _run_job(job_execution_id)
    except Exception as ex:
        LOG.warning(
            _LW("Can't run job execution {job} (reason: {reason})").format(
                job=job_execution_id, reason=ex))

        conductor.job_execution_update(
            context.ctx(), job_execution_id,
            {'info': {'status': edp.JOB_STATUS_FAILED},
             'start_time': datetime.datetime.now(),
             'end_time': datetime.datetime.now()})


def cancel_job(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    if job_execution.info['status'] in edp.JOB_STATUSES_TERMINATED:
        return job_execution
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster is None:
        return job_execution
    engine = _get_job_engine(cluster, job_execution)
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
                    LOG.warning(
                        _LW("Error during cancel of job execution {job}: "
                            "{error}").format(job=job_execution.id,
                                              error=ex))
                if job_info is not None:
                    job_execution = _write_job_status(job_execution, job_info)
                    LOG.info(_LI("Job execution {job_id} was canceled "
                                 "successfully").format(
                                     job_id=job_execution.id))
                    return job_execution
                context.sleep(3)
                job_execution = conductor.job_execution_get(
                    ctx, job_execution_id)
                if not job_execution:
                    LOG.info(_LI("Job execution {job_exec_id} was deleted. "
                                 "Canceling current operation.").format(
                             job_exec_id=job_execution_id))
                    return job_execution
            else:
                LOG.info(_LI("Job execution status {job}: {status}").format(
                         job=job_execution.id,
                         status=job_execution.info['status']))
                return job_execution
        else:
            raise e.CancelingFailed(_('Job execution %s was not canceled')
                                    % job_execution.id)


def get_job_status(job_execution_id):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_execution_id)
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster is not None and cluster.status == 'Active':
        engine = _get_job_engine(cluster, job_execution)
        if engine is not None:
            job_execution = _update_job_status(engine,
                                               job_execution)
    return job_execution


def update_job_statuses():
    ctx = context.ctx()
    for je in conductor.job_execution_get_all(ctx, end_time=None):
        try:
            get_job_status(je.id)
        except Exception as e:
            LOG.error(_LE("Error during update job execution {job}: {error}")
                      .format(job=je.id, error=e))


def get_job_config_hints(job_type):
    for eng in ENGINES:
        if job_type in eng.get_supported_job_types():
            return eng.get_possible_job_config(job_type)
