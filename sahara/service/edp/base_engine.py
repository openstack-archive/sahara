# Copyright (c) 2014 OpenStack Foundation
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

import abc

import six

from sahara import conductor as c

conductor = c.API


def optional(fun):
    fun.__not_implemented__ = True
    return fun


@six.add_metaclass(abc.ABCMeta)
class JobEngine(object):
    @abc.abstractmethod
    def cancel_job(self, job_execution):
        pass

    @abc.abstractmethod
    def get_job_status(self, job_execution):
        pass

    @abc.abstractmethod
    def run_job(self, job_execution):
        pass

    @abc.abstractmethod
    def run_scheduled_job(self, job_execution):
        pass

    @abc.abstractmethod
    def validate_job_execution(self, cluster, job, data):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_possible_job_config(job_type):
        return None

    @staticmethod
    @abc.abstractmethod
    def get_supported_job_types():
        return None

    @optional
    def suspend_job(self, job_execution):
        pass

    def does_engine_implement(self, fun_name):
        fun = getattr(self, fun_name)
        if not (fun and callable(fun)):
            return False
        return not hasattr(fun, '__not_implemented__')
