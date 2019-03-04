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

import time

from oslo_utils import timeutils

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import base as plugin_base
from sahara.service.edp import job_utils as j_u
from sahara.service.validations import acl
from sahara.service.validations import base as val_base
import sahara.service.validations.edp.base as b
import sahara.service.validations.edp.job_interface as j_i
from sahara.utils import cluster as c_u
from sahara.utils import edp


conductor = c.API


def _is_main_class_present(data):
    if data:
        val = data.get(
            'job_configs', {}).get(
                'configs', {}).get('edp.java.main_class', None)
        return val and isinstance(val, six.string_types)
    return False


def check_main_class_present(data, job):
    if not _is_main_class_present(data):
        raise ex.InvalidDataException(
            _('%s job must specify edp.java.main_class') % job.type)


def _is_topology_name_present(data):
    if data:
        val = data.get(
            'job_configs', {}).get(
            'configs', {}).get('topology_name', None)
        return val and isinstance(val, six.string_types)
    return False


def check_topology_name_present(data, job):
    if not _is_main_class_present(data):
        raise ex.InvalidDataException(
            _('%s job must specify topology_name') % job.type)


def _streaming_present(data):
    try:
        streaming = set(('edp.streaming.mapper',
                         'edp.streaming.reducer'))
        configs = set(data['job_configs']['configs'])
        return streaming.intersection(configs) == streaming
    except Exception:
        return False


def check_streaming_present(data, job):
    if not _streaming_present(data):
        raise ex.InvalidDataException(
            _("%s job must specify streaming mapper and reducer") % job.type)


def check_scheduled_job_execution_info(job_execution_info):
    start = job_execution_info.get('start', None)
    if start is None:
        raise ex.InvalidDataException(_(
            "Scheduled job must specify start time"))
    try:
        start = time.strptime(start, "%Y-%m-%d %H:%M:%S")
        start = timeutils.datetime.datetime.fromtimestamp(time.mktime(start))
    except Exception:
        raise ex.InvalidDataException(_("Invalid Time Format"))

    now_time = timeutils.utcnow()

    if timeutils.delta_seconds(now_time, start) < 0:
        raise ex.InvalidJobExecutionInfoException(_(
            "Job start time should be later than now"))


def check_job_execution(data, job_templates_id=None):
    ctx = context.ctx()
    job_execution_info = data.get('job_execution_info', {})

    cluster = conductor.cluster_get(ctx, data['cluster_id'])
    if not cluster:
        raise ex.InvalidReferenceException(
            _("Cluster with id '%s' doesn't exist") % data['cluster_id'])

    val_base.check_plugin_labels(cluster.plugin_name, cluster.hadoop_version)

    jt_err_msg = _("Job template with id '%s' doesn't exist")
    if job_templates_id is None:
        job = conductor.job_get(ctx, data['job_template_id'])
        if not job:
            raise ex.InvalidReferenceException(
                jt_err_msg % data['job_template_id'])
    else:
        job = conductor.job_get(ctx, job_templates_id)
        if not job:
            raise ex.InvalidReferenceException(
                jt_err_msg % job_templates_id)

    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    edp_engine = plugin.get_edp_engine(cluster, job.type)
    if not edp_engine:
        raise ex.InvalidReferenceException(
            _("Cluster with id '%(cluster_id)s' doesn't support job type "
              "'%(job_type)s'") % {"cluster_id": cluster.id,
                                   "job_type": job.type})

    j_i.check_execution_interface(data, job)
    edp_engine.validate_job_execution(cluster, job, data)

    if 'job_execution_type' in job_execution_info:
        j_type = job_execution_info.get('job_execution_type', 'workflow')
        if j_type == 'scheduled':
            check_scheduled_job_execution_info(job_execution_info)


def check_data_sources(data, job):
    if not ('input_id' in data and 'output_id' in data):
        raise ex.InvalidDataException(_("%s job requires 'input_id' "
                                        "and 'output_id'") % job.type)

    b.check_data_source_exists(data['input_id'])
    b.check_data_source_exists(data['output_id'])

    b.check_data_sources_are_different(data['input_id'], data['output_id'])


def check_job_execution_cancel(job_id, **kwargs):
    ctx = context.current()
    je = conductor.job_execution_get(ctx, job_id)

    if je.tenant_id != ctx.tenant_id:
        raise ex.CancelingFailed(
            _("Job execution with id '%s' cannot be canceled "
              "because it wasn't created in this tenant")
            % job_id)

    if je.is_protected:
        raise ex.CancelingFailed(
            _("Job Execution with id '%s' cannot be canceled "
              "because it's marked as protected") % job_id)


def check_job_execution_delete(job_id, **kwargs):
    ctx = context.current()
    je = conductor.job_execution_get(ctx, job_id)

    acl.check_tenant_for_delete(ctx, je)
    acl.check_protected_from_delete(je)


def check_job_execution_update(job_id, data, **kwargs):
    ctx = context.current()
    je = conductor.job_execution_get(ctx, job_id)

    acl.check_tenant_for_update(ctx, je)
    acl.check_protected_from_update(je, data)


def check_job_status_update(job_id, data):
    ctx = context.ctx()
    job_execution = conductor.job_execution_get(ctx, job_id)
    # check we are updating status
    if 'info' in data:
        if len(data) != 1:
            raise ex.InvalidJobStatus(_("Invalid status parameter"))
    cluster = conductor.cluster_get(ctx, job_execution.cluster_id)
    if cluster is None or cluster.status != c_u.CLUSTER_STATUS_ACTIVE:
        raise ex.InvalidDataException(
            _("Suspending operation can not be performed on an inactive or "
              "non-existent cluster"))
    job_templates_id = conductor.job_execution_get(ctx, job_id).job_id
    job_type = conductor.job_get(ctx, job_templates_id).type
    engine = j_u.get_plugin(cluster).get_edp_engine(cluster, job_type)
    if 'info' in data:
        if data['info']['status'] == edp.JOB_ACTION_SUSPEND:
            if not engine.does_engine_implement('suspend_job'):
                raise ex.InvalidReferenceException(
                    _("Engine doesn't support suspending job feature"))
