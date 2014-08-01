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

from sahara.i18n import _


class FrozenList(list):
    def append(self, p_object):
        raise FrozenClassError(self)

    def extend(self, iterable):
        raise FrozenClassError(self)

    def insert(self, index, p_object):
        raise FrozenClassError(self)

    def pop(self, index=None):
        raise FrozenClassError(self)

    def remove(self, value):
        raise FrozenClassError(self)

    def reverse(self):
        raise FrozenClassError(self)

    def sort(self, cmp=None, key=None, reverse=False):
        raise FrozenClassError(self)

    def __add__(self, y):
        raise FrozenClassError(self)

    def __delitem__(self, y):
        raise FrozenClassError(self)

    def __delslice__(self, i, j):
        raise FrozenClassError(self)

    def __iadd__(self, y):
        raise FrozenClassError(self)

    def __imul__(self, y):
        raise FrozenClassError(self)

    def __setitem__(self, i, y):
        raise FrozenClassError(self)

    def __setslice__(self, i, j, y):
        raise FrozenClassError(self)


class FrozenDict(dict):
    def clear(self):
        raise FrozenClassError(self)

    def pop(self, k, d=None):
        raise FrozenClassError(self)

    def popitem(self):
        raise FrozenClassError(self)

    def setdefault(self, k, d=None):
        raise FrozenClassError(self)

    def update(self, E=None, **F):
        raise FrozenClassError(self)

    def __delitem__(self, y):
        raise FrozenClassError(self)

    def __setitem__(self, i, y):
        raise FrozenClassError(self)


class FrozenClassError(Exception):
    def __init__(self, instance):
        self.message = _("Class %s is immutable!") % type(instance).__name__


def is_int(s):
    try:
        int(s)
        return True
    except Exception:
        return False
