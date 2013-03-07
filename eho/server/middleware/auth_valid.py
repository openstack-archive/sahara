import logging
from eho.common.common import split_path
from webob.exc import HTTPServiceUnavailable, HTTPNotFound, HTTPUnauthorized


class AuthValidator:
    """
    Auth Validation Middleware handles token auth results and tenants
    """

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf

    def __call__(self, env, start_response):
        """
        Handle incoming request by checking tenant info prom the headers and
        url ({tenant_id} url attribute).

        Pass request downstream on success.
        Reject request if tenant_id from headers not equals to tenant_id from
        url.
        """
        token_tenant = env['HTTP_X_TENANT_ID']
        if not token_tenant:
            logging.warn("Can't get tenant_id from env")
            resp = HTTPServiceUnavailable()
            return resp(env, start_response)

        path = env['PATH_INFO']
        version, url_tenant, rest = split_path(path, 3, 3, True)

        if not version or not url_tenant or not rest:
            logging.info("Incorrect path: %s", path)
            resp = HTTPNotFound("Incorrect path")
            resp(env, start_response)

        if token_tenant != url_tenant:
            logging.debug("Unauthorized: token tenant != requested tenant")
            resp = HTTPUnauthorized('Token tenant != requested tenant')
            return resp(env, start_response)

        return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return AuthValidator(app, conf)

    return auth_filter
