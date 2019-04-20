How to Participate
==================

Getting started
---------------

* Make sure that your local git is properly configured by executing
  ``git config --list``. If not, configure ``user.name``, ``user.email``

* Create account on `Launchpad <https://launchpad.net/>`_
  (if you don't have one)

* Subscribe to `OpenStack general mail-list <http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack>`_

* Subscribe to `OpenStack development mail-list <http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-discuss>`_

* Create `OpenStack profile <https://www.openstack.org/profile/>`_

* Login to `OpenStack Gerrit <https://review.openstack.org/>`_ with your
  Launchpad id

  * Sign `OpenStack Individual Contributor License Agreement <https://review.openstack.org/#/settings/agreements>`_
  * Make sure that your email is listed in `identities <https://review.openstack.org/#/settings/web-identities>`_

* Subscribe to code-reviews. Go to your settings on https://review.openstack.org

  * Go to ``watched projects``
  * Add ``openstack/sahara``, ``openstack/sahara-extra``,
    ``openstack/python-saharaclient``, and ``openstack/sahara-image-elements``


How to stay in touch with the community
---------------------------------------

* If you have something to discuss use
  `OpenStack development mail-list <http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-discuss>`_.
  Prefix the mail subject with ``[sahara]``

* Join ``#openstack-sahara`` IRC channel on `freenode <http://freenode.net/>`_

* Attend Sahara team meetings

  * Weekly on Thursdays at 1400 UTC

  * IRC channel: ``#openstack-meeting-3``

  * See agenda at https://wiki.openstack.org/wiki/Meetings/SaharaAgenda


How to post your first patch for review
---------------------------------------

* Checkout Sahara code from `its repository <https://opendev.org/openstack/sahara>`_

* Carefully read https://docs.openstack.org/infra/manual/developers.html#development-workflow

  * Pay special attention to https://docs.openstack.org/infra/manual/developers.html#committing-a-change

* Apply and commit your changes

* Make sure that your code passes ``PEP8`` checks and unit-tests.
  See :doc:`development-guidelines`

* Post your patch for review

* Monitor the status of your patch review on https://review.openstack.org/#/



