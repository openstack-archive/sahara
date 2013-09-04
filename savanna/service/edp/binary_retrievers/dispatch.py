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

from savanna import context
from savanna.service.edp.binary_retrievers import internal_swift as i_swift
from savanna.service.edp.binary_retrievers import savanna_db as db


def get_raw_binary(job_binary):
    url = job_binary.url
    if url.startswith("savanna-db://"):
        return db.get_raw_data(context.ctx(), job_binary)
    if url.startswith("internal-swift://"):
        return i_swift.get_raw_data(context.ctx(), job_binary)
