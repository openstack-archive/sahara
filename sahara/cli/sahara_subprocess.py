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

import pickle
import sys
import traceback


def main():
    # NOTE(dmitryme): since we do not read stderr in the main process,
    # we need to flush it somewhere, otherwise both processes might
    # hang because of i/o buffer overflow.
    with open('/dev/null', 'w') as sys.stderr:
        while True:
            result = dict()

            try:
                func = pickle.load(sys.stdin)
                args = pickle.load(sys.stdin)
                kwargs = pickle.load(sys.stdin)

                result['output'] = func(*args, **kwargs)
            except BaseException as e:
                result['exception'] = e.__class__.__name__ + ': ' + str(e)
                result['traceback'] = traceback.format_exc()

            pickle.dump(result, sys.stdout)
            sys.stdout.flush()
