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
import requests
from requests import auth

from savanna.openstack.common import log as logging
from savanna.plugins.intel import exceptions as iex


LOG = logging.getLogger(__name__)


class RESTClient():
    def __init__(self, manager_ip, auth_username, auth_password):
        #TODO(alazarev) make port configurable (bug #1262895)
        self.base_url = ('https://%s:9443/restapi/intelcloud/api/v1'
                         % manager_ip)
        LOG.debug("Connecting to manager with URL of %s", self.base_url)

        self.auth = auth.HTTPBasicAuth(auth_username, auth_password)

    def get(self, url):
        url = self.base_url + url
        LOG.debug("Sending GET to URL of %s", url)
        r = requests.get(url, verify=False, auth=self.auth)
        return self._check_response(r)

    def post(self, url, data=None, files=None):
        url = self.base_url + url
        LOG.debug("Sending POST to URL '%s' (%s files): %s", url,
                  len(files) if files else 0,
                  data if data else 'no data')
        r = requests.post(url, data=json.dumps(data) if data else None,
                          verify=False, auth=self.auth, files=files)
        return self._check_response(r)

    def delete(self, url):
        url = self.base_url + url
        LOG.debug("Sending DELETE to URL of %s", url)
        r = requests.delete(url, verify=False, auth=self.auth)
        return self._check_response(r)

    def put(self, url, data=None):
        url = self.base_url + url
        if data:
            LOG.debug("Sending PUT to URL of %s: %s", url, data)
            r = requests.put(url, data=json.dumps(data), verify=False,
                             auth=self.auth)
        else:
            LOG.debug("Sending PUT to URL of %s with no data", url)
            r = requests.put(url, verify=False, auth=self.auth)

        return self._check_response(r)

    def _check_response(self, resp):
        LOG.debug("Response with HTTP code %s, and content of %s",
                  resp.status_code, resp.text)
        if not resp.ok:
            raise iex.IntelPluginException(
                "Request to manager returned with code '%s', reason '%s' "
                "and message '%s'" % (resp.status_code, resp.reason,
                                      json.loads(resp.text)['message']))
        else:
            return json.loads(resp.text)
