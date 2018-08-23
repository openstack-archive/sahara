# Copyright (c) 2014 Red Hat, Inc.
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
from oslo_utils import uuidutils
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.castellan import utils as key_manager
from sahara.service.edp import job_utils
from sahara.service import trusts as t
from sahara.swift import utils as su
from sahara.utils.openstack import base as b
from sahara.utils.openstack import keystone as k


PROXY_DOMAIN = None
conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF

opts = [
    cfg.BoolOpt('use_domain_for_proxy_users',
                default=False,
                help='Enables Sahara to use a domain for creating temporary '
                     'proxy users to access Swift. If this is enabled '
                     'a domain must be created for Sahara to use.'),
    cfg.StrOpt('proxy_user_domain_name',
               default=None,
               help='The domain Sahara will use to create new proxy users '
                    'for Swift object access.'),
    cfg.ListOpt('proxy_user_role_names',
                default=['member'],
                help='A list of the role names that the proxy user should '
                     'assume through trust for Swift object access.')
]
CONF.register_opts(opts)


def create_proxy_user_for_job_execution(job_execution):
    '''Creates a proxy user and adds the credentials to the job execution

    :param job_execution: The job execution model to update

    '''
    username = 'job_{0}'.format(job_execution.id)
    password = key_manager.store_secret(proxy_user_create(username))
    current_user = k.auth()
    proxy_user = k.auth_for_proxy(username, password)
    trust_id = t.create_trust(trustor=current_user,
                              trustee=proxy_user,
                              role_names=CONF.proxy_user_role_names)
    update = {'job_configs': job_execution.job_configs.to_dict()}
    update['job_configs']['proxy_configs'] = {
        'proxy_username': username,
        'proxy_password': password,
        'proxy_trust_id': trust_id
        }
    conductor.job_execution_update(context.ctx(), job_execution, update)


def delete_proxy_user_for_job_execution(job_execution):
    '''Delete a proxy user based on a JobExecution

    :param job_execution: The job execution with proxy user information
    :returns: An updated job_configs dictionary or None

    '''
    proxy_configs = job_execution.job_configs.get('proxy_configs')
    if proxy_configs is not None:
        proxy_username = proxy_configs.get('proxy_username')
        proxy_trust_id = proxy_configs.get('proxy_trust_id')
        proxy_user = k.auth_for_proxy(proxy_username,
                                      key_manager.get_secret(
                                          proxy_configs.get('proxy_password')),
                                      proxy_trust_id)
        t.delete_trust(proxy_user, proxy_trust_id)
        proxy_user_delete(proxy_username)
        key_manager.delete_secret(proxy_configs.get('proxy_password'))
        update = job_execution.job_configs.to_dict()
        del update['proxy_configs']
        return update
    return None


def create_proxy_user_for_cluster(cluster):
    '''Creates a proxy user and adds the credentials to the cluster

    :param cluster: The cluster model to update

    '''
    if cluster.cluster_configs.get('proxy_configs'):
        return cluster
    username = 'cluster_{0}'.format(cluster.id)
    password = key_manager.store_secret(proxy_user_create(username))
    current_user = k.auth()
    proxy_user = k.auth_for_proxy(username, password)
    trust_id = t.create_trust(trustor=current_user,
                              trustee=proxy_user,
                              role_names=CONF.proxy_user_role_names)
    update = {'cluster_configs': cluster.cluster_configs.to_dict()}
    update['cluster_configs']['proxy_configs'] = {
        'proxy_username': username,
        'proxy_password': password,
        'proxy_trust_id': trust_id
        }
    return conductor.cluster_update(context.ctx(), cluster, update)


def delete_proxy_user_for_cluster(cluster):
    '''Delete a proxy user based on a Cluster

    :param cluster: The cluster model with proxy user information

    '''
    proxy_configs = cluster.cluster_configs.get('proxy_configs')
    if proxy_configs is not None:
        proxy_username = proxy_configs.get('proxy_username')
        proxy_trust_id = proxy_configs.get('proxy_trust_id')
        proxy_user = k.auth_for_proxy(proxy_username,
                                      key_manager.get_secret(
                                          proxy_configs.get('proxy_password')),
                                      proxy_trust_id)
        t.delete_trust(proxy_user, proxy_trust_id)
        proxy_user_delete(proxy_username)
        key_manager.delete_secret(proxy_configs.get('proxy_password'))
        update = {'cluster_configs': cluster.cluster_configs.to_dict()}
        del update['cluster_configs']['proxy_configs']
        conductor.cluster_update(context.ctx(), cluster, update)


def domain_for_proxy():
    '''Return the proxy domain or None

    If configured to use the proxy domain, this function will return that
    domain. If not configured to use the proxy domain, this function will
    return None. If the proxy domain can't be found this will raise an
    exception.

    :returns: A Keystone Domain object or None.
    :raises ConfigurationError: If the domain is requested but not specified.
    :raises NotFoundException: If the domain name is specified but cannot be
                               found.

    '''
    if CONF.use_domain_for_proxy_users is False:
        return None
    if CONF.proxy_user_domain_name is None:
        raise ex.ConfigurationError(_('Proxy domain requested but not '
                                      'specified.'))
    admin = k.client_for_admin()

    global PROXY_DOMAIN
    if not PROXY_DOMAIN:
        domain_list = b.execute_with_retries(
            admin.domains.list, name=CONF.proxy_user_domain_name)
        if len(domain_list) == 0:
            raise ex.NotFoundException(
                value=CONF.proxy_user_domain_name,
                message_template=_('Failed to find domain %s'))
        # the domain name should be globally unique in Keystone
        if len(domain_list) > 1:
            raise ex.NotFoundException(
                value=CONF.proxy_user_domain_name,
                message_template=_('Unexpected results found when searching '
                                   'for domain %s'))
        PROXY_DOMAIN = domain_list[0]
    return PROXY_DOMAIN


def job_execution_requires_proxy_user(job_execution):
    '''Returns True if the job execution requires a proxy user.'''

    def _check_values(values):
        return any(value.startswith(
            su.SWIFT_INTERNAL_PREFIX) for value in values if (
                isinstance(value, six.string_types)))

    if CONF.use_domain_for_proxy_users is False:
        return False

    paths = [conductor.data_source_get(context.ctx(), job_execution.output_id),
             conductor.data_source_get(context.ctx(), job_execution.input_id)]
    if _check_values(ds.url for ds in paths if ds):
        return True

    if _check_values(six.itervalues(
            job_execution.job_configs.get('configs', {}))):
        return True

    if _check_values(six.itervalues(
            job_execution.job_configs.get('params', {}))):
        return True

    if _check_values(job_execution.job_configs.get('args', [])):
        return True

    job = conductor.job_get(context.ctx(), job_execution.job_id)
    if _check_values(main.url for main in job.mains):
        return True

    if _check_values(lib.url for lib in job.libs):
        return True

    # We did the simple checks, now if data_source referencing is
    # enabled and we have values that could be a name or uuid,
    # query for data_sources that match and contain a swift path
    by_name, by_uuid = job_utils.may_contain_data_source_refs(
        job_execution.job_configs)
    if by_name:
        names = tuple(job_utils.find_possible_data_source_refs_by_name(
            job_execution.job_configs))
        # do a query here for name in names and path starts with swift-prefix
        if names and conductor.data_source_count(
                context.ctx(),
                name=names,
                url=su.SWIFT_INTERNAL_PREFIX+'%') > 0:
            return True

    if by_uuid:
        uuids = tuple(job_utils.find_possible_data_source_refs_by_uuid(
            job_execution.job_configs))
        # do a query here for id in uuids and path starts with swift-prefix
        if uuids and conductor.data_source_count(
                context.ctx(),
                id=uuids,
                url=su.SWIFT_INTERNAL_PREFIX+'%') > 0:
            return True

    return False


def proxy_domain_users_list():
    '''Return a list of all users in the proxy domain.'''
    admin = k.client_for_admin()
    domain = domain_for_proxy()
    if domain:
        return b.execute_with_retries(admin.users.list, domain=domain.id)
    return []


def proxy_user_create(username):
    '''Create a new user in the proxy domain

    Creates the username specified with a random password.

    :param username: The name of the new user.
    :returns: The password created for the user.

    '''
    admin = k.client_for_admin()
    domain = domain_for_proxy()
    password = uuidutils.generate_uuid()
    b.execute_with_retries(
        admin.users.create, name=username, password=password, domain=domain.id)
    LOG.debug('Created proxy user {username}'.format(username=username))
    return password


def proxy_user_delete(username=None, user_id=None):
    '''Delete the user from the proxy domain.

    :param username: The name of the user to delete.
    :param user_id: The id of the user to delete, if provided this overrides
                    the username.
    :raises NotFoundException: If there is an error locating the user in the
                               proxy domain.

    '''
    admin = k.client_for_admin()
    if not user_id:
        domain = domain_for_proxy()
        user_list = b.execute_with_retries(
            admin.users.list, domain=domain.id, name=username)
        if len(user_list) == 0:
            raise ex.NotFoundException(
                value=username,
                message_template=_('Failed to find user %s'))
        if len(user_list) > 1:
            raise ex.NotFoundException(
                value=username,
                message_template=_('Unexpected results found when searching '
                                   'for user %s'))
        user_id = user_list[0].id
    b.execute_with_retries(admin.users.delete, user_id)
    LOG.debug('Deleted proxy user id {user_id}'.format(user_id=user_id))
