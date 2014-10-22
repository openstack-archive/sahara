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

import collections as cl
import copy as cp
import functools as ft
import itertools as it

import six

import sahara.plugins.mapr.util.func_utils as fu


def append_to_key(dict_0, dict_1):
    return dict((k0, dict((k1, dict_1[k1]) for k1 in keys_1 if k1 in dict_1))
                for k0, keys_1 in six.iteritems(dict_0))


def iterable_to_values_pair_dict_reducer(key_0, key_1):
    def reducer(previous, iterable, mapper):
        previous.update(dict(map(mapper, iterable)))
        return previous
    return ft.partial(reducer, mapper=fu.get_values_pair_function(key_0,
                                                                  key_1))


def flatten_to_list_reducer():
    def reducer(previous, iterable):
        previous.extend(list(iterable))
        return previous
    return reducer


def map_by_field_value(iterable, key, factory=list,
                       iterator_reducer=flatten_to_list_reducer()):
    def reducer(mapping, current):
        mapping[current[0]] = iterator_reducer(
            mapping[current[0]], iter(current[1]))
        return mapping
    groups = it.groupby(iterable, fu.get_value_function(key))
    return reduce(reducer, groups, cl.defaultdict(factory))


def map_by_fields_values(iterable, fields, factory=list,
                         reducer=flatten_to_list_reducer()):
    if len(fields) == 1:
        return map_by_field_value(iterable, fields[0], factory, reducer)
    else:
        return dict((k, map_by_fields_values(v, fields[1:], factory, reducer))
                    for k, v in six.iteritems(map_by_field_value(
                        iterable, fields[0])))


def get_keys_by_value_type(mapping, value_type):
    return filter(lambda k: isinstance(mapping[k], value_type), mapping)


def deep_update(dict_0, dict_1, copy=True):
    result = cp.deepcopy(dict_0) if copy else dict_0
    dict_valued_keys_0 = set(get_keys_by_value_type(dict_0, dict))
    dict_valued_keys_1 = set(get_keys_by_value_type(dict_1, dict))
    common_keys = dict_valued_keys_0 & dict_valued_keys_1
    if not common_keys:
        result.update(dict_1)
    else:
        for k1, v1 in six.iteritems(dict_1):
            result[k1] = deep_update(
                dict_0[k1], v1) if k1 in common_keys else v1
    return result


def get_keys_by_value(mapping, value):
    return [k for k, v in six.iteritems(mapping) if v == value]

# TODO(aosadchiy): find more appropriate name


def get_keys_by_value_2(mapping, value):
    return [k for k, v in six.iteritems(mapping) if value in v]


def iterable_to_values_list_reducer(key):
    def reducer(previous, iterable, mapper):
        previous.extend(map(mapper, iterable))
        return previous
    return ft.partial(reducer, mapper=fu.get_value_function(key))


def select(fields, iterable, predicate=fu.true_predicate):
    return map(fu.extract_fields_function(fields), filter(predicate, iterable))

has_no_dict_values_predicate = lambda n: not get_keys_by_value_type(n, dict)


def list_of_vp_dicts_function(key_0, key_1):
    def transformer(item, key_0, key_1):
        return [fu.values_pair_to_dict_function(key_0, key_1)(i)
                for i in six.iteritems(item)]
    return ft.partial(transformer, key_0=key_0, key_1=key_1)


def flattened_dict(mapping, keys, is_terminal=has_no_dict_values_predicate,
                   transform=None):
    if not transform:
        transform = list_of_vp_dicts_function(*keys[-2:])
    if is_terminal(mapping):
        return list(transform(mapping))
    else:
        temp = [it.imap(fu.append_field_function(keys[0], key),
                        flattened_dict(value, keys[1:],
                                       is_terminal, transform))
                for key, value in six.iteritems(mapping)]
    return list(it.chain(*temp))
