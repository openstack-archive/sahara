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

import _io
import pickle  # nosec
import sys
import traceback

from oslo_utils import reflection


def main():
    # NOTE(dmitryme): since we do not read stderr in the main process,
    # we need to flush it somewhere, otherwise both processes might
    # hang because of i/o buffer overflow.
    with open('/dev/null', 'w') as sys.stderr:
        while True:
            result = dict()

            try:
                # TODO(elmiko) these pickle usages should be
                # reinvestigated to determine a more secure manner to
                # deploy remote commands.
                if isinstance(sys.stdin, _io.TextIOWrapper):
                    func = pickle.load(sys.stdin.buffer)  # nosec
                    args = pickle.load(sys.stdin.buffer)  # nosec
                    kwargs = pickle.load(sys.stdin.buffer)  # nosec
                else:
                    func = pickle.load(sys.stdin)  # nosec
                    args = pickle.load(sys.stdin)  # nosec
                    kwargs = pickle.load(sys.stdin)  # nosec

                result['output'] = func(*args, **kwargs)
            except BaseException as e:
                cls_name = reflection.get_class_name(e, fully_qualified=False)
                result['exception'] = cls_name + ': ' + str(e)
                result['traceback'] = traceback.format_exc()

            if isinstance(sys.stdin, _io.TextIOWrapper):
                pickle.dump(result, sys.stdout.buffer, protocol=2)  # nosec
            else:
                pickle.dump(result, sys.stdout, protocol=2)  # nosec
            sys.stdout.flush()
