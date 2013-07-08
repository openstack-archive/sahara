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

# Stolen from the hacking lib's trunk
# TODO(slukjanov): remove it when it'll be released with hacking

import logging
import re

# Don't need this for testing
logging.disable('LOG')


def _check_for_exact_apache(start, lines):
    """Check for the Apache 2.0 license header.

    We strip all the newlines and extra spaces so this license string
    should work regardless of indentation in the file.
    """
    APACHE2 = """
Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License."""

    # out of all the formatting I've seen, a 12 line version seems to be the
    # longest in the source tree. So just take the 12 lines starting with where
    # the Apache starting words were found, strip all the '#' and collapse the
    # spaces.
    content = ''.join(lines[start:(start + 12)])
    content = re.sub('\#', '', content)
    content = re.sub('\s+', ' ', content)
    stripped_apache2 = re.sub('\s+', ' ', APACHE2)

    if stripped_apache2 in content:
        return True
    else:
        print ("<license>!=<apache2>:\n'%s' !=\n'%s'" %
               (stripped_apache2, content))
        return False


def _project_is_apache():
    """Determine if a project is Apache.

    Look for a key string in a set of possible license files to figure out
    if a project looks to be Apache. This is used as a precondition for
    enforcing license headers.
    """

    license_files = ["LICENSE"]
    for filename in license_files:
        try:
            with open(filename, "r") as file:
                for line in file:
                    if re.search('Apache License', line):
                        return True
        except IOError:
            pass
    return False


def hacking_has_license(physical_line, filename, lines, line_number):
    """Check for Apache 2.0 license.

    H102 license header not found
    """
    # don't work about init files for now
    # TODO(sdague): enforce license in init file if it's not empty of content
    license_found = False

    # skip files that are < 10 lines, which isn't enough for a license to fit
    # this allows us to handle empty files, as well as not fail on the Okay
    # doctests.
    if _project_is_apache() and not line_number > 1 and len(lines) > 10:
        for idx, line in enumerate(lines):
            # if it's more than 10 characters in, it's probably not in the
            # header
            if 0 < line.find('Licensed under the Apache License') < 10:
                license_found = True
        if not license_found:
            return (0, "H102: Apache 2.0 license header not found")


def hacking_has_correct_license(physical_line, filename, lines, line_number):
    """Check for Apache 2.0 license.

    H103 header does not match Apache 2.0 License notice
    """
    # don't work about init files for now
    # TODO(sdague): enforce license in init file if it's not empty of content

    # skip files that are < 10 lines, which isn't enough for a license to fit
    # this allows us to handle empty files, as well as not fail on the Okay
    # doctests.
    if _project_is_apache() and not line_number > 1 and len(lines) > 10:
        for idx, line in enumerate(lines):
            # if it's more than 10 characters in, it's probably not in the
            # header
            if (0 < line.find('Licensed under the Apache License') < 10
                    and not _check_for_exact_apache(idx, lines)):
                return (idx, "H103: Header does not match Apache 2.0 "
                             "License notice")


def hacking_python3x_print_function(logical_line):
    r"""Check that all occurrences look like print functions, not
        print operator.

    As of Python 3.x, the print operator has been removed.


    Okay: print(msg)
    Okay: print (msg)
    H233: print msg
    H233: print >>sys.stderr, "hello"
    H233: print msg,
    """

    for match in re.finditer(r"\bprint\s+[^\(]", logical_line):
        yield match.start(0), (
            "H233: Python 3.x incompatible use of print operator")


def factory(register):
    register(hacking_has_license)
    register(hacking_has_correct_license)
    register(hacking_python3x_print_function)
