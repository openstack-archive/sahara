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

from keystoneclient.auth import identity as keystone_identity
from keystoneclient import session as keystone_session
from keystoneclient.v2_0 import client as keystone_client
from keystoneclient.v3 import client as keystone_client_v3
from oslo_config import cfg

from sahara import context
from sahara.service import sessions
from sahara.utils.openstack import base


opts = [
    # TODO(alazarev) Move to [keystone] section
    cfg.BoolOpt('use_identity_api_v3',
                default=True,
                help='Enables Sahara to use Keystone API v3. '
                     'If that flag is disabled, '
                     'per-job clusters will not be terminated '
                     'automatically.'),
    cfg.IntOpt('cluster_operation_trust_expiration_hours',
               default=24,
               help='Defines the period of time (in hours) after which trusts '
                    'created to allow sahara to create or scale a cluster '
                    'will expire. Note that this value should be '
                    'significantly larger than the value of the '
                    'cleanup_time_for_incomplete_clusters configuration key '
                    'if use of the cluster cleanup feature is desired (the '
                    'trust must last at least as long as a cluster could '
                    'validly take to stall in its creation, plus the '
                    'timeout value set in that key, plus one hour for the '
                    'period of the cleanup job).'),
    # TODO(mimccune) The following should be integrated into a custom
    # auth section
    cfg.StrOpt('admin_user_domain_name',
               default='default',
               help='The name of the domain to which the admin user '
                    'belongs.'),
    cfg.StrOpt('admin_project_domain_name',
               default='default',
               help='The name of the domain for the service '
                    'project(ex. tenant).')
]

ssl_opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to keystone.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for keystone '
                    'client requests.'),
    cfg.StrOpt("endpoint_type",
               default="internalURL",
               help="Endpoint type for keystone client requests")
]

keystone_group = cfg.OptGroup(name='keystone',
                              title='Keystone client options')

CONF = cfg.CONF
CONF.register_group(keystone_group)
CONF.register_opts(opts)
CONF.register_opts(ssl_opts, group=keystone_group)


def auth():
    '''Return a token auth plugin for the current context.'''
    ctx = context.current()
    return ctx.auth_plugin or token_auth(token=context.get_auth_token(),
                                         project_id=ctx.tenant_id)


def auth_for_admin(project_name=None, trust_id=None):
    '''Return an auth plugin for the admin.

    :param project_name: a project to scope the auth with (optional).

    :param trust_id: a trust to scope the auth with (optional).

    :returns: an auth plugin object for the admin.
    '''
    # TODO(elmiko) revisit the project_domain_name if we start getting
    # into federated authentication. it will need to match the domain that
    # the project_name exists in.
    auth = _password_auth(
        username=CONF.keystone_authtoken.admin_user,
        password=CONF.keystone_authtoken.admin_password,
        project_name=project_name,
        user_domain_name=CONF.admin_user_domain_name,
        project_domain_name=CONF.admin_project_domain_name,
        trust_id=trust_id)
    return auth


def auth_for_proxy(username, password, trust_id=None):
    '''Return an auth plugin for the proxy user.

    :param username: the name of the proxy user.

    :param password: the proxy user's password.

    :param trust_id: a trust to scope the auth with (optional).

    :returns: an auth plugin object for the proxy user.
    '''
    auth = _password_auth(
        username=username,
        password=password,
        user_domain_name=CONF.proxy_user_domain_name,
        trust_id=trust_id)
    return auth


def client():
    '''Return the current context client.'''
    return client_from_auth(auth())


def client_for_admin():
    '''Return the Sahara admin user client.'''
    auth = auth_for_admin(
        project_name=CONF.keystone_authtoken.admin_tenant_name)
    return client_from_auth(auth)


def client_from_auth(auth):
    '''Return a session based client from the auth plugin provided.

    A session is obtained from the global session cache.

    :param auth: the auth plugin object to use in client creation.

    :returns: a keystone client
    '''
    session = sessions.cache().get_session(sessions.SESSION_TYPE_KEYSTONE)
    if CONF.use_identity_api_v3:
        client_class = keystone_client_v3.Client
    else:
        client_class = keystone_client.Client
    return client_class(session=session, auth=auth)


def project_id_from_auth(auth):
    '''Return the project id associated with an auth plugin.

    :param auth: the auth plugin to inspect.

    :returns: the project id associated with the auth plugin.
    '''
    return auth.get_project_id(
        sessions.cache().get_session(sessions.SESSION_TYPE_KEYSTONE))


def service_catalog_from_auth(auth):
    '''Return the service catalog associated with an auth plugin.

    :param auth: the auth plugin to inspect.

    :returns: a list containing the service catalog.
    '''
    if CONF.use_identity_api_v3:
        return auth.get_access(
            sessions.cache().get_session()).get('catalog', [])
    else:
        return auth.get_access(
            sessions.cache().get_session()).get('serviceCatalog', [])


# TODO(elmiko) factor this out when redoing the barbicanclient
def session_for_admin():
    '''Return a Keystone session for the admin user.'''
    auth = _password_auth(
        username=CONF.keystone_authtoken.admin_user,
        password=CONF.keystone_authtoken.admin_password,
        project_name=CONF.keystone_authtoken.admin_tenant_name,
        user_domain_name=CONF.admin_user_domain_name,
        project_domain_name=CONF.admin_project_domain_name)
    return keystone_session.Session(auth=auth)


def token_auth(token, project_id=None, project_name=None,
               project_domain_name='Default'):
    '''Return a token auth plugin object.

    :param token: the token to use for authentication.

    :param project_id: the project(ex. tenant) id to scope the auth.

    :returns: a token auth plugin object.
    '''
    token_kwargs = dict(
        auth_url=base.retrieve_auth_url(CONF.keystone.endpoint_type),
        token=token
    )
    if CONF.use_identity_api_v3:
        token_kwargs.update(dict(
            project_id=project_id,
            project_name=project_name,
            project_domain_name=project_domain_name,
        ))
        auth = keystone_identity.v3.Token(**token_kwargs)
    else:
        token_kwargs.update(dict(
            tenant_id=project_id,
            tenant_name=project_name,
        ))
        auth = keystone_identity.v2.Token(**token_kwargs)
    return auth


def token_from_auth(auth):
    '''Return an authentication token from an auth plugin.

    :param auth: the auth plugin to acquire a token from.

    :returns: an auth token in string format.
    '''
    return keystone_session.Session(
        auth=auth, verify=CONF.generic_session_verify).get_token()


def user_id_from_auth(auth):
    '''Return a user id associated with an auth plugin.

    :param auth: the auth plugin to inspect.

    :returns: a token associated with the auth.
    '''
    return auth.get_user_id(sessions.cache().get_session(
        sessions.SESSION_TYPE_KEYSTONE))


# TODO(elmiko) deprecate this when all client have been migrated to sessions
def _client(username, password=None, token=None, tenant_name=None,
            tenant_id=None, trust_id=None, domain_name=None):

    if trust_id and not CONF.use_identity_api_v3:
        raise Exception("Trusts aren't implemented in keystone api"
                        " less than v3")

    auth_url = base.retrieve_auth_url(
        endpoint_type=CONF.keystone.endpoint_type)

    client_kwargs = {'username': username,
                     'password': password,
                     'token': token,
                     'tenant_name': tenant_name,
                     'tenant_id': tenant_id,
                     'trust_id': trust_id,
                     'user_domain_name': domain_name,
                     'auth_url': auth_url,
                     'cacert': CONF.keystone.ca_file,
                     'insecure': CONF.keystone.api_insecure
                     }

    if CONF.use_identity_api_v3:
        keystone = keystone_client_v3.Client(**client_kwargs)
        keystone.management_url = auth_url
    else:
        keystone = keystone_client.Client(**client_kwargs)

    return keystone


def _password_auth(username, password,
                   project_name=None, user_domain_name=None,
                   project_domain_name=None, trust_id=None):
    '''Return a password auth plugin object.

    :param username: the user to authenticate as.

    :param password: the user's password.

    :param project_name: the project(ex. tenant) name to scope the auth.

    :param user_domain_name: the domain the user belongs to.

    :param project_domain_name: the domain the project belongs to.

    :param trust_id: a trust id to scope the auth.

    :returns: a password auth plugin object.
    '''
    passwd_kwargs = dict(
        auth_url=base.retrieve_auth_url(CONF.keystone.endpoint_type),
        username=username,
        password=password
    )
    if CONF.use_identity_api_v3:
        passwd_kwargs.update(dict(
            project_name=project_name,
            user_domain_name=user_domain_name,
            project_domain_name=project_domain_name,
            trust_id=trust_id
        ))
        auth = keystone_identity.v3.Password(**passwd_kwargs)
    else:
        passwd_kwargs.update(dict(
            tenant_name=project_name,
            trust_id=trust_id
        ))
        auth = keystone_identity.v2.Password(**passwd_kwargs)
    return auth
