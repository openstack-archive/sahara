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

import cookielib
import json
import posixpath
import types
import urllib
import urllib2

from oslo_log import log as logging
import six

from sahara.i18n import _LW
from sahara.plugins.cdh import exceptions as ex

LOG = logging.getLogger(__name__)


class HttpClient(object):
    """Basic HTTP client tailored for rest APIs."""
    def __init__(self, base_url, exc_class=ex.CMApiException):
        """Init Method

        :param base_url: The base url to the API.
        :param exc_class: An exception class to handle non-200 results.

        Creates an HTTP(S) client to connect to the Cloudera Manager API.
        """
        self._base_url = base_url.rstrip('/')
        self._exc_class = exc_class
        self._headers = {}

        # Make a basic auth handler that does nothing. Set credentials later.
        self._passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        authhandler = urllib2.HTTPBasicAuthHandler(self._passmgr)

        # Make a cookie processor
        cookiejar = cookielib.CookieJar()

        self._opener = urllib2.build_opener(
            urllib2.HTTPErrorProcessor(),
            urllib2.HTTPCookieProcessor(cookiejar),
            authhandler)

    def set_basic_auth(self, username, password, realm):
        """Set up basic auth for the client

        :param username: Login name.
        :param password: Login password.
        :param realm: The authentication realm.
        :return: The current object
        """
        self._passmgr.add_password(realm, self._base_url, username, password)
        return self

    def set_headers(self, headers):
        """Add headers to the request

        :param headers: A dictionary with the key value pairs for the headers
        :return: The current object
        """
        self._headers = headers
        return self

    @property
    def base_url(self):
        return self._base_url

    def _get_headers(self, headers):
        res = self._headers.copy()
        if headers:
            res.update(headers)
        return res

    def execute(self, http_method, path, params=None, data=None, headers=None):
        """Submit an HTTP request

        :param http_method: GET, POST, PUT, DELETE
        :param path: The path of the resource.
        :param params: Key-value parameter data.
        :param data: The data to attach to the body of the request.
        :param headers: The headers to set for this request.

        :return: The result of urllib2.urlopen()
        """
        # Prepare URL and params
        url = self._make_url(path, params)
        if http_method in ("GET", "DELETE"):
            if data is not None:
                LOG.warning(_LW("{method} method does not pass any data. "
                                "Path {path}").format(method=http_method,
                                                      path=path))
                data = None

        # Setup the request
        request = urllib2.Request(url, data)
        # Hack/workaround because urllib2 only does GET and POST
        request.get_method = lambda: http_method

        headers = self._get_headers(headers)
        for k, v in headers.items():
            request.add_header(k, v)

        # Call it
        LOG.debug("Method: {method}, URL: {url}".format(method=http_method,
                                                        url=url))
        try:
            return self._opener.open(request)
        except urllib2.HTTPError as ex:
            message = six.text_type(ex)
            try:
                json_body = json.loads(message)
                message = json_body['message']
            except (ValueError, KeyError):
                pass    # Ignore json parsing error
            raise self._exc_class(message)

    def _make_url(self, path, params):
        res = self._base_url
        if path:
            res += posixpath.normpath('/' + path.lstrip('/'))
        if params:
            param_str = urllib.urlencode(params, True)
            res += '?' + param_str
        return iri_to_uri(res)


#
# Method copied from Django
#
def iri_to_uri(iri):
    """Convert IRI to URI

    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from section 3.1 of RFC 3987.  However, since we are
    assuming input is either UTF-8 or unicode already, we can simplify things a
    little from the full method.

    Returns an ASCII string containing the encoded result.
    """
    # The list of safe characters here is constructed from the "reserved" and
    # "unreserved" characters specified in sections 2.2 and 2.3 of RFC 3986:
    #     reserved    = gen-delims / sub-delims
    #     gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    #     sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #                   / "*" / "+" / "," / ";" / "="
    #     unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # Of the unreserved characters, urllib.quote already considers all but
    # the ~ safe.
    # The % character is also added to the list of safe characters here, as the
    # end of section 3.1 of RFC 3987 specifically mentions that % must not be
    # converted.
    if iri is None:
        return iri
    return urllib.quote(smart_str(iri), safe="/#%[]=:;$&()+,!?*@'~")


#
# Method copied from Django
#
def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """Convert string into bytestring version

    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    elif not isinstance(s, basestring):
        try:
            return six.text_type(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                                errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s
