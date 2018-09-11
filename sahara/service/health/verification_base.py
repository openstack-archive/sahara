# Copyright (c) 2016 Mirantis Inc.
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

import collections

from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor
from sahara import context
from sahara import exceptions
from sahara.i18n import _
from sahara.plugins import health_check_base
from sahara.service.health import common
from sahara.utils import cluster as cluster_utils


cond = conductor.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class CannotVerifyError(exceptions.SaharaException):
    code = "CANNOT_VERIFY"
    message_template = _("Cannot verify cluster. Reason: %s")

    def __init__(self, reason):
        message = self.message_template % reason
        super(CannotVerifyError, self).__init__(message)


def get_possible_ops():
    return common.VERIFICATIONS_OPS


def verification_exists(cluster):
    try:
        if cluster.verification is not None:
            return True
    except (AttributeError, KeyError):
        return False


def validate_verification_ops(cluster, data):
    status = data.get('verification', {}).get('status', None)
    if not status:
        # update doesn't affect verifications
        return False
    if len(list(data.keys())) != 1:
        raise CannotVerifyError(
            _("Can't update verification with other updates"))
    if status == common.VERIFICATIONS_START_OPS:
        return validate_verification_start(cluster)


def clean_verification_data(cluster):
    cluster = cond.cluster_get(context.ctx(), cluster)
    if verification_exists(cluster):
        try:
            vid = cluster.verification.id
            cond.cluster_verification_delete(context.ctx(), vid)
        except exceptions.NotFoundException:
            LOG.debug("Verification data already cleaned")


def validate_verification_start(cluster):
    if not CONF.cluster_verifications.verification_enable:
        raise CannotVerifyError(_("All verifications are disabled"))
    ctx = context.ctx()
    cluster = cond.cluster_get(ctx, cluster)
    if not cluster or cluster.status != cluster_utils.CLUSTER_STATUS_ACTIVE:
        raise CannotVerifyError(_("Cluster is not active or doesn't exists"))
    if not verification_exists(cluster):
        return True
    if cluster.verification.status == common.HEALTH_STATUS_CHECKING:
        raise CannotVerifyError(
            _("Cluster verification in state %s")
            % common.HEALTH_STATUS_CHECKING)
    return True


def _prepare_verification_running(ctx, cluster):
    if verification_exists(cluster):
        vid = cluster.verification.id
        # to delete all data related to the previous one
        cond.cluster_verification_delete(ctx, vid)
    return (cond.cluster_verification_add(
        ctx, cluster, {'status': common.HEALTH_STATUS_CHECKING}),
        cond.cluster_get(ctx, cluster))


def _execute_health_checks(ctx, cluster):
    health_checks = health_check_base.get_health_checks(cluster)
    actual = []
    with context.ThreadGroup() as tg:
        for check in health_checks:
            actual_check = check(cluster)
            actual.append(actual_check)
            tg.spawn('health-check-exc', actual_check.execute)


def _decide_status_for_verification(ctx, verification):
    ver = cond.cluster_verification_get(ctx, verification)
    cnt = collections.Counter()
    for check in ver.checks:
        cnt[check.status] += 1

    if cnt[common.HEALTH_STATUS_GREEN] == len(ver.checks):
        decided_status = common.HEALTH_STATUS_GREEN
    elif cnt[common.HEALTH_STATUS_RED] > 0:
        decided_status = common.HEALTH_STATUS_RED
    else:
        decided_status = common.HEALTH_STATUS_YELLOW

    return cond.cluster_verification_update(
        context.ctx(), ver.id, {'status': decided_status})


def verification_run(cluster):
    ctx = context.ctx()
    LOG.debug("Running verification for the cluster")
    ver, cluster = _prepare_verification_running(ctx, cluster)
    _execute_health_checks(ctx, cluster)
    return _decide_status_for_verification(ctx, ver)


def handle_verification(cluster, values):
    cluster = cond.cluster_get(context.ctx(), cluster)
    context.set_current_cluster_id(cluster.id)
    values = {} if not values else values
    status = values.get('verification', {}).get('status', None)
    if status == common.VERIFICATIONS_START_OPS:
        verification_run(cluster)


def update_verification_required(values):
    if values.get('verification', {}).get('status', None):
        return True
    return False


def get_verification_periodic_interval():
    return (CONF.cluster_verifications.verification_periodic_interval if
            CONF.cluster_verifications.verification_enable else -1)
