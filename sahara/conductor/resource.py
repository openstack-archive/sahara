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

"""Provides means to wrap dicts coming from DB layer in objects.

The Conductor can fetch only values represented by JSON.
That limitation comes from Oslo RPC implementation.
This module provides means to wrap a fetched value, always
dictionary, into an immutable Resource object. A descendant of
Resource class might provide back references to parent objects
and helper methods.
"""

import datetime

import six

from sahara.conductor import objects
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp import s3_common
from sahara.swift import swift_helper
from sahara.utils import types


def wrap(resource_class):
    """A decorator wraps dict returned by a given function into a Resource."""

    def decorator(func):
        def handle(*args, **kwargs):
            ret = func(*args, **kwargs)
            if isinstance(ret, types.Page):
                return types.Page([resource_class(el) for el in ret],
                                  ret.prev, ret.next)
            elif isinstance(ret, list):
                return [resource_class(el) for el in ret]
            elif ret:
                return resource_class(ret)
            else:
                return None

        return handle

    return decorator


class Resource(types.FrozenDict):
    """Represents dictionary as an immutable object.

    Enhancing it with back references and helper methods.

    For instance, the following dictionary:
    {'first': {'a': 1, 'b': 2}, 'second': [1,2,3]}

    after wrapping with Resource will look like an object, let it be
    'res' with the following fields:
    res.first
    res.second

    'res.first' will in turn be wrapped into Resource with two fields:
    res.first.a == 1
    res.first.b == 2

    'res.second', which is a list, will be transformed into a tuple
    for immutability:
    res.second == (1,2,3)

    Additional helper methods could be specified in descendant
    classes. '_children' specifies children of that specific Resource
    in the following format: {refname: (child_class, backref_name)}
    Back reference is a reference to parent object which is
    injected into a Resource during wrapping.
    """

    _resource_name = 'resource'
    _children = {}
    _filter_fields = []
    _sanitize_fields = {}

    def __init__(self, dct):
        super(Resource, self).__setattr__('_initial_dict', dct)
        newdct = dict()
        for refname, entity in six.iteritems(dct):
            newdct[refname] = self._wrap_entity(refname, entity)

        super(Resource, self).__init__(newdct)

    def to_dict(self):
        """Return dictionary representing the Resource for REST API.

        On the way filter out fields which shouldn't be exposed.
        """
        return self._to_dict(None)

    def to_wrapped_dict(self):
        return {self._resource_name: self.to_dict()}

    # Construction

    def _wrap_entity(self, refname, entity):
        if isinstance(entity, Resource):
            # that is a back reference
            return entity
        elif isinstance(entity, list):
            return self._wrap_list(refname, entity)
        elif isinstance(entity, dict):
            return self._wrap_dict(refname, entity)
        elif self._is_passthrough_type(entity):
            return entity
        else:
            raise TypeError(_("Unsupported type: %s") % type(entity).__name__)

    def _wrap_list(self, refname, lst):
        newlst = [self._wrap_entity(refname, entity) for entity in lst]

        return types.FrozenList(newlst)

    def _wrap_dict(self, refname, dct):
        if refname in self._children:
            dct = dict(dct)
            child_class = self._children[refname][0]
            backref_name = self._children[refname][1]
            if backref_name:
                dct[backref_name] = self
            return child_class(dct)
        else:
            return Resource(dct)

    def _is_passthrough_type(self, entity):
        return (entity is None or
                isinstance(entity,
                           (six.integer_types, float,
                            datetime.datetime, six.string_types)))

    # Conversion to dict

    def _to_dict(self, backref):
        dct = dict()
        for refname, entity in six.iteritems(self):
            if refname != backref and refname not in self._filter_fields:
                childs_backref = None
                if refname in self._children:
                    childs_backref = self._children[refname][1]
                dct[refname] = self._entity_to_dict(entity, childs_backref)
                sanitize = self._sanitize_fields.get(refname)
                if sanitize is not None:
                    dct[refname] = sanitize(self, dct[refname])
        return dct

    def _entity_to_dict(self, entity, childs_backref):
        if isinstance(entity, Resource):
            return entity._to_dict(childs_backref)
        elif isinstance(entity, list):
            return self._list_to_dict(entity, childs_backref)
        elif entity is not None:
            return entity

    def _list_to_dict(self, lst, childs_backref):
        return [self._entity_to_dict(entity, childs_backref) for entity in lst]

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, *args):
        raise ex.FrozenClassError(self)


class NodeGroupTemplateResource(Resource, objects.NodeGroupTemplate):
    _resource_name = 'node_group_template'


class InstanceResource(Resource, objects.Instance):
    _filter_fields = ['tenant_id', 'node_group_id', "volumes"]

    @property
    def cluster_id(self):
        return self.node_group.cluster_id

    @property
    def cluster(self):
        return self.node_group.cluster


class NodeGroupResource(Resource, objects.NodeGroup):
    _children = {
        'instances': (InstanceResource, 'node_group'),
        'node_group_template': (NodeGroupTemplateResource, None)
    }

    _filter_fields = ['tenant_id', 'cluster_id', 'cluster_template_id',
                      'image_username', 'open_ports']


class ClusterTemplateResource(Resource, objects.ClusterTemplate):
    _resource_name = 'cluster_template'

    _children = {
        'node_groups': (NodeGroupResource, 'cluster_template')
    }


class ClusterHealthCheckResource(Resource, objects.ClusterHealthCheck):
    _resource_name = 'cluster_health_check'


class ClusterVerificationResource(Resource, objects.ClusterVerification):
    _resource_name = 'cluster_verification'
    _children = {
        'checks': (ClusterHealthCheckResource, 'verification')
    }


class ClusterResource(Resource, objects.Cluster):

    def sanitize_cluster_configs(self, cluster_configs):
        if 'proxy_configs' in cluster_configs:
            del cluster_configs['proxy_configs']
        return cluster_configs

    _resource_name = 'cluster'

    _children = {
        'node_groups': (NodeGroupResource, 'cluster'),
        'cluster_template': (ClusterTemplateResource, None),
        'verification': (ClusterVerificationResource, 'cluster')
    }

    _filter_fields = ['management_private_key', 'extra', 'rollback_info',
                      'sahara_info']
    _sanitize_fields = {'cluster_configs': sanitize_cluster_configs}


class ImageResource(Resource, objects.Image):

    _resource_name = 'image'

    @property
    def dict(self):
        return self.to_dict()

    @property
    def wrapped_dict(self):
        return {'image': self.dict}

    def _sanitize_image_properties(self, image_props):
        if 'links' in image_props:
            del image_props['links']
        return image_props

    _sanitize_fields = {'links': _sanitize_image_properties}


# EDP Resources

class DataSource(Resource, objects.DataSource):
    _resource_name = "data_source"
    _filter_fields = ['credentials']


class JobExecution(Resource, objects.JobExecution):

    def sanitize_job_configs(self, job_configs):
        if 'configs' in job_configs:
            configs = job_configs['configs']
            if swift_helper.HADOOP_SWIFT_USERNAME in configs:
                configs[swift_helper.HADOOP_SWIFT_USERNAME] = ""
            if swift_helper.HADOOP_SWIFT_PASSWORD in configs:
                configs[swift_helper.HADOOP_SWIFT_PASSWORD] = ""
            if s3_common.S3_ACCESS_KEY_CONFIG in configs:
                configs[s3_common.S3_ACCESS_KEY_CONFIG] = ""
            if s3_common.S3_SECRET_KEY_CONFIG in configs:
                configs[s3_common.S3_SECRET_KEY_CONFIG] = ""

        if 'trusts' in job_configs:
            del job_configs['trusts']
        if 'proxy_configs' in job_configs:
            del job_configs['proxy_configs']
        return job_configs

    def sanitize_info(self, info):
        if 'actions' in info:
            for d in info['actions']:
                if 'conf' in d:
                    del d['conf']
        return info

    _resource_name = "job_execution"
    _filter_fields = ['extra']
    _sanitize_fields = {'job_configs': sanitize_job_configs,
                        'info': sanitize_info}
    # TODO(egafford): Sanitize interface ("secret" bool field on job args?)


class JobBinary(Resource, objects.JobBinary):
    _resource_name = "job_binary"
    _filter_fields = ['extra']


class JobBinaryInternal(Resource, objects.JobBinaryInternal):
    _resource_name = "job_binary_internal"


class Job(Resource, objects.Job):
    _resource_name = "job"
    _children = {
        'mains': (JobBinary, None),
        'libs': (JobBinary, None)
    }
