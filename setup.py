import setuptools

from savanna.openstack.common import setup as common_setup

requires = common_setup.parse_requirements()
depend_links = common_setup.parse_dependency_links()
project = 'savanna'

setuptools.setup(
    name=project,
    version=common_setup.get_version(project, '0.1'),
    description='Savanna project',
    author='Mirantis Inc.',
    author_email='savanna-team@mirantis.com',
    url='http://savanna.mirantis.com',
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
    cmdclass=common_setup.get_cmdclass(),
    packages=setuptools.find_packages(exclude=['bin']),
    package_data={'savanna': ['resources/*.template']},
    install_requires=requires,
    dependency_links=depend_links,
    include_package_data=True,
    test_suite='nose.collector',
    setup_requires=['setuptools_git>=0.4'],
    scripts=[
        'bin/savanna-api',
        'bin/savanna-manage',
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
