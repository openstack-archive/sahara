Continuous Integration with Jenkins
===================================

Each change made to Savanna core code is tested with unit and integration tests and style checks flake8.

Unit tests and style checks are performed on public `OpenStack Jenkins <https://jenkins.openstack.org/>`_ managed by `Zuul <http://status.openstack.org/zuul/>`_.
Unit tests are checked using both python 2.6 and python 2.7.

The result of those checks and Unit tests are +1 or -1 to *Verify* column in a code review from *Jenkins* user.

Integration tests check CRUD operations for Image Registry, Templates and Clusters.
Also a test job is launched on a created Cluster to verify Hadoop work.

All integration tests are launched by `Jenkins <http://jenkins.savanna.mirantis.com/>`_ on internal Mirantis OpenStack Lab.
Jenkins keeps a pool of VMs to run tests in parallel. Still integration testing may take a while.

The integration tests result is +1 or -1 to *Verify* column in a code review from *savanna-ci* user.