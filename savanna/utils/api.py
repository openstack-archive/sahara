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

import inspect
import mimetypes
import traceback

import flask
from werkzeug import datastructures

from savanna import context
from savanna.openstack.common import log as logging
from savanna.openstack.common import wsgi

LOG = logging.getLogger(__name__)


class Rest(flask.Blueprint):
    def get(self, rule, status_code=200):
        return self._mroute('GET', rule, status_code)

    def post(self, rule, status_code=202):
        return self._mroute('POST', rule, status_code)

    def post_file(self, rule, status_code=202):
        return self._mroute('POST', rule, status_code, file_upload=True)

    def put(self, rule, status_code=202):
        return self._mroute('PUT', rule, status_code)

    def delete(self, rule, status_code=204):
        return self._mroute('DELETE', rule, status_code)

    def _mroute(self, methods, rule, status_code=None, **kw):
        if type(methods) is str:
            methods = [methods]
        return self.route(rule, methods=methods, status_code=status_code, **kw)

    def route(self, rule, **options):
        status = options.pop('status_code', None)
        file_upload = options.pop('file_upload', False)

        def decorator(func):
            endpoint = options.pop('endpoint', func.__name__)

            def handler(**kwargs):
                # extract response content type
                resp_type = flask.request.accept_mimetypes
                type_suffix = kwargs.pop('resp_type', None)
                if type_suffix:
                    suffix_mime = mimetypes.guess_type("res." + type_suffix)[0]
                    if suffix_mime:
                        resp_type = datastructures.MIMEAccept(
                            [(suffix_mime, 1)])
                flask.request.resp_type = resp_type
                flask.request.file_upload = file_upload

                # update status code
                if status:
                    flask.request.status_code = status

                kwargs.pop("tenant_id")

                ctx = context.Context(
                    flask.request.headers['X-User-Id'],
                    flask.request.headers['X-Tenant-Id'],
                    flask.request.headers[
                        'X-Auth-Token'],
                    flask.request.headers)
                context.set_ctx(ctx)

                # set func implicit args
                args = inspect.getargspec(func).args

                if 'ctx' in args:
                    kwargs['ctx'] = ctx
                if 'request' in args:
                    kwargs['request'] = flask.request

                if flask.request.method in ['POST', 'PUT'] and 'data' in args:
                    kwargs['data'] = request_data()

                return func(**kwargs)

            f_rule = "/<tenant_id>" + rule
            self.add_url_rule(f_rule, endpoint, handler, **options)
            ext_rule = f_rule + '.<resp_type>'
            self.add_url_rule(ext_rule, endpoint, handler, **options)

            try:
                return func
            except Exception, e:
                return internal_error(500, 'Exception in API call', e)

        return decorator


RT_JSON = datastructures.MIMEAccept([("application/json", 1)])
RT_XML = datastructures.MIMEAccept([("application/xml", 1)])


def _clean_nones(obj):
    if not isinstance(obj, dict) and not isinstance(obj, list):
        return obj

    if isinstance(obj, dict):
        remove = []
        for key, value in obj.iteritems():
            if value is None:
                remove.append(key)
        for key in remove:
            obj.pop(key)
        for value in obj.values():
            _clean_nones(value)
    elif isinstance(obj, list):
        new_list = []
        for elem in obj:
            elem = _clean_nones(elem)
            if elem is not None:
                new_list.append(elem)
        return new_list

    return obj


def render(res=None, resp_type=None, status=None, **kwargs):
    if not res:
        res = {}
    if type(res) is dict:
        res.update(kwargs)
    elif kwargs:
        # can't merge kwargs into the non-dict res
        abort_and_log(500, "Non-dict and non-empty kwargs passed to render")

    res = _clean_nones(res)

    status_code = getattr(flask.request, 'status_code', None)
    if status:
        status_code = status
    if not status_code:
        status_code = 200

    if not resp_type:
        resp_type = getattr(flask.request, 'resp_type', RT_JSON)

    if not resp_type:
        resp_type = RT_JSON

    serializer = None
    if "application/json" in resp_type:
        resp_type = RT_JSON
        serializer = wsgi.JSONDictSerializer()
    elif "application/xml" in resp_type:
        resp_type = RT_XML
        serializer = wsgi.XMLDictSerializer()
    else:
        abort_and_log(400, "Content type '%s' isn't supported" % resp_type)

    body = serializer.serialize(res)
    resp_type = str(resp_type)

    return flask.Response(response=body, status=status_code,
                          mimetype=resp_type)


def request_data():
    if hasattr(flask.request, 'parsed_data'):
        return flask.request.parsed_data

    if not flask.request.content_length > 0:
        LOG.debug("Empty body provided in request")
        return dict()

    if flask.request.file_upload:
        return flask.request.data

    deserializer = None
    content_type = flask.request.mimetype
    if not content_type or content_type in RT_JSON:
        deserializer = wsgi.JSONDeserializer()
    elif content_type in RT_XML:
        abort_and_log(400, "XML requests are not supported yet")
        # deserializer = XMLDeserializer()
    else:
        abort_and_log(400, "Content type '%s' isn't supported" % content_type)

    # parsed request data to avoid unwanted re-parsings
    parsed_data = deserializer.deserialize(flask.request.data)['body']
    flask.request.parsed_data = parsed_data

    return flask.request.parsed_data


def abort_and_log(status_code, descr, exc=None):
    LOG.error("Request aborted with status code %s and message '%s'",
              status_code, descr)

    if exc is not None:
        LOG.error(traceback.format_exc())

    flask.abort(status_code, description=descr)


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

    error_code = "INTERNAL_SERVER_ERROR"
    if status_code == 501:
        error_code = "NOT_IMPLEMENTED_ERROR"

    return render_error_message(status_code, descr, error_code)


def bad_request(error):
    error_code = 400

    LOG.debug("Validation Error occurred: "
              "error_code=%s, error_message=%s, error_name=%s",
              error_code, error.message, error.code)

    return render_error_message(error_code, error.message, error.code)


def not_found(error):
    error_code = 404

    LOG.debug("Not Found exception occurred: "
              "error_code=%s, error_message=%s, error_name=%s",
              error_code, error.message, error.code)

    return render_error_message(error_code, error.message, error.code)
