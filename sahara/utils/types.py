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

from sahara import exceptions as ex


class FrozenList(list):
    def append(self, p_object):
        raise ex.FrozenClassError(self)

    def extend(self, iterable):
        raise ex.FrozenClassError(self)

    def insert(self, index, p_object):
        raise ex.FrozenClassError(self)

    def pop(self, index=None):
        raise ex.FrozenClassError(self)

    def remove(self, value):
        raise ex.FrozenClassError(self)

    def reverse(self):
        raise ex.FrozenClassError(self)

    def sort(self, cmp=None, key=None, reverse=False):
        raise ex.FrozenClassError(self)

    def __add__(self, y):
        raise ex.FrozenClassError(self)

    def __delitem__(self, y):
        raise ex.FrozenClassError(self)

    def __delslice__(self, i, j):
        raise ex.FrozenClassError(self)

    def __iadd__(self, y):
        raise ex.FrozenClassError(self)

    def __imul__(self, y):
        raise ex.FrozenClassError(self)

    def __setitem__(self, i, y):
        raise ex.FrozenClassError(self)

    def __setslice__(self, i, j, y):
        raise ex.FrozenClassError(self)


class FrozenDict(dict):
    def clear(self):
        raise ex.FrozenClassError(self)

    def pop(self, k, d=None, force=False):
        if force:
            return super(FrozenDict, self).pop(k, d)
        raise ex.FrozenClassError(self)

    def popitem(self):
        raise ex.FrozenClassError(self)

    def setdefault(self, k, d=None):
        raise ex.FrozenClassError(self)

    def update(self, E=None, **F):
        raise ex.FrozenClassError(self)

    def __delitem__(self, y):
        raise ex.FrozenClassError(self)

    def __setitem__(self, i, y):
        raise ex.FrozenClassError(self)


def is_int(s):
    try:
        int(s)
        return True
    except Exception:
        return False


def transform_to_num(s):
    # s can be a string or non-string.
    try:
        return int(str(s))
    except ValueError:
        try:
            return float(str(s))
        except ValueError:
            return s


class Page(list):
    def __init__(self, l, prev=None, next=None):
        super(Page, self).__init__(l)
        self.prev = prev
        self.next = next
