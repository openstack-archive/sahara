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

import six


class BaseResource(object):
    __resource_name__ = 'base'
    __filter_cols__ = []

    @property
    def dict(self):
        return self.to_dict()

    @property
    def wrapped_dict(self):
        return {self.__resource_name__: self.dict}

    @property
    def __all_filter_cols__(self):
        cls = self.__class__
        if not hasattr(cls, '__mro_filter_cols__'):
            filter_cols = []
            for base_cls in inspect.getmro(cls):
                filter_cols += getattr(base_cls, '__filter_cols__', [])
            cls.__mro_filter_cols__ = set(filter_cols)
        return cls.__mro_filter_cols__

    def _filter_field(self, k):
        return k == '_sa_instance_state' or k in self.__all_filter_cols__

    def to_dict(self):
        dictionary = self.__dict__.copy()
        return {k: v for k, v in six.iteritems(dictionary)
                if not self._filter_field(k)}

    def as_resource(self):
        return Resource(self.__resource_name__, self.to_dict())


class Resource(BaseResource):
    def __init__(self, _name, _info):
        self._name = _name
        self.__resource_name__ = _name
        self._info = _info

    def __getattr__(self, k):
        if k not in self.__dict__:
            return self._info.get(k)
        return self.__dict__[k]

    def __repr__(self):
        return '<%s %s>' % (self._name, self._info)

    def __eq__(self, other):
        return self._name == other._name and self._info == other._info

    def to_dict(self):
        return self._info.copy()
