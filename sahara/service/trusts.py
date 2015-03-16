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

import json

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.utils.openstack import keystone


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def create_trust(trustor,
                 trustee,
                 role_names,
                 impersonation=True,
                 project_id=None):
    '''Create a trust and return it's identifier

    :param trustor: The Keystone client delegating the trust.
    :param trustee: The Keystone client consuming the trust.
    :param role_names: A list of role names to be assigned.
    :param impersonation: Should the trustee impersonate trustor,
                          default is True.
    :param project_id: The project that the trust will be scoped into,
                       default is the trustor's project id.
    :returns: A valid trust id.
    :raises CreationFailed: If the trust cannot be created.

    '''
    if project_id is None:
        project_id = trustor.tenant_id
    try:
        trust = trustor.trusts.create(trustor_user=trustor.user_id,
                                      trustee_user=trustee.user_id,
                                      impersonation=impersonation,
                                      role_names=role_names,
                                      project=project_id)
        LOG.debug('Created trust {trust_id}'.format(
            trust_id=six.text_type(trust.id)))
        return trust.id
    except Exception as e:
        LOG.error(_LE('Unable to create trust (reason: {reason})').format(
            reason=e))
        raise ex.CreationFailed(_('Failed to create trust'))


def create_trust_for_cluster(cluster):
    '''Create a trust for a cluster

    This delegates a trust from the current user to the Sahara admin user
    based on the current context roles, and then adds the trust identifier
    to the cluster object.

    '''
    trustor = keystone.client()
    ctx = context.current()
    trustee = keystone.client_for_admin()

    trust_id = create_trust(trustor=trustor,
                            trustee=trustee,
                            role_names=ctx.roles)

    conductor.cluster_update(ctx,
                             cluster,
                             {'trust_id': trust_id})


def delete_trust(trustee, trust_id):
    '''Delete a trust from a trustee

    :param trustee: The Keystone client to delete the trust from.
    :param trust_id: The identifier of the trust to delete.
    :raises DeletionFailed: If the trust cannot be deleted.

    '''
    try:
        trustee.trusts.delete(trust_id)
        LOG.debug('Deleted trust {trust_id}'.format(
            trust_id=six.text_type(trust_id)))
    except Exception as e:
        LOG.error(_LE('Unable to delete trust (reason: {reason})').format(
            reason=e))
        raise ex.DeletionFailed(
            _('Failed to delete trust {0}').format(trust_id))


def delete_trust_from_cluster(cluster):
    '''Delete a trust from a cluster

    If the cluster has a trust delegated to it, then delete it and set
    the trust id to None.

    :param cluster: The cluster to delete the trust from.

    '''
    if cluster.trust_id:
        keystone_client = keystone.client_for_admin_from_trust(
            cluster.trust_id)
        delete_trust(keystone_client, cluster.trust_id)
        ctx = context.current()
        conductor.cluster_update(ctx,
                                 cluster,
                                 {'trust_id': None})


def use_os_admin_auth_token(cluster):
    '''Set the current context to the admin user's trust scoped token

    This will configure the current context to the admin user's identity
    with the cluster's tenant. It will also generate an authentication token
    based on the admin user and a delegated trust associated with the
    cluster.

    :param cluster: The cluster to use for tenant and trust identification.

    '''
    if cluster.trust_id:
        ctx = context.current()
        ctx.username = CONF.keystone_authtoken.admin_user
        ctx.tenant_id = cluster.tenant_id
        client = keystone.client_for_admin_from_trust(cluster.trust_id)
        ctx.auth_token = client.auth_token
        ctx.service_catalog = json.dumps(
            client.service_catalog.catalog['catalog'])
