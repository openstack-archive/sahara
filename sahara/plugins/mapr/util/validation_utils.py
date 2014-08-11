# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import functools as ft

from sahara.i18n import _
import sahara.plugins.exceptions as e
import sahara.plugins.mapr.util.cluster_info as ci
import sahara.plugins.mapr.util.wrapper as w


class LessThanCountException(e.InvalidComponentCountException):

    def __init__(self, component, expected_count, count):
        super(LessThanCountException, self).__init__(
            component, expected_count, count)
        self.message = (_("Hadoop cluster should contain at least"
                          " %(expected_count)d %(component)s component(s)."
                          " Actual %(component)s count is %(count)d")
                        % {'expected_count': expected_count,
                           'component': component, 'count': count})


class MoreThanCountException(e.InvalidComponentCountException):

    def __init__(self, component, expected_count, count):
        super(MoreThanCountException, self).__init__(
            component, expected_count, count)
        self.message = (_("Hadoop cluster should contain not more than"
                          " %(expected_count)d %(component)s component(s)."
                          " Actual %(component)s count is %(count)d")
                        % {'expected_count': expected_count,
                           'component': component, 'count': count})


class NodeRequiredServiceMissingException(e.RequiredServiceMissingException):

    def __init__(self, service_name, required_by=None):
        super(NodeRequiredServiceMissingException, self).__init__(
            service_name, required_by)
        self.message = _('Node is missing a service: %s') % service_name
        if required_by:
            self.message = (_('%(message)s, required by service:'
                              ' %(required_by)s')
                            % {'message': self.message,
                               'required_by': required_by})


def not_less_than_count_component_vr(component, count):
    def validate(cluster, component, count):
        c_info = ci.ClusterInfo(cluster, None)
        actual_count = c_info.get_instances_count(component)
        if not actual_count >= count:
            raise LessThanCountException(component, count, actual_count)
    return ft.partial(validate, component=component, count=count)


def not_more_than_count_component_vr(component, count):
    def validate(cluster, component, count):
        c_info = ci.ClusterInfo(cluster, None)
        actual_count = c_info.get_instances_count(component)
        if not actual_count <= count:
            raise MoreThanCountException(component, count, actual_count)
    return ft.partial(validate, component=component, count=count)


def equal_count_component_vr(component, count):
    def validate(cluster, component, count):
        c_info = ci.ClusterInfo(cluster, None)
        actual_count = c_info.get_instances_count(component)
        if not actual_count == count:
            raise e.InvalidComponentCountException(
                component, count, actual_count)
    return ft.partial(validate, component=component, count=count)


def require_component_vr(component):
    def validate(instance, component):
        if component not in instance.node_group.node_processes:
            raise NodeRequiredServiceMissingException(component)
    return ft.partial(validate, component=component)


def require_of_listed_components(components):
    def validate(instance, components):
        if (False in (c in instance.node_group.node_processes
                      for c in components)):
            raise NodeRequiredServiceMissingException(components)
    return ft.partial(validate, components=components)


def each_node_has_component_vr(component):
    def validate(cluster, component):
        rc_vr = require_component_vr(component)
        c_info = ci.ClusterInfo(cluster, None)
        for i in c_info.get_instances():
            rc_vr(i)
    return ft.partial(validate, component=component)


def each_node_has_at_least_one_of_listed_components(components):
    def validate(cluster, components):
        rc_vr = require_of_listed_components(components)
        c_info = ci.ClusterInfo(cluster, None)
        for i in c_info.get_instances():
            rc_vr(i)
    return ft.partial(validate, components=components)


def node_dependency_satisfied_vr(component, dependency):
    def validate(cluster, component, dependency):
        c_info = ci.ClusterInfo(cluster, None)
        for ng in c_info.get_node_groups(component):
            if dependency not in ng.node_processes:
                raise NodeRequiredServiceMissingException(
                    component, dependency)
    return ft.partial(validate, component=component, dependency=dependency)


def create_fake_cluster(cluster, existing, additional):
    w_node_groups = [w.Wrapper(ng, count=existing[ng.id])
                     if ng.id in existing else ng
                     for ng in cluster.node_groups]
    return w.Wrapper(cluster, node_groups=w_node_groups)
