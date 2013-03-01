import mimetypes
import json
import logging

from flask import abort, request, Blueprint, Response
from werkzeug.datastructures import MIMEAccept

from eho.server.utils import xml


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

                return func(**kwargs)

            self.add_url_rule(rule, endpoint, handler, **options)
            ext_rule = rule + '.<resp_type>'
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

    body = None
    if "application/json" in resp_type:
        resp_type = RT_JSON
        body = json.dumps(res)
    elif "application/xml" in resp_type:
        resp_type = RT_XML
        body = xml.dumps(res)
    else:
        raise abort_and_log(400, "%s isn't supported" % resp_type)

    resp_type = resp_type.__str__()
    return Response(response=body, status=status_code, mimetype=resp_type)


def request_data():
    # should check body, content type, etc
    # should support different request types
    return json.loads(request.data)


def abort_and_log(status_code, descr):
    logging.error("Request aborted with status code %s and message '%s'",
                  status_code, descr)
    abort(status_code, description=descr)
