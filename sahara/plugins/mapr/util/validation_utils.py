# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import functools as ft

from sahara.conductor import resource as r
import sahara.exceptions as ex
from sahara.i18n import _
import sahara.plugins.exceptions as e
from sahara.service.api import v10 as api
import sahara.utils.openstack.nova as nova


class LessThanCountException(e.InvalidComponentCountException):
    MESSAGE = _("Hadoop cluster should contain at least"
                " %(expected_count)d %(component)s component(s)."
                " Actual %(component)s count is %(actual_count)d")

    def __init__(self, component, expected_count, count):
        super(LessThanCountException, self).__init__(
            component, expected_count, count)
        args = {
            'expected_count': expected_count,
            'component': component,
            'actual_count': count,
        }
        self.message = LessThanCountException.MESSAGE % args


class MoreThanCountException(e.InvalidComponentCountException):
    MESSAGE = _("Hadoop cluster should contain at most"
                " %(expected_count)d %(component)s component(s)."
                " Actual %(component)s count is %(actual_count)d")

    def __init__(self, component, expected_count, count):
        super(MoreThanCountException, self).__init__(
            component, expected_count, count)
        args = {
            "expected_count": expected_count,
            "component": component,
            "actual_count": count,
        }
        self.message = MoreThanCountException.MESSAGE % args


class EvenCountException(ex.SaharaException):
    MESSAGE = _("Hadoop cluster should contain odd number of %(component)s"
                " but %(actual_count)s found.")

    def __init__(self, component, count):
        super(EvenCountException, self).__init__()
        args = {'component': component, 'actual_count': count}
        self.message = EvenCountException.MESSAGE % args


class NodeRequiredServiceMissingException(e.RequiredServiceMissingException):
    MISSING_MSG = _('Node "%(ng_name)s" is missing component %(component)s')
    REQUIRED_MSG = _('%(message)s, required by %(required_by)s')

    def __init__(self, service_name, ng_name, required_by=None):
        super(NodeRequiredServiceMissingException, self).__init__(
            service_name, required_by)
        args = {'ng_name': ng_name, 'component': service_name}
        self.message = (
            NodeRequiredServiceMissingException.MISSING_MSG % args)
        if required_by:
            args = {'message': self.message, 'required_by': required_by}
            self.message = (
                NodeRequiredServiceMissingException.REQUIRED_MSG % args)


class NodeServiceConflictException(ex.SaharaException):
    MESSAGE = _('%(service)s service cannot be installed alongside'
                ' %(package)s package')
    ERROR_CODE = "NODE_PROCESS_CONFLICT"

    def __init__(self, service_name, conflicted_package):
        super(NodeServiceConflictException, self).__init__()
        args = {
            'service': service_name,
            'package': conflicted_package,
        }
        self.message = NodeServiceConflictException.MESSAGE % args
        self.code = NodeServiceConflictException.ERROR_CODE


class NoVolumesException(ex.SaharaException):
    MESSAGE = _('%s must have at least 1 volume or ephemeral drive')
    ERROR_CODE = "NO_VOLUMES"

    def __init__(self, ng_name):
        super(NoVolumesException, self).__init__()
        self.message = NoVolumesException.MESSAGE % ng_name
        self.code = NoVolumesException.ERROR_CODE


class NotRequiredImageException(ex.SaharaException):
    MESSAGE = _('Service %(service)s requires %(os)s OS.'
                ' Use %(os)s image and add "%(os)s" tag to it.')
    ERROR_CODE = "INVALID_IMAGE"

    def __init__(self, service, os):
        super(NotRequiredImageException, self).__init__()
        self.message = NotRequiredImageException.MESSAGE % {'service': service,
                                                            'os': os}
        self.code = NotRequiredImageException.ERROR_CODE


def at_least(count, component):
    def validate(cluster_context, component, count):
        actual_count = cluster_context.get_instances_count(component)
        if not actual_count >= count:
            raise LessThanCountException(
                component.ui_name, count, actual_count)

    return ft.partial(validate, component=component, count=count)


def at_most(count, component):
    def validate(cluster_context, component, count):
        actual_count = cluster_context.get_instances_count(component)
        if actual_count > count:
            raise MoreThanCountException(
                component.ui_name, count, actual_count)

    return ft.partial(validate, component=component, count=count)


def exactly(count, component):
    def validate(cluster_context, component, count):
        actual_count = cluster_context.get_instances_count(component)
        if not actual_count == count:
            raise e.InvalidComponentCountException(
                component.ui_name, count, actual_count)

    return ft.partial(validate, component=component, count=count)


def each_node_has(component):
    def validate(cluster_context, component):
        for node_group in cluster_context.cluster.node_groups:
            if component.ui_name not in node_group.node_processes:
                raise NodeRequiredServiceMissingException(
                    component.ui_name, node_group.name)

    return ft.partial(validate, component=component)


def odd_count_of(component):
    def validate(cluster_context, component):
        actual_count = cluster_context.get_instances_count(component)
        if actual_count > 1 and actual_count % 2 == 0:
            raise EvenCountException(component.ui_name, actual_count)

    return ft.partial(validate, component=component)


def on_same_node(component, dependency):
    def validate(cluster_context, component, dependency):
        for ng in cluster_context.get_node_groups(component):
            if dependency.ui_name not in ng.node_processes:
                raise NodeRequiredServiceMissingException(
                    dependency.ui_name, ng.name, component.ui_name)

    return ft.partial(validate, component=component, dependency=dependency)


def depends_on(service, required_by):
    def validate(cluster_context, service, required_by):
        if not cluster_context.is_present(service):
            service_name = service.ui_name
            if service.version:
                service_name += " %s" % service.version

            raise e.RequiredServiceMissingException(
                service_name, required_by.ui_name)

    return ft.partial(validate, service=service, required_by=required_by)


def node_client_package_conflict_vr(components, client_component):
    def validate(cluster_context, components):
        for ng in cluster_context.get_node_groups():
            for c in components:
                nps = ng.node_processes
                if c in nps and client_component in nps:
                    raise NodeServiceConflictException(c, client_component)

    return ft.partial(validate, components=components)


def assert_present(service, cluster_context):
    if not cluster_context.is_present(service):
        raise e.RequiredServiceMissingException(service.ui_name)


def required_os(os, required_by):
    def validate(cluster_context, os, required_by):
        for ng in cluster_context.get_node_groups():
            nps = ng.node_processes
            for node_process in required_by.node_processes:
                if node_process.ui_name in nps:
                    image_id = (ng.image_id or
                                cluster_context.cluster.default_image_id)
                    if not image_has_tag(image_id, os):
                        raise NotRequiredImageException(required_by.ui_name,
                                                        os)

    return ft.partial(validate, os=os, required_by=required_by)


def create_fake_cluster(cluster, existing, additional):
    counts = existing.copy()
    counts.update(additional)

    def update_ng(node_group):
        ng_dict = node_group.to_dict()
        count = counts[node_group.id]
        ng_dict.update(dict(count=count))
        return r.NodeGroupResource(ng_dict)

    def need_upd(node_group):
        return node_group.id in counts and counts[node_group.id] > 0

    updated = map(update_ng, filter(need_upd, cluster.node_groups))
    not_updated = filter(lambda ng:
                         not need_upd(ng) and ng is not None,
                         cluster.node_groups)
    cluster_dict = cluster.to_dict()
    cluster_dict.update({'node_groups': updated + not_updated})
    fake = r.ClusterResource(cluster_dict)
    return fake


def get_ephemeral(node_group):
    return nova.get_flavor(id=node_group.flavor_id).ephemeral


def has_volumes():
    def validate(cluster_context):
        for node_group in cluster_context.cluster.node_groups:
            if not (node_group.volumes_per_node or get_ephemeral(node_group)):
                raise NoVolumesException(node_group.name)

    return validate


def image_has_tag(image_id, tag):
    image = api.get_registered_image(image_id)
    return tag in image.tags
