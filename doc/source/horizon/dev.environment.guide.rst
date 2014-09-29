Sahara UI Dev Environment Setup
===============================

This page describes how to setup Horizon for developing Sahara by either
installing it as part of DevStack with Sahara or installing it in an isolated environment
and running from the command line.

Install as a part of DevStack
-----------------------------

See the `DevStack guide <../devref/devstack.html>`_ for more information
on installing and configuring DevStack with Sahara.

After Horizon installation, it will contain a Data Processing tab under Projects tab.
Sahara UI source code will be located at
``$DEST/horizon/openstack_dashboard/dashboards/project/data_processing``
where ``$DEST/`` is usually ``/opt/stack/``.

Isolated Dashboard for Sahara
-----------------------------

These installation steps serve two purposes:
 1. Setup a dev environment
 2. Setup an isolated Dashboard for Sahara

**Note** The host where you are going to perform installation has to be able
to connect to all OpenStack endpoints. You can list all available endpoints
using the following command:

.. sourcecode:: console

    $ keystone endpoint-list

1. Install prerequisites

  .. sourcecode:: console

      $ sudo apt-get update
      $ sudo apt-get install git-core python-dev gcc python-setuptools python-virtualenv node-less libssl-dev libffi-dev libxslt-dev
  ..

  On Ubuntu 12.10 and higher you have to install the following lib as well:

  .. sourcecode:: console

      $ sudo apt-get install nodejs-legacy
  ..

2. Checkout Horizon from git and switch to your version of OpenStack

  Here is an example:

  .. sourcecode:: console

      $ git clone https://github.com/openstack/horizon
  ..

  Then install the virtual environment:

  .. sourcecode:: console

      $ python tools/install_venv.py
  ..

3. Create a ``local_settings.py`` file

  .. sourcecode:: console

      $ cp openstack_dashboard/local/local_settings.py.example openstack_dashboard/local/local_settings.py
  ..

4. Modify ``openstack_dashboard/local/local_settings.py``

  Set the proper values for host and url variables:

  .. sourcecode:: python

     OPENSTACK_HOST = "ip of your controller"
  ..

  If you are using Nova-Network with ``auto_assign_floating_ip=True`` add the following parameter:

  .. sourcecode:: python

     SAHARA_AUTO_IP_ALLOCATION_ENABLED = True
  ..

5. If Sahara is not registered in keystone service catalog, then we should modify
   ``openstack_dashboard/api/sahara.py``:

   Add following lines before ``def client(request)``:
   Note, that you should replace the ip and port in ``SAHARA_URL`` with the
   appropriate values.

   .. sourcecode:: python

        SAHARA_URL = "http://localhost:8386/v1.1"

        def get_sahara_url(request):

            if SAHARA_URL:
                url = SAHARA_URL.rstrip('/')
                if url.split('/')[-1] in ['v1.0', 'v1.1']:
                    url = SAHARA_URL + '/' + request.user.tenant_id
                return url

            return base.url_for(request, SAHARA_SERVICE)
   ..

   After that modify sahara_url provided in ``def client(request):``

   .. sourcecode:: python

        sahara_url=get_sahara_url(request)
   ..

6. Start Horizon

  .. sourcecode:: console

      $ tools/with_venv.sh python manage.py runserver 0.0.0.0:8080
  ..

  This will start Horizon in debug mode. That means the logs will be written to console
  and if any exceptions happen, you will see the stack-trace rendered as a web-page.

  Debug mode can be disabled by changing ``DEBUG=True`` to ``False`` in
  ``local_settings.py``. In that case Horizon should be started slightly
  differently, otherwise it will not serve static files:

  .. sourcecode:: console

      $ tools/with_venv.sh  python manage.py runserver --insecure 0.0.0.0:8080
  ..

  **Note** It is not recommended to use Horizon in this mode for production.

7. Applying changes

  If you have changed any ``*.py`` files in
  ``horizon/openstack_dashboard/dashboards/project/data_processing`` directory,
  Horizon will notice that and reload automatically. However changes made to
  non-python files may not be noticed, so you have to restart Horizon again
  manually, as described in step 6.
