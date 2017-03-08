# Copyright (c) 2014 Red Hat Inc.
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


from oslo_utils import uuidutils

from sahara.utils import files

# job execution status
JOB_STATUS_DONEWITHERROR = 'DONEWITHERROR'
JOB_STATUS_FAILED = 'FAILED'
JOB_STATUS_KILLED = 'KILLED'
JOB_STATUS_PENDING = 'PENDING'
JOB_STATUS_READYTORUN = 'READYTORUN'
JOB_STATUS_RUNNING = 'RUNNING'
JOB_STATUS_SUCCEEDED = 'SUCCEEDED'
JOB_STATUS_TOBEKILLED = 'TOBEKILLED'
JOB_STATUS_TOBESUSPENDED = 'TOBESUSPENDED'
JOB_STATUS_PREP = 'PREP'
JOB_STATUS_PREPSUSPENDED = 'PREPSUSPENDED'
JOB_STATUS_SUSPENDED = 'SUSPENDED'
JOB_STATUS_SUSPEND_FAILED = 'SUSPENDFAILED'
# statuses for suspended jobs
JOB_STATUSES_SUSPENDIBLE = [
    JOB_STATUS_PREP,
    JOB_STATUS_RUNNING
]
# statuses for terminated jobs
JOB_STATUSES_TERMINATED = [
    JOB_STATUS_DONEWITHERROR,
    JOB_STATUS_FAILED,
    JOB_STATUS_KILLED,
    JOB_STATUS_SUCCEEDED,
    JOB_STATUS_SUSPEND_FAILED
]
# job type separator character
JOB_TYPE_SEP = '.'
# job sub types available
JOB_SUBTYPE_STREAMING = 'Streaming'
JOB_SUBTYPE_NONE = ''
# job types available
JOB_TYPE_HIVE = 'Hive'
JOB_TYPE_JAVA = 'Java'
JOB_TYPE_MAPREDUCE = 'MapReduce'
JOB_TYPE_SPARK = 'Spark'
JOB_TYPE_STORM = 'Storm'
JOB_TYPE_PYLEUS = 'Storm.Pyleus'
JOB_TYPE_MAPREDUCE_STREAMING = (JOB_TYPE_MAPREDUCE + JOB_TYPE_SEP +
                                JOB_SUBTYPE_STREAMING)
JOB_TYPE_PIG = 'Pig'
JOB_TYPE_SHELL = 'Shell'

# job type groupings available
JOB_TYPES_ALL = [
    JOB_TYPE_HIVE,
    JOB_TYPE_JAVA,
    JOB_TYPE_MAPREDUCE,
    JOB_TYPE_MAPREDUCE_STREAMING,
    JOB_TYPE_PIG,
    JOB_TYPE_SHELL,
    JOB_TYPE_SPARK,
    JOB_TYPE_STORM,
    JOB_TYPE_PYLEUS
]

JOB_TYPES_ACCEPTABLE_CONFIGS = {
    JOB_TYPE_HIVE: {"configs", "params"},
    JOB_TYPE_PIG: {"configs", "params", "args"},
    JOB_TYPE_MAPREDUCE: {"configs"},
    JOB_TYPE_MAPREDUCE_STREAMING: {"configs"},
    JOB_TYPE_JAVA: {"configs", "args"},
    JOB_TYPE_SHELL: {"configs", "params", "args"},
    JOB_TYPE_SPARK: {"configs", "args"},
    JOB_TYPE_STORM: {"args"},
    JOB_TYPE_PYLEUS: {}
}

# job actions
JOB_ACTION_SUSPEND = 'suspend'
JOB_ACTION_CANCEL = 'cancel'

JOB_ACTION_TYPES_ACCEPTABLE = [
    JOB_ACTION_SUSPEND,
    JOB_ACTION_CANCEL
]

ADAPT_FOR_OOZIE = 'edp.java.adapt_for_oozie'
SPARK_DRIVER_CLASSPATH = 'edp.spark.driver.classpath'
ADAPT_SPARK_FOR_SWIFT = 'edp.spark.adapt_for_swift'


def split_job_type(job_type):
    '''Split a job type string into a type and subtype

    The split is done on the first '.'.  A subtype will
    always be returned, even if it is empty.
    '''
    type_info = job_type.split(JOB_TYPE_SEP, 1)
    if len(type_info) == 1:
        type_info.append('')
    return type_info


def compare_job_type(job_type, *args, **kwargs):
    '''Compare a job type against a list of job types

    :param job_type: The job type being compared
    :param *args: A list of types to compare against
    :param strict: Passed as a keyword arg. Default is False.
                   If strict is False, job_type will be compared
                   with and without its subtype indicator.
    :returns: True if job_type is present in the list, False otherwise
    '''
    strict = kwargs.get('strict', False)
    res = job_type in args
    if res or strict or JOB_TYPE_SEP not in job_type:
        return res

    jtype, jsubtype = split_job_type(job_type)
    return jtype in args


def get_hive_shared_conf_path(hdfs_user):
    return "/user/%s/conf/hive-site.xml" % hdfs_user


def is_adapt_for_oozie_enabled(configs):
    return configs.get(ADAPT_FOR_OOZIE, False)


def is_adapt_spark_for_swift_enabled(configs):
    return configs.get(ADAPT_SPARK_FOR_SWIFT, False)


def spark_driver_classpath(configs):
    # Return None in case when you need to use default value
    return configs.get(SPARK_DRIVER_CLASSPATH)


def get_builtin_binaries(job, configs):
    if job.type == JOB_TYPE_JAVA:
        if is_adapt_for_oozie_enabled(configs):
            path = 'service/edp/resources/edp-main-wrapper.jar'
            name = 'builtin-%s.jar' % uuidutils.generate_uuid()
            return [{'raw': files.get_file_binary(path),
                     'name': name}]
    return []
