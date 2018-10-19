=============
sahara-status
=============

----------------------------------------
CLI interface for Sahara status commands
----------------------------------------

Synopsis
========

::

  sahara-status <category> <command> [<args>]

Description
===========

:program:`sahara-status` is a tool that provides routines for checking the
status of a Sahara deployment.

Options
=======

The standard pattern for executing a :program:`sahara-status` command is::

    sahara-status <category> <command> [<args>]

Run without arguments to see a list of available command categories::

    sahara-status

Categories are:

* ``upgrade``

Detailed descriptions are below:

You can also run with a category argument such as ``upgrade`` to see a list of
all commands in that category::

    sahara-status upgrade

These sections describe the available categories and arguments for
:program:`sahara-status`.

Upgrade
~~~~~~~

.. _sahara-status-checks:

``sahara-status upgrade check``
  Performs a release-specific readiness check before restarting services with
  new code. For example, missing or changed configuration options,
  incompatible object states, or other conditions that could lead to
  failures while upgrading.

  **Return Codes**

  .. list-table::
     :widths: 20 80
     :header-rows: 1

     * - Return code
       - Description
     * - 0
       - All upgrade readiness checks passed successfully and there is nothing
         to do.
     * - 1
       - At least one check encountered an issue and requires further
         investigation. This is considered a warning but the upgrade may be OK.
     * - 2
       - There was an upgrade status check failure that needs to be
         investigated. This should be considered something that stops an
         upgrade.
     * - 255
       - An unexpected error occurred.

  **History of Checks**

  **10.0.0 (Stein)**

  * Sample check to be filled in with checks as they are added in Stein.
