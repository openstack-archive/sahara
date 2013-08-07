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

"""The Conductor can fetch only values represented by JSON. That
limitation comes from Oslo RPC implementation.

This module provides means to wrap a fetched value, always
dictionary, into an immutable Resource object. A descendant of
Resource class might provide back references to parent objects
and helper methods
"""

import six

from savanna.utils import types


def wrap(resource_class):
    """A decorator which wraps dict returned by a given function into
    a Resource
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

    _children = {}

    def __init__(self, dct):
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
        if refname in self._children:
            dct = dict(dct)
            child_class = self._children[refname][0]
            backref_name = self._children[refname][1]
            dct[backref_name] = self
            return child_class(dct)
        else:
            return Resource(dct)

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, *args):
        raise types.FrozenClassError(self)


class InstanceResource(Resource):
    pass


class NodeGroupResource(Resource):
    _children = {'instances': (InstanceResource, 'node_group')}


class ClusterResource(Resource):
    _children = {'node_groups': (NodeGroupResource, 'cluster')}
