# Copyright (c) 2014 Intel Corporation.
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
#
# The contents of this file are mainly copied from cm_api sources,
# released by Cloudrea. Codes not used by Sahara CDH plugin are removed.
# You can find the original codes at
#
#     https://github.com/cloudera/cm_api/tree/master/python/src/cm_api
#
# To satisfy the pep8 and python3 tests, we did some changes to the codes.
# We also change some importings to use Sahara inherited classes.

import json
import posixpath
import socket
import urllib2

from oslo_log import log as logging
import six

from sahara import context
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.i18n import _LW
from sahara.plugins.cdh import exceptions as ex

LOG = logging.getLogger(__name__)


class Resource(object):
    """Base Resource

    Encapsulates a resource, and provides actions to invoke on it.
    """
    def __init__(self, client, relpath=""):
        """Constructor method

        :param client: A Client object.
        :param relpath: The relative path of the resource.
        """
        self._client = client
        self._path = relpath.strip('/')
        self.retries = 3
        self.retry_sleep = 3

    @property
    def base_url(self):
        return self._client.base_url

    def _join_uri(self, relpath):
        if relpath is None:
            return self._path
        return self._path + posixpath.normpath('/' + relpath)

    def invoke(self, method, relpath=None, params=None, data=None,
               headers=None):
        """Invoke an API method

        :return: Raw body or JSON dictionary (if response content type is
                 JSON).
        """
        path = self._join_uri(relpath)
        resp = self._client.execute(method,
                                    path,
                                    params=params,
                                    data=data,
                                    headers=headers)
        try:
            body = resp.read()
        except Exception as ex:
            raise ex.CMApiException(
                _("Command %(method)s %(path)s failed: %(msg)s")
                % {'method': method, 'path': path, 'msg': six.text_type(ex)})

        LOG.debug("{method} got response: {body}".format(method=method,
                                                         body=body[:32]))
        # Is the response application/json?
        if (len(body) != 0 and resp.info().getmaintype() == "application"
                and resp.info().getsubtype() == "json"):
            try:
                json_dict = json.loads(body)
                return json_dict
            except Exception as ex:
                LOG.error(_LE('JSON decode error: {body}').format(body=body))
                raise ex
        else:
            return body

    def get(self, relpath=None, params=None):
        """Invoke the GET method on a resource

        :param relpath: Optional. A relative path to this resource's path.
        :param params: Key-value data.

        :return: A dictionary of the JSON result.
        """
        for retry in six.moves.xrange(self.retries + 1):
            if retry:
                context.sleep(self.retry_sleep)
            try:
                return self.invoke("GET", relpath, params)
            except (socket.error, urllib2.URLError) as e:
                if "timed out" in six.text_type(e).lower():
                    if retry < self.retries:
                        LOG.warning(_LW("Timeout issuing GET request for "
                                        "{path}. Will retry").format(
                                            path=self._join_uri(relpath)))
                    else:
                        LOG.warning(_LW("Timeout issuing GET request for "
                                        "{path}. No retries left").format(
                                            path=self._join_uri(relpath)))
                else:
                    raise e
        else:
            raise ex.CMApiException(_("Get retry max time reached."))

    def delete(self, relpath=None, params=None):
        """Invoke the DELETE method on a resource

        :param relpath: Optional. A relative path to this resource's path.
        :param params: Key-value data.

        :return: A dictionary of the JSON result.
        """
        return self.invoke("DELETE", relpath, params)

    def post(self, relpath=None, params=None, data=None, contenttype=None):
        """Invoke the POST method on a resource

        :param relpath: Optional. A relative path to this resource's path.
        :param params: Key-value data.
        :param data: Optional. Body of the request.
        :param contenttype: Optional.

        :return: A dictionary of the JSON result.
        """
        return self.invoke("POST", relpath, params, data,
                           self._make_headers(contenttype))

    def put(self, relpath=None, params=None, data=None, contenttype=None):
        """Invoke the PUT method on a resource

        :param relpath: Optional. A relative path to this resource's path.
        :param params: Key-value data.
        :param data: Optional. Body of the request.
        :param contenttype: Optional.

        :return: A dictionary of the JSON result.
        """
        return self.invoke("PUT", relpath, params, data,
                           self._make_headers(contenttype))

    def _make_headers(self, contenttype=None):
        if contenttype:
            return {'Content-Type': contenttype}
        return None
