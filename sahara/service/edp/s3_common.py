#   Copyright 2017 Massachusetts Open Cloud
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import botocore.exceptions
import botocore.session
from oslo_config import cfg
import six

import sahara.exceptions as ex
from sahara.i18n import _
from sahara.service.castellan import utils as key_manager

S3_JB_PREFIX = "s3://"
S3_ACCESS_KEY_CONFIG = "fs.s3a.access.key"
S3_SECRET_KEY_CONFIG = "fs.s3a.secret.key"
S3_ENDPOINT_CONFIG = "fs.s3a.endpoint"
S3_BUCKET_IN_PATH_CONFIG = "fs.s3a.path.style.access"
S3_SSL_CONFIG = "fs.s3a.connection.ssl.enabled"
S3_DS_CONFIGS = [S3_ACCESS_KEY_CONFIG,
                 S3_SECRET_KEY_CONFIG,
                 S3_ENDPOINT_CONFIG,
                 S3_BUCKET_IN_PATH_CONFIG,
                 S3_SSL_CONFIG]
CONF = cfg.CONF


def _get_s3_client(extra):
    sess = botocore.session.get_session()
    secretkey = key_manager.get_secret(extra['secretkey'])
    return sess.create_client(
        's3',
        # TODO(jfreud): investigate region name support
        region_name=None,
        # TODO(jfreud): investigate configurable verify
        verify=False,
        endpoint_url=extra['endpoint'],
        aws_access_key_id=extra['accesskey'],
        aws_secret_access_key=secretkey
    )


def _get_names_from_job_binary_url(url):
    parse = six.moves.urllib.parse.urlparse(url)
    return (parse.netloc + parse.path).split('/', 1)


def _get_raw_job_binary_data(job_binary, conn):
    names = _get_names_from_job_binary_url(job_binary.url)
    bucket, obj = names
    try:
        size = conn.head_object(Bucket=bucket, Key=obj)['ContentLength']
        # We have bytes, but want kibibytes:
        total_KB = size / 1024.0
        if total_KB > CONF.job_binary_max_KB:
            raise ex.DataTooBigException(
                round(total_KB, 1), CONF.job_binary_max_KB,
                _("Size of S3 object (%(size)sKB) is greater "
                  "than maximum (%(maximum)sKB)"))
        body = conn.get_object(Bucket=bucket, Key=obj)['Body'].read()
    except ex.DataTooBigException:
        raise
    except Exception:
        raise ex.S3ClientException("Couldn't get object from s3")
    return body


def _validate_job_binary_url(job_binary_url):
    if not job_binary_url.startswith(S3_JB_PREFIX):
        # Sanity check
        raise ex.BadJobBinaryException(
            _("URL for binary in S3 must start with %s") % S3_JB_PREFIX)
    names = _get_names_from_job_binary_url(job_binary_url)
    if len(names) == 1:
        # we have a bucket instead of an individual object
        raise ex.BadJobBinaryException(
            _("URL for binary in S3 must specify an object not a bucket"))


def get_raw_job_binary_data(job_binary):
    _validate_job_binary_url(job_binary.url)
    try:
        conn = _get_s3_client(job_binary.extra)
    except Exception:
        raise ex.S3ClientException("Couldn't create boto client")
    return _get_raw_job_binary_data(job_binary, conn)
