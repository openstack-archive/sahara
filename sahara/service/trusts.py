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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils as json
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.utils.openstack import keystone

conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def create_trust(trustor, trustee, role_names, impersonation=True,
                 project_id=None, allow_redelegation=False):
    '''Create a trust and return it's identifier

    :param trustor: The user delegating the trust, this is an auth plugin.

    :param trustee: The user consuming the trust, this is an auth plugin.

    :param role_names: A list of role names to be assigned.

    :param impersonation: Should the trustee impersonate trustor,
                          default is True.

    :param project_id: The project that the trust will be scoped into,
                       default is the trustor's project id.

    :param allow_redelegation: Allow redelegation parameter for cluster
                               trusts.

    :returns: A valid trust id.

    :raises CreationFailed: If the trust cannot be created.

    '''
    if project_id is None:
        project_id = keystone.project_id_from_auth(trustor)
    try:
        trustor_user_id = keystone.user_id_from_auth(trustor)
        trustee_user_id = keystone.user_id_from_auth(trustee)
        client = keystone.client_from_auth(trustor)
        trust = client.trusts.create(trustor_user=trustor_user_id,
                                     trustee_user=trustee_user_id,
                                     impersonation=impersonation,
                                     role_names=role_names,
                                     project=project_id,
                                     allow_redelegation=allow_redelegation)
        LOG.debug('Created trust {trust_id}'.format(
            trust_id=six.text_type(trust.id)))
        return trust.id
    except Exception as e:
        LOG.error('Unable to create trust (reason: {reason})'.format(reason=e))
        raise ex.CreationFailed(_('Failed to create trust'))


def create_trust_for_cluster(cluster, expires=True):
    '''Create a trust for a cluster

    This delegates a trust from the current user to the Sahara admin user
    based on the current context roles, and then adds the trust identifier
    to the cluster object.

    :param expires: The trust will expire if this is set to True.
    '''
    ctx = context.current()
    cluster = conductor.cluster_get(ctx, cluster)
    if CONF.use_identity_api_v3 and not cluster.trust_id:
        trustor = keystone.auth()
        trustee = keystone.auth_for_admin(
            project_name=CONF.trustee.project_name)

        trust_id = create_trust(trustor=trustor,
                                trustee=trustee,
                                role_names=ctx.roles,
                                allow_redelegation=True)

        conductor.cluster_update(ctx,
                                 cluster,
                                 {'trust_id': trust_id})


def delete_trust(trustee, trust_id):
    '''Delete a trust from a trustee

    :param trustee: The user to delete the trust from, this is an auth plugin.

    :param trust_id: The identifier of the trust to delete.

    :raises DeletionFailed: If the trust cannot be deleted.

    '''
    try:
        client = keystone.client_from_auth(trustee)
        client.trusts.delete(trust_id)
        LOG.debug('Deleted trust {trust_id}'.format(
            trust_id=six.text_type(trust_id)))
    except Exception as e:
        LOG.error('Unable to delete trust (reason: {reason})'.format(reason=e))
        raise ex.DeletionFailed(
            _('Failed to delete trust {0}').format(trust_id))


def delete_trust_from_cluster(cluster):
    '''Delete a trust from a cluster

    If the cluster has a trust delegated to it, then delete it and set
    the trust id to None.

    :param cluster: The cluster to delete the trust from.

    '''
    ctx = context.current()
    cluster = conductor.cluster_get(ctx, cluster)
    if CONF.use_identity_api_v3 and cluster.trust_id:
        keystone_auth = keystone.auth_for_admin(trust_id=cluster.trust_id)
        delete_trust(keystone_auth, cluster.trust_id)
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
    ctx = context.current()
    cluster = conductor.cluster_get(ctx, cluster)
    if CONF.use_identity_api_v3 and cluster.trust_id:
        ctx.username = CONF.trustee.username
        ctx.tenant_id = cluster.tenant_id
        ctx.auth_plugin = keystone.auth_for_admin(
            trust_id=cluster.trust_id)
        ctx.auth_token = context.get_auth_token()
        ctx.service_catalog = json.dumps(
            keystone.service_catalog_from_auth(ctx.auth_plugin))


def get_os_admin_auth_plugin(cluster):
    '''Return an admin auth plugin based on the cluster trust id or project

    If a trust id is available for the cluster, then it is used
    to create an auth plugin scoped to the trust. If not, the
    project name from the current context is used to scope the
    auth plugin.

    :param cluster: The id of the cluster to use for trust identification.

    '''
    ctx = context.current()
    cluster = conductor.cluster_get(ctx, cluster)
    if CONF.use_identity_api_v3 and cluster.trust_id:
        return keystone.auth_for_admin(trust_id=cluster.trust_id)
    return keystone.auth_for_admin(project_name=ctx.tenant_name)
