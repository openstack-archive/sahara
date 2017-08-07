
Log Guidelines
==============

Levels Guidelines
-----------------

During the Kilo release cycle the sahara community defined the following
log levels:

* Debug: Shows everything and is likely not suitable for normal production
  operation due to the sheer size of logs generated (e.g. scripts executions,
  process execution, etc.).
* Info: Usually indicates successful service start/stop, versions and such
  non-error related data. This should include largely positive units of work
  that are accomplished (e.g. service setup and configuration, cluster start,
  job execution information).
* Warning: Indicates that there might be a systemic issue;
  potential predictive failure notice (e.g. job execution failed).
* Error: An error has occurred and the administrator should research the error
  information (e.g. cluster failed to start, plugin violations of operation).
* Critical: An error has occurred and the system might be unstable, anything
  that eliminates part of sahara's intended functionalities; immediately get
  administrator assistance (e.g. failed to access keystone/database, failed to
  load plugin).


Formatting Guidelines
---------------------

Sahara uses string formatting defined in `PEP 3101`_ for logs.


.. _PEP 3101: https://www.python.org/dev/peps/pep-3101/
