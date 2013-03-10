import setuptools

from eho.openstack.common import setup as common_setup

requires = common_setup.parse_requirements()
depend_links = common_setup.parse_dependency_links()
project = 'eho'

setuptools.setup(
    name=project,
    version=common_setup.get_version(project, '0.1'),
    description='elastic hadoop on openstack',
    author='Mirantis Inc.',
    author_email='elastic-hadoop-all@mirantis.com',
    url='http://eho.mirantis.com',
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
    install_requires=requires,
    dependency_links=depend_links,
    include_package_data=True,
    test_suite='nose.collector',
    setup_requires=['setuptools_git>=0.4'],
    scripts=['bin/eho-api'],
    py_modules=[]
)
