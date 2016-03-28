# Copyright (c) 2016 Red Hat, Inc.
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

from sahara import conductor as c
from sahara import context


conductor = c.API


def get_data_sources(**kwargs):
    return conductor.data_source_get_all(context.ctx(),
                                         regex_search=True, **kwargs)


def get_data_source(id):
    return conductor.data_source_get(context.ctx(), id)


def delete_data_source(id):
    conductor.data_source_destroy(context.ctx(), id)


def register_data_source(values):
    return conductor.data_source_create(context.ctx(), values)


def data_source_update(id, values):
    return conductor.data_source_update(context.ctx(), id, values)
