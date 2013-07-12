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

import setuptools

from savanna.openstack.common import setup as common_setup

requires = common_setup.parse_requirements()
depend_links = common_setup.parse_dependency_links()
project = 'savanna'

setuptools.setup(
    name=project,
    version=common_setup.get_version(project, '0.2'),
    description='Savanna project',
    author='OpenStack',
    author_email='openstack-dev@lists.openstack.org',
    url='https://savanna.readthedocs.org',
    classifiers=[
        'Environment :: OpenStack',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    license='Apache Software License',
    cmdclass=common_setup.get_cmdclass(),
    packages=setuptools.find_packages(exclude=['bin']),
    package_data={'savanna': [
        'plugins/vanilla/resources/*.xml',
        'swift/resources/*.xml',
        'tests/unit/resources/*.xml'
    ]},
    install_requires=requires,
    dependency_links=depend_links,
    setup_requires=['setuptools-git>=0.4'],
    include_package_data=True,
    test_suite='nose.collector',
    scripts=[
        'bin/savanna-api',
        'bin/savanna-db-manage',
    ],
    py_modules=[],
    data_files=[
        ('share/savanna',
         [
             'etc/savanna/savanna.conf.sample',
             'etc/savanna/savanna.conf.sample-full',
         ]),
    ],
)
