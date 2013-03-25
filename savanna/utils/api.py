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

import mimetypes
import traceback

from flask import abort, request, Blueprint, Response
from werkzeug.datastructures import MIMEAccept

from savanna.openstack.common.wsgi import JSONDictSerializer, \
    XMLDictSerializer, JSONDeserializer
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class Rest(Blueprint):
    def get(self, rule, status_code=200):
        return self._mroute('GET', rule, status_code)

    def post(self, rule, status_code=202):
        return self._mroute('POST', rule, status_code)

    def put(self, rule, status_code=202):
        return self._mroute('PUT', rule, status_code)

    def delete(self, rule, status_code=204):
        return self._mroute('DELETE', rule, status_code)

    def _mroute(self, methods, rule, status_code=None):
        if type(methods) is str:
            methods = [methods]
        return self.route(rule, methods=methods, status_code=status_code)

    def route(self, rule, **options):
        status = options.pop('status_code', None)

        def decorator(func):
            endpoint = options.pop('endpoint', func.__name__)

            def handler(**kwargs):
                # extract response content type
                resp_type = request.accept_mimetypes
                type_suffix = kwargs.pop('resp_type', None)
                if type_suffix:
                    suffix_mime = mimetypes.guess_type("res." + type_suffix)[0]
                    if suffix_mime:
                        resp_type = MIMEAccept([(suffix_mime, 1)])
                request.resp_type = resp_type

                # extract fields (column selection)
                fields = list(set(request.args.getlist('fields')))
                fields.sort()
                request.fields_selector = fields

                if status:
                    request.status_code = status

                kwargs.pop("tenant_id")

                return func(**kwargs)

            f_rule = "/<tenant_id>" + rule
            self.add_url_rule(f_rule, endpoint, handler, **options)
            ext_rule = f_rule + '.<resp_type>'
            self.add_url_rule(ext_rule, endpoint, handler, **options)

            return func

        return decorator


RT_JSON = MIMEAccept([("application/json", 1)])
RT_XML = MIMEAccept([("application/xml", 1)])


def render(res=None, resp_type=None, status=None, **kwargs):
    if not res:
        res = {}
    if type(res) is dict:
        res.update(kwargs)
    elif kwargs:
        # can't merge kwargs into the non-dict res
        abort_and_log(500, "Non-dict and non-empty kwargs passed to render")

    status_code = getattr(request, 'status_code', None)
    if status:
        status_code = status
    if not status_code:
        status_code = 200

    if not resp_type:
        resp_type = getattr(request, 'resp_type', RT_JSON)

    if not resp_type:
        resp_type = RT_JSON

    serializer = None
    if "application/json" in resp_type:
        resp_type = RT_JSON
        serializer = JSONDictSerializer()
    elif "application/xml" in resp_type:
        resp_type = RT_XML
        serializer = XMLDictSerializer()
    else:
        abort_and_log(400, "Content type '%s' isn't supported" % resp_type)

    body = serializer.serialize(res)
    resp_type = str(resp_type)

    return Response(response=body, status=status_code, mimetype=resp_type)


def request_data():
    if hasattr(request, 'parsed_data'):
        return request.parsed_data

    if not request.content_length > 0:
        LOG.debug("Empty body provided in request")
        return dict()

    deserializer = None
    content_type = request.mimetype
    if not content_type or content_type in RT_JSON:
        deserializer = JSONDeserializer()
    elif content_type in RT_XML:
        abort_and_log(400, "XML requests are not supported yet")
        # deserializer = XMLDeserializer()
    else:
        abort_and_log(400, "Content type '%s' isn't supported" % content_type)

    # parsed request data to avoid unwanted re-parsings
    request.parsed_data = deserializer.deserialize(request.data)['body']

    return request.parsed_data


def abort_and_log(status_code, descr, exc=None):
    LOG.error("Request aborted with status code %s and message '%s'",
              status_code, descr)

    if exc is not None:
        LOG.error(traceback.format_exc())

    abort(status_code, description=descr)


def render_error_message(error_code, error_message, error_name):
    message = {
        "error_code": error_code,
        "error_message": error_message,
        "error_name": error_name
    }

    resp = render(message)
    resp.status_code = error_code

    return resp


def internal_error(status_code, descr, exc=None):
    LOG.error("Request aborted with status code %s and message '%s'",
              status_code, descr)

    if exc is not None:
        LOG.error(traceback.format_exc())

    return render_error_message(status_code, descr, "INTERNAL_SERVER_ERROR")


def bad_request(error):
    error_code = 400

    LOG.debug("Validation Error occurred: "
              "error_code=%s, error_message=%s, error_name=%s",
              error_code, error.message, error.code)

    return render_error_message(error_code, error.message, error.code)
