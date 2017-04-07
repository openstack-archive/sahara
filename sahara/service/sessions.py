# Copyright (c) 2015 Red Hat, Inc.
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

from keystoneauth1 import session as keystone
from oslo_config import cfg
from oslo_log import log as logging

from sahara import exceptions as ex
from sahara.i18n import _


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_SESSION_CACHE = None

SESSION_TYPE_CINDER = 'cinder'
SESSION_TYPE_KEYSTONE = 'keystone'
SESSION_TYPE_NEUTRON = 'neutron'
SESSION_TYPE_NOVA = 'nova'
SESSION_TYPE_GLANCE = 'glance'
SESSION_TYPE_INSECURE = 'insecure'
SESSION_TYPE_HEAT = 'heat'


def cache():
    global _SESSION_CACHE
    if not _SESSION_CACHE:
        _SESSION_CACHE = SessionCache()
    return _SESSION_CACHE


class SessionCache(object):
    '''A cache of keystone Session objects

    When a requested Session is not currently cached, it will be
    acquired from specific information in this module. Sessions should
    be referenced by their OpenStack project name and not the service
    name, this is to allow for multiple service implementations
    while retaining the ability to generate Session objects. In all
    cases, the constant values in this module should be used to
    communicate the session type.

    '''
    def __init__(self):
        '''create a new SessionCache'''
        self._sessions = {}
        self._session_funcs = {
            SESSION_TYPE_CINDER: self.get_cinder_session,
            SESSION_TYPE_KEYSTONE: self.get_keystone_session,
            SESSION_TYPE_NEUTRON: self.get_neutron_session,
            SESSION_TYPE_NOVA: self.get_nova_session,
            SESSION_TYPE_GLANCE: self.get_glance_session,
            SESSION_TYPE_INSECURE: self.get_insecure_session,
            SESSION_TYPE_HEAT: self.get_heat_session,
        }

    def _set_session(self, session_type, session):
        '''Set the session for a given type.

        :param session_type: the type of session to set.

        :param session: the session to associate with the type
        '''
        self._sessions[session_type] = session

    def get_session(self, session_type=SESSION_TYPE_INSECURE):
        '''Return a Session for the requested type

        :param session_type: the type of Session to get, if None an insecure
        session will be returned.

        :raises SaharaException: if the requested session type is not
        found.
        '''
        session_function = self._session_funcs.get(session_type)
        if session_function:
            return session_function()
        else:
            LOG.error('Requesting an unknown session type (type: {type})'.
                      format(type=session_type))
            raise ex.SaharaException(
                _('Session type {type} not recognized').
                format(type=session_type))

    def get_insecure_session(self):
        session = self._sessions.get(SESSION_TYPE_INSECURE)
        if not session:
            session = keystone.Session(verify=False)
            self._set_session(SESSION_TYPE_INSECURE, session)
        return session

    def get_cinder_session(self):
        session = self._sessions.get(SESSION_TYPE_CINDER)
        if not session:
            if not CONF.cinder.api_insecure:
                session = keystone.Session(
                    verify=CONF.cinder.ca_file or True)
            else:
                session = self.get_insecure_session()
            self._set_session(SESSION_TYPE_CINDER, session)
        return session

    def get_keystone_session(self):
        session = self._sessions.get(SESSION_TYPE_KEYSTONE)
        if not session:
            if not CONF.keystone.api_insecure:
                session = keystone.Session(
                    verify=CONF.keystone.ca_file or True)
            else:
                session = self.get_insecure_session()
            self._set_session(SESSION_TYPE_KEYSTONE, session)
        return session

    def get_neutron_session(self):
        session = self._sessions.get(SESSION_TYPE_NEUTRON)
        if not session:
            if not CONF.neutron.api_insecure:
                session = keystone.Session(
                    verify=CONF.neutron.ca_file or True)
            else:
                session = self.get_insecure_session()
            self._set_session(SESSION_TYPE_NEUTRON, session)
        return session

    def get_nova_session(self):
        session = self._sessions.get(SESSION_TYPE_NOVA)
        if not session:
            if not CONF.nova.api_insecure:
                session = keystone.Session(
                    verify=CONF.nova.ca_file or True)
            else:
                session = self.get_insecure_session()
            self._set_session(SESSION_TYPE_NOVA, session)
        return session

    def get_glance_session(self):
        session = self._sessions.get(SESSION_TYPE_GLANCE)
        if not session:
            if not CONF.glance.api_insecure:
                session = keystone.Session(verify=CONF.glance.ca_file or True)
            else:
                session = self.get_insecure_session()
            self._set_session(SESSION_TYPE_GLANCE, session)
        return session

    def get_heat_session(self):
        session = self._sessions.get(SESSION_TYPE_HEAT)
        if not session:
            if not CONF.heat.api_insecure:
                session = keystone.Session(verify=CONF.heat.ca_file or True)
            else:
                session = self.get_insecure_session()
            self._set_session(SESSION_TYPE_HEAT, session)
        return session

    def token_for_auth(self, auth):
        return self.get_keystone_session().get_auth_headers(auth).get(
            'X-Auth-Token')
