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

from oslo_config import cfg
import six.moves.urllib.parse as urlparse

from sahara import conductor as c
from sahara import context
import sahara.exceptions as ex
from sahara.i18n import _
import sahara.service.validations.edp.base as b
from sahara.swift import utils as su

CONF = cfg.CONF


def check_data_source_create(data, **kwargs):
    b.check_data_source_unique_name(data['name'])

    if "swift" == data["type"]:
        _check_swift_data_source_create(data)

    if "hdfs" == data["type"]:
        _check_hdfs_data_source_create(data)

    if "maprfs" == data["type"]:
        _check_maprfs_data_source_create(data)


def _check_swift_data_source_create(data):
    if len(data['url']) == 0:
        raise ex.InvalidDataException(_("Swift url must not be empty"))
    url = urlparse.urlparse(data['url'])
    if url.scheme != "swift":
        raise ex.InvalidDataException(_("URL scheme must be 'swift'"))

    # The swift url suffix does not have to be included in the netloc.
    # However, if the swift suffix indicator is part of the netloc then
    # we require the right suffix.
    # Additionally, the path must be more than '/'
    if (su.SWIFT_URL_SUFFIX_START in url.netloc and not url.netloc.endswith(
            su.SWIFT_URL_SUFFIX)) or len(url.path) <= 1:
        raise ex.InvalidDataException(
            _("URL must be of the form swift://container%s/object")
            % su.SWIFT_URL_SUFFIX)

    if not CONF.use_domain_for_proxy_users and "credentials" not in data:
        raise ex.InvalidCredentials(_("No credentials provided for Swift"))
    if not CONF.use_domain_for_proxy_users and (
            "user" not in data["credentials"]):
        raise ex.InvalidCredentials(
            _("User is not provided in credentials for Swift"))
    if not CONF.use_domain_for_proxy_users and (
            "password" not in data["credentials"]):
        raise ex.InvalidCredentials(
            _("Password is not provided in credentials for Swift"))


def _check_hdfs_data_source_create(data):
    if len(data['url']) == 0:
        raise ex.InvalidDataException(_("HDFS url must not be empty"))
    url = urlparse.urlparse(data['url'])
    if url.scheme:
        if url.scheme != "hdfs":
            raise ex.InvalidDataException(_("URL scheme must be 'hdfs'"))
        if not url.hostname:
            raise ex.InvalidDataException(
                _("HDFS url is incorrect, cannot determine a hostname"))


def _check_maprfs_data_source_create(data):
    if len(data['url']) == 0:
        raise ex.InvalidDataException(_("MapR FS url must not be empty"))
    url = urlparse.urlparse(data['url'])
    if url.scheme:
        if url.scheme != "maprfs":
            raise ex.InvalidDataException(_("URL scheme must be 'maprfs'"))


def check_data_source_update(data, **kwargs):
    ctx = context.ctx()
    jobs = c.API.job_execution_get_all(ctx)
    pending_jobs = [job for job in jobs if job.info.status == "PENDING"]
    for job in pending_jobs:
        if kwargs["data_source_id"] in job.data_source_urls:
            raise ex.UpdateFailedException(
                _("DataSource is used in a "
                  "PENDING Job and can not be updated."))
