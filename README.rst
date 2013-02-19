Elastic Hadoop on Openstack
===========================

Quickstart
----------
::

    # tools/install_venv
    # tools/with_venv python
    # tools/build_docs
    # tools/run_pep8
    # tools/run_tests


Git hook for pep8 check
-----------------------
Just add the following lines to .git/hooks/pre-commit and do chmod +x for it.
::
    #!/bin/sh
    # Auto-check for pep8
    tools/run_pep8
