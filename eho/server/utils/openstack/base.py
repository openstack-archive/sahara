import json


def url_for(headers, service_type, admin=False, endpoint_type=None):
    if not endpoint_type:
        endpoint_type = 'publicURL'
    if admin:
        endpoint_type = 'adminURL'

    catalog = headers['X-Service-Catalog']
    service = _get_service_from_catalog(catalog, service_type)

    if service:
        return service['endpoints'][0][endpoint_type]
    else:
        raise Exception('Service "%s" not found' % service_type)


def _get_service_from_catalog(catalog, service_type):
    if catalog:
        catalog = json.loads(catalog)
        for service in catalog:
            if service['type'] == service_type:
                return service

    return None
