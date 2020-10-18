# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

from os import environ
from pathlib import Path

OVERRIDE_TEST_DATA_REPOSITORY = Path("/home") / "marti" / "experiments" / "actions-runner" / "_work" / "iris" / "iris" / "iris-test-data-master" / "test_data"
environ["OVERRIDE_TEST_DATA_REPOSITORY"] = str(OVERRIDE_TEST_DATA_REPOSITORY)
print(environ["OVERRIDE_TEST_DATA_REPOSITORY"])
