import os

from nose import config
from nose import core

import sys
from savanna.openstack.test_lib import run_tests
import savanna.tests


def main():
    c = config.Config(stream=sys.stdout,
                      env=os.environ,
                      verbosity=3,
                      includeExe=True,
                      traverseNamespace=True,
                      plugins=core.DefaultPluginManager())
    c.configureWhere(savanna.tests.__path__)
    sys.exit(run_tests(c))


if __name__ == "__main__":
    main()
