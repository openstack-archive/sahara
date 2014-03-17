# Copyright (c) 2013 Intel Corporation
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

from requests import auth

from sahara.openstack.common import log as logging
from sahara.plugins.intel import exceptions as iex


LOG = logging.getLogger(__name__)


def _check_response(fct):
    def wrapper(*args, **kwargs):
        resp = fct(*args, **kwargs)
        if not resp.ok:
            raise iex.IntelPluginException(
                "Request to manager returned with code '%s', reason '%s' and "
                "response '%s'" % (resp.status_code, resp.reason, resp.text))
        else:
            return json.loads(resp.text)

    return wrapper


class RESTClient():
    def __init__(self, manager, auth_username, auth_password, version):
        #TODO(alazarev) make port configurable (bug #1262895)
        port = '9443'
        self.session = manager.remote().get_http_client(port, max_retries=10)
        self.base_url = ('https://%s:%s/restapi/intelcloud/api/%s'
                         % (manager.management_ip, port, version))
        LOG.debug("Connecting to manager with URL of %s", self.base_url)

        self.auth = auth.HTTPBasicAuth(auth_username, auth_password)

    @_check_response
    def get(self, url):
        url = self.base_url + url
        LOG.debug("Sending GET to URL of %s", url)
        return self.session.get(url, verify=False, auth=self.auth)

    @_check_response
    def post(self, url, data=None, files=None):
        url = self.base_url + url
        LOG.debug("Sending POST to URL '%s' (%s files): %s", url,
                  len(files) if files else 0,
                  data if data else 'no data')
        return self.session.post(url, data=json.dumps(data) if data else None,
                                 verify=False, auth=self.auth, files=files)

    @_check_response
    def delete(self, url):
        url = self.base_url + url
        LOG.debug("Sending DELETE to URL of %s", url)
        return self.session.delete(url, verify=False, auth=self.auth)

    @_check_response
    def put(self, url, data=None):
        url = self.base_url + url
        if data:
            LOG.debug("Sending PUT to URL of %s: %s", url, data)
            r = self.session.put(url, data=json.dumps(data), verify=False,
                                 auth=self.auth)
        else:
            LOG.debug("Sending PUT to URL of %s with no data", url)
            r = self.session.put(url, verify=False, auth=self.auth)

        return r
