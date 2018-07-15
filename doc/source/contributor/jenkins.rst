Continuous Integration with Jenkins
===================================

Each change made to Sahara core code is tested with unit and integration tests
and style checks using flake8.

Unit tests and style checks are performed on public `OpenStack Zuul
<http://zuul.openstack.org/>`_ instance.

Unit tests are checked using python 2.7.

The result of those checks and Unit tests are represented as a vote of +1 or
-1 in the *Verify* column in code reviews from the *Jenkins* user.

Integration tests check CRUD operations for the Image Registry, Templates, and
Clusters. Also a test job is launched on a created Cluster to verify Hadoop
work.

All integration tests are launched by `Jenkins
<https://sahara.mirantis.com/jenkins/>`_ on the internal Mirantis OpenStack
Lab.

Jenkins keeps a pool of VMs to run tests in parallel. Even with the pool of VMs
integration testing may take a while.

Jenkins is controlled for the most part by Zuul which determines what jobs are
run when.

Zuul status is available at this address: `Zuul Status
<https://sahara.mirantis.com/zuul>`_.

For more information see: `Sahara Hadoop Cluster CI
<https://wiki.openstack.org/wiki/Sahara/SaharaCI>`_.

The integration tests result is represented as a vote of +1 or -1 in the
*Verify* column in a code review from the *Sahara Hadoop Cluster CI* user.

You can put *sahara-ci-recheck* in comment, if you want to recheck sahara-ci
jobs. Also, you can put *recheck* in comment, if you want to recheck both
Jenkins and sahara-ci jobs. Finally, you can put *reverify* in a comment, if
you only want to recheck Jenkins jobs.
