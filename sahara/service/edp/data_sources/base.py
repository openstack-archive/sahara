# Copyright (c) 2017 OpenStack Foundation
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
import random
import re
import string

import six

from sahara.plugins import base as plugins_base


@six.add_metaclass(abc.ABCMeta)
class DataSourceType(object):
    @plugins_base.required_with_default
    def construct_url(self, url, job_exec_id):
        """Resolve placeholders in the data source url

        Supported placeholders:
        * %RANDSTR(len)% - will be replaced with random string of lowercase
                           letters of length `len`
        * %JOB_EXEC_ID%  - will be replaced with the job execution ID

        :param url: String that represents an url with placeholders
        :param job_exec_id: Id of the job execution

        :returns: String that is an url without placeholders

        """
        def _randstr(match):
            random_len = int(match.group(1))
            return ''.join(random.choice(string.ascii_lowercase)
                           for _ in six.moves.range(random_len))

        url = url.replace("%JOB_EXEC_ID%", job_exec_id)
        url = re.sub(r"%RANDSTR\((\d+)\)%", _randstr, url)

        return url

    @plugins_base.required_with_default
    def prepare_cluster(self, data_source, cluster, **kwargs):
        """Makes a cluster ready to use this data source

        Different implementations for each data source, for HDFS
        will be configure the cluster, for Swift verify credentials,
        and so on

        :param data_source: The object handle to a data source
        :param cluster: The object handle to a cluster
        :returns: None
        """
        pass

    @plugins_base.required_with_default
    def get_runtime_url(self, url, cluster):
        """Get the runtime url of the data source for a cluster

        It will construct a runtime url if needed, if it's not needed
        it will use the native url as runtime url

        :param url: String that represents an already constructed url
        :param cluster: The object handle to a cluster
        :returns: String representing the runtime url
        """
        return url

    @plugins_base.required_with_default
    def get_urls(self, url, cluster, job_exec_id):
        """Get the native url and runtime url of a determined data source

        :param url: String that represents a url (constructed or not)
        :param cluster: The object handle to a cluster
        :param job_exec_id: Id of the job execution

        :returns: A tuple of the form (native_url, runtime_url), where the urls
        are Strings
        """
        native_url = self.construct_url(url, job_exec_id)
        runtime_url = self.get_runtime_url(native_url, cluster)
        return (native_url, runtime_url)

    @plugins_base.required_with_default
    def validate(self, data):
        """Method that validates the data passed through the API

        This method will be executed during the data source creation and
        update

        :raise: If data is invalid, InvalidDataException
        """
        pass

    @plugins_base.optional
    def _validate_url(self, url):
        """Auxiliary method used by the validate method"""
        pass
