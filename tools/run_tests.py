import sys

import os
from eho.common.test_lib import run_tests
from nose import config
from nose import core
import eho.tests


def main():
    c = config.Config(stream=sys.stdout,
                      env=os.environ,
                      verbosity=3,
                      includeExe=True,
                      traverseNamespace=True,
                      plugins=core.DefaultPluginManager())
    c.configureWhere(eho.tests.__path__)
    sys.exit(run_tests(c))


if __name__ == "__main__":
    main()
