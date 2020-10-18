# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

from os import environ
from pathlib import Path

ASV_ENV_DIR = environ["ASV_ENV_DIR"]
environ["OVERRIDE_TEST_DATA_REPOSITORY"] = Path(ASV_ENV_DIR) / "iris-test-data" / "test_data"
