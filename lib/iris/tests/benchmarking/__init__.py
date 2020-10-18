# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

from os import environ
from pathlib import Path

ASV_ENV_DIR = Path(environ["ASV_ENV_DIR"])
OVERRIDE_TEST_DATA_REPOSITORY = ASV_ENV_DIR / "lib" / "python3.7" / "site-packages" / "iris-test-data" / "test_data"
environ["OVERRIDE_TEST_DATA_REPOSITORY"] = str(OVERRIDE_TEST_DATA_REPOSITORY)
print(environ["OVERRIDE_TEST_DATA_REPOSITORY"])
