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

import copy as c
import functools as ft
import itertools as it

import six


# predicates
true_predicate = lambda i: True
false_predicate = lambda i: False


def not_predicate(predicate):
    return ft.partial(lambda i, p: not p(i), p=predicate)


def and_predicate(*predicates):
    if len(predicates) == 1:
        return predicates[0]
    else:
        def predicate(item, predicates):
            for p in predicates:
                if not p(item):
                    return False
            return True
        return ft.partial(predicate, predicates=predicates)


def or_predicate(*predicates):
    if len(predicates) == 1:
        return predicates[0]
    else:
        def predicate(item, predicates):
            for p in predicates:
                if p(item):
                    return True
            return False
        return ft.partial(predicate, predicates=predicates)


def impl_predicate(p0, p1):
    return or_predicate(not_predicate(p0), p1)


def field_equals_predicate(key, value):
    return ft.partial(lambda i, k, v: i[k] == v, k=key, v=value)


def like_predicate(template, ignored=[]):
    if not template:
        return true_predicate
    elif len(template) == 1:
        k, v = six.iteritems(template).next()
        return true_predicate if k in ignored else field_equals_predicate(k, v)
    else:
        return and_predicate(*[field_equals_predicate(key, value)
                               for key, value in six.iteritems(template)
                               if key not in ignored])


def in_predicate(key, values):
    if not values:
        return false_predicate
    else:
        return or_predicate(*[field_equals_predicate(key, value)
                              for value in values])

# functions


def chain_function(*functions):
    return reduce(lambda p, c: ft.partial(lambda i, p, c: c(p(i)), p=p, c=c),
                  functions)


def copy_function():
    return lambda i: c.deepcopy(i)


def append_field_function(key, value):
    def mapper(item, key, value):
        item = c.deepcopy(item)
        item[key] = value
        return item
    return ft.partial(mapper, key=key, value=value)


def append_fields_function(fields):
    if not fields:
        return copy_function()
    elif len(fields) == 1:
        key, value = six.iteritems(fields).next()
        return append_field_function(key, value)
    else:
        return chain_function(*[append_field_function(key, value)
                                for key, value in six.iteritems(fields)])


def get_values_pair_function(key_0, key_1):
    return ft.partial(lambda i, k0, k1: (i[k0], i[k1]), k0=key_0, k1=key_1)


def get_field_function(key):
    return ft.partial(lambda i, k: (k, i[k]), k=key)


def get_fields_function(keys):
    return ft.partial(lambda i, k: [f(i) for f in [get_field_function(key)
                                                   for key in k]], k=keys)


def extract_fields_function(keys):
    return lambda i: dict(get_fields_function(keys)(i))


def get_value_function(key):
    return ft.partial(lambda i, k: i[k], k=key)


def set_default_value_function(key, value):
    def mapper(item, key, value):
        item = c.deepcopy(item)
        if key not in item:
            item[key] = value
        return item
    return ft.partial(mapper, key=key, value=value)


def set_default_values_function(fields):
    if not fields:
        return copy_function()
    elif len(fields) == 1:
        key, value = six.iteritems(fields).next()
        return set_default_value_function(key, value)
    else:
        return chain_function(*[set_default_value_function(key, value)
                                for key, value in six.iteritems(fields)])


def values_pair_to_dict_function(key_0, key_1):
    return ft.partial(lambda vp, k0, k1: {k0: vp[0], k1: vp[1]},
                      k0=key_0, k1=key_1)


def flatten(iterable):
    return it.chain.from_iterable(iterable)


def sync_execute_consumer(*consumers):
    def consumer(argument, consumers):
        for cn in consumers:
            cn(argument)
    return ft.partial(consumer, consumers=consumers)
