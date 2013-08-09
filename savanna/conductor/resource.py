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

import six

from savanna.conductor import objects
from savanna.utils import types


def wrap(resource_class):
    """A decorator which wraps dict returned by a given function into
    a Resource.
    """
    def decorator(func):
        def handle(*args, **kwargs):
            ret = func(*args, **kwargs)
            if isinstance(ret, list):
                return [resource_class(el) for el in ret]
            elif ret:
                return resource_class(ret)
            else:
                return None

        return handle
    return decorator


class Resource(types.FrozenDict):
    """Represents dictionary as an immutable object, enhancing it with
    back references and helper methods.

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

    # internal field, should not be overridden
    _backref_name = None

    def __init__(self, dct):
        self._init(dct)

    def re_init(self, dct):
        """Re-init resource with a new dictionary.

        Should be used inside conductor only for update operations.
        Preserve backreference if it exists.
        """
        dct = dict(dct)
        if self._backref_name:
            dct[self._backref_name] = self[self._backref_name]
        super(types.FrozenDict, self).clear()
        self._init(dct)

    def to_dict(self):
        """Return dictionary representing the Resource for REST API.

        On the way filter out fields which shouldn't be exposed.
        """
        return self._to_dict()

    def to_wrapped_dict(self):
        return {self._resource_name: self.to_dict()}

    # Construction

    def _init(self, dct):
        newdct = dict()
        for refname, entity in dct.iteritems():
            newdct[refname] = self._wrap_entity(refname, entity)

        super(Resource, self).__init__(newdct)

    def _wrap_entity(self, refname, entity):
        if isinstance(entity, Resource):
            # that is a back reference
            return entity
        elif isinstance(entity, list):
            return self._wrap_list(refname, entity)
        elif isinstance(entity, dict):
            return self._wrap_dict(refname, entity)
        elif (entity is None or
              isinstance(entity,
                         (six.integer_types, float, six.string_types))):
            return entity
        else:
            raise TypeError("Unsupported type: %s" % type(entity).__name__)

    def _wrap_list(self, refname, lst):
        newlst = [self._wrap_entity(refname, entity) for entity in lst]

        return types.FrozenList(newlst)

    def _wrap_dict(self, refname, dct):
        child_class = self._get_child_class(refname)
        resource = child_class(dct)
        resource._set_backref(refname, self)
        return resource

    def _get_child_class(self, refname):
        if refname in self._children:
            return self._children[refname][0]
        else:
            return Resource

    def _set_backref(self, refname, parent):
        if refname in parent._children and parent._children[refname][1]:
            backref_name = parent._children[refname][1]
            super(Resource, self).__setattr__('_backref_name', backref_name)
            super(types.FrozenDict, self).__setitem__(backref_name, parent)

    # Conversion to dict

    def _to_dict(self):
        dct = dict()
        for refname, entity in self.iteritems():
            if (refname != self._backref_name and
                    refname not in self._filter_fields):
                dct[refname] = self._entity_to_dict(entity)

        return dct

    def _entity_to_dict(self, entity):
        if isinstance(entity, Resource):
            return entity._to_dict()
        elif isinstance(entity, list):
            return self._list_to_dict(entity)
        elif entity is not None:
            return entity

    def _list_to_dict(self, lst):
        return [self._entity_to_dict(entity) for entity in lst]

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, *args):
        raise types.FrozenClassError(self)


class NodeGroupTemplateResource(Resource, objects.NodeGroupTemplate):
    _resource_name = 'node_group_template'


class InstanceResource(Resource, objects.Instance):
    _filter_fields = ['node_group_id']


class NodeGroupResource(Resource, objects.NodeGroup):
    _children = {
        'instances': (InstanceResource, 'node_group'),
        'node_group_template': (NodeGroupTemplateResource, None)
    }

    _filter_fields = ['id', 'cluster_id', 'cluster_template_id']


class ClusterTemplateResource(Resource, objects.ClusterTemplate):
    _resource_name = 'cluster_template_resource'

    _children = {
        'node_groups': (NodeGroupResource, 'cluster_template')
    }


class ClusterResource(Resource, objects.Cluster):
    _resource_name = 'cluster'

    _children = {
        'node_groups': (NodeGroupResource, 'cluster'),
        'cluster_template': (ClusterTemplateResource, None)
    }

    _filter_fields = ['private_key']
