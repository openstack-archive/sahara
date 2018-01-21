# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import argparse
import sys

from oslo_serialization import jsonutils as json

_GROUP_VERSION_SEPARATOR = ","
_ALL_GROUP_VERSION = "all"


def _build_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("packages", help="path to the packages.json")
    parser.add_argument("spec", help="path to the spec.json")
    parser.add_argument("--separator", default=":",
                        help="separator between package name"
                             " and version in output")

    return parser


def _load_json(path):
    with open(path) as json_file:
        return json.load(json_file)


def _version_matches(version, group_version):
    for gv in group_version.split(_GROUP_VERSION_SEPARATOR):
        if version.startswith(gv):
            return True

    return False


def _get_packages(version, group_spec):
    for group_version in group_spec:
        if _version_matches(version, group_version):
            return group_spec[group_version]

    return group_spec[_ALL_GROUP_VERSION]


def _get_package_versions(spec, package_groups):
    return [(package, version)
            for pg_name, versions in spec.items()
            for version in versions
            for package in _get_packages(version, package_groups[pg_name])]


parser = _build_parser()


def main(args=None):
    args = parser.parse_args(args or sys.argv[1:])

    spec = _load_json(args.spec)
    package_groups = _load_json(args.packages)
    separator = args.separator

    package_versions = _get_package_versions(spec, package_groups)
    package_format = "%s" + separator + "%s\n"
    package_versions = map(lambda pv: package_format % pv, package_versions)

    sys.stdout.writelines(package_versions)


if __name__ == "__main__":
    main()
