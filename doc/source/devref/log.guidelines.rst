
Log Guidelines
======================

Levels Guidelines
-----------------

During Kilo release cycle Sahara community defined the following log levels:


* Debug: Shows everything and is likely not suitable for normal production
  operation due to the sheer size of logs generated (e.g. scripts executions,
  process execution, etc.).
* Info: Usually indicates successful service start/stop, versions and such
  non-error related data. This should include largely positive units of work
  that are accomplished (e.g. service setup, cluster start, successful job
  execution).
* Warning: Indicates that there might be a systemic issue;
  potential predictive failure notice (e.g. job execution failed).
* Error: An error has occurred and an administrator should research the event
  (e.g. cluster failed to start, plugin violations of operation).
* Critical: An error has occurred and the system might be unstable, anything
  that eliminates part of Sahara's intended functionality; immediately get
  administrator assistance (e.g. failed to access keystone/database, plugin
  load failed).


Formatting Guidelines
----------------------

Now Sahara uses string formatting defined in `PEP 3101`_ for logs.

.. code:: python

    LOG.warning(_LW("Incorrect path: {path}").format(path=path))


..


Translation Guidelines
----------------------

All log levels except Debug requires translation. None of the separate cli tools packaged
with Sahara contain log translations.

* Debug: no translation
* Info: _LI
* Warning: _LW
* Error: _LE
* Critical: _LC

.. _PEP 3101: https://www.python.org/dev/peps/pep-3101/
