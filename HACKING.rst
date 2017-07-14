Sahara Style Commandments
=========================

- Step 1: Read the OpenStack Style Commandments
  https://docs.openstack.org/hacking/latest/
- Step 2: Read on

Sahara Specific Commandments
----------------------------

Commit Messages
---------------
Using a common format for commit messages will help keep our git history
readable. Follow these guidelines:

- [S365] First, provide a brief summary of 50 characters or less. Summaries
  of greater than 72 characters will be rejected by the gate.

- [S364] The first line of the commit message should provide an accurate
  description of the change, not just a reference to a bug or blueprint.

Imports
-------
- [S366, S367] Organize your imports according to the ``Import order``

Dictionaries/Lists
------------------

- [S360] Ensure default arguments are not mutable.
- [S368] Must use a dict comprehension instead of a dict constructor with a
         sequence of key-value pairs. For more information, please refer to
         http://legacy.python.org/dev/peps/pep-0274/

Logs
----

- [S373] Don't translate logs

- [S374] You used a deprecated log level

Importing json
--------------

- [S375] It's more preferable to use ``jsonutils`` from ``oslo_serialization``
         instead of ``json`` for operating with ``json`` objects.
