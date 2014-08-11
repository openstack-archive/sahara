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


class Wrapper(object):
    WRAPPED = '__wrapped__'

    def __init__(self, wrapped, **kargs):
        object.__getattribute__(self, '__dict__').update(kargs)
        object.__setattr__(self, Wrapper.WRAPPED, wrapped)

    def __getattribute__(self, name):
        wrapped = object.__getattribute__(self, Wrapper.WRAPPED)
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return object.__getattribute__(wrapped, name)
