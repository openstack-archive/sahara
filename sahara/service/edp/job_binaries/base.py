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

import six

from sahara import exceptions as ex
from sahara.plugins import base as plugins_base


@six.add_metaclass(abc.ABCMeta)
class JobBinaryType(object):
    @plugins_base.required_with_default
    def prepare_cluster(self, job_binary, **kwargs):
        """Makes a cluster ready to use this job binary

        Different implementations for each job binary type for Manila it will
        be mount the share, for Swift verify credentials, and so on

        :param job_binary: The object handle to a job binary
        :returns: None
        """
        pass

    @plugins_base.required
    def copy_binary_to_cluster(self, job_binary, **kwargs):
        """Get the path for the binary in a cluster

        If necessary, pull binary data from the binary store, and copy that
        data to a useful path on the cluster. Then returns a valid
        FS path for the job binary in the cluster

        :param job_binary: The object handle to a job binary

        :returns: String representing the local path
        """

        # TODO(mariannelm): currently for the job binaries it's true
        # that the raw data must be available at a FS path in the cluster, but
        # for most of the job binary types there's no need to keep this data
        # in the cluster after the job is done, so it would be a good thing to
        # have a method responsible for removing the job binary raw data
        # after the end of the job
        return None

    @plugins_base.required_with_default
    def validate(self, data, **kwargs):
        """Method that validate the data passed through the API

        This method will be executed during the job binary creation and
        update

        :raise: If data is invalid, InvalidDataException
        """
        pass

    @plugins_base.optional
    def _validate_url(self, url):
        """Auxiliary method used by the validate method"""
        pass

    @plugins_base.required_with_default
    def validate_job_location_format(self, entry):
        """Checks whether or not the API entry is valid

        :param entry: String that represents a job binary url

        :returns: True if this entry is valid, False otherwhise

        """
        return True

    @plugins_base.required_with_default
    def get_raw_data(self, job_binary, **kwargs):
        """Get the raw binary

        Used only by the API, if the type doesn't support this operation it
        should raise NotImplementedException

        :param job_binary: The object handle to a job binary

        :returns: Raw binary

        """
        raise ex.NotImplementedException()

    @plugins_base.optional
    def _generate_valid_path(self, job_binary):
        """Generates a valid FS path for the binary be placed"""
        return '/tmp/' + job_binary.name
