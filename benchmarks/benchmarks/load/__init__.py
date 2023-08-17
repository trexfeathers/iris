# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
File loading benchmark tests.

Where applicable benchmarks should be parameterised for two sizes of input data:
  * minimal: enables detection of regressions in parts of the run-time that do
             NOT scale with data size.
  * large: large enough to exclusively detect regressions in parts of the
           run-time that scale with data size. Size should be _just_ large
           enough - don't want to bloat benchmark runtime.

"""

from iris import AttributeConstraint, Constraint, load, load_cube
from iris.cube import Cube
from iris.fileformats.um import structured_um_loading

from ..generate_data import BENCHMARK_DATA, REUSE_DATA, run_function_elsewhere
from ..generate_data.um_files import create_um_files


class LoadAndRealise:
    # For data generation
    timeout = 600.0
    params = [
        [(50, 50, 2), (1280, 960, 5), (2, 2, 1000)],
        [False, True],
        ["FF", "PP", "NetCDF"],
    ]
    param_names = ["xyz", "compressed", "file_format"]

    def setup_cache(self) -> dict:
        file_type_args = self.params[2]
        file_path_dict = {}
        for xyz in self.params[0]:
            file_path_dict[xyz] = {}
            x, y, z = xyz
            for compress in self.params[1]:
                file_path_dict[xyz][compress] = create_um_files(
                    x, y, z, 1, compress, file_type_args
                )
        return file_path_dict

    def setup(
        self,
        file_path_dict: dict,
        xyz: tuple,
        compress: bool,
        file_format: str,
    ) -> None:
        self.file_path = file_path_dict[xyz][compress][file_format]
        self.cube = self.load()

    def load(self) -> Cube:
        return load_cube(self.file_path)

    def time_load(self, _, __, ___, ____) -> None:
        _ = self.load()

    def time_realise(self, _, __, ___, ____) -> None:
        # Don't touch cube.data - permanent realisation plays badly with ASV's
        #  re-run strategy.
        assert self.cube.has_lazy_data()
        self.cube.core_data().compute()


class STASHConstraint:
    # xyz sizes mimic LoadAndRealise to maximise file re-use.
    params = [[(2, 2, 2), (1280, 960, 5), (2, 2, 1000)], ["FF", "PP"]]
    param_names = ["xyz", "file_format"]

    def setup_cache(self) -> dict:
        file_type_args = self.params[1]
        file_path_dict = {}
        for xyz in self.params[0]:
            x, y, z = xyz
            file_path_dict[xyz] = create_um_files(
                x, y, z, 1, False, file_type_args
            )
        return file_path_dict

    def setup(
        self, file_path_dict: dict, xyz: tuple, file_format: str
    ) -> None:
        self.file_path = file_path_dict[xyz][file_format]

    def time_stash_constraint(self, _, __, ___) -> None:
        _ = load_cube(self.file_path, AttributeConstraint(STASH="m??s??i901"))


class TimeConstraint:
    params = [[3, 20], ["FF", "PP", "NetCDF"]]
    param_names = ["time_dim_len", "file_format"]

    def setup_cache(self) -> dict:
        file_type_args = self.params[1]
        file_path_dict = {}
        for time_dim_len in self.params[0]:
            file_path_dict[time_dim_len] = create_um_files(
                20, 20, 5, time_dim_len, False, file_type_args
            )
        return file_path_dict

    def setup(
        self, file_path_dict: dict, time_dim_len: int, file_format: str
    ) -> None:
        self.file_path = file_path_dict[time_dim_len][file_format]
        self.time_constr = Constraint(time=lambda cell: cell.point.year < 3)

    def time_time_constraint(self, _, __, ___) -> None:
        _ = load_cube(self.file_path, self.time_constr)


class ManyVars:
    FILE_PATH = BENCHMARK_DATA / "many_var_file.nc"

    @staticmethod
    def _create_file(save_path: str) -> None:
        """Is run externally - everything must be self-contained."""
        import numpy as np

        from iris import save
        from iris.coords import AuxCoord
        from iris.cube import Cube

        data_len = 8
        data = np.arange(data_len)
        cube = Cube(data, units="unknown")
        extra_vars = 80
        names = ["coord_" + str(i) for i in range(extra_vars)]
        for name in names:
            coord = AuxCoord(data, long_name=name, units="unknown")
            cube.add_aux_coord(coord, 0)
        save(cube, save_path)

    def setup_cache(self) -> None:
        if not REUSE_DATA or not self.FILE_PATH.is_file():
            # See :mod:`benchmarks.generate_data` docstring for full explanation.
            _ = run_function_elsewhere(
                self._create_file,
                str(self.FILE_PATH),
            )

    def time_many_var_load(self) -> None:
        _ = load(str(self.FILE_PATH))


class StructuredFF:
    """
    Test structured loading of a large-ish fieldsfile.

    Structured load of the larger size should show benefit over standard load,
    avoiding the cost of merging.
    """

    params = [[(2, 2, 2), (1280, 960, 5), (2, 2, 1000)], [False, True]]
    param_names = ["xyz", "structured_loading"]

    def setup_cache(self) -> dict:
        file_path_dict = {}
        for xyz in self.params[0]:
            x, y, z = xyz
            file_path_dict[xyz] = create_um_files(x, y, z, 1, False, ["FF"])
        return file_path_dict

    def setup(self, file_path_dict, xyz, structured_load):
        self.file_path = file_path_dict[xyz]["FF"]
        self.structured_load = structured_load

    def load(self):
        """Load the whole file (in fact there is only 1 cube)."""

        def _load():
            _ = load(self.file_path)

        if self.structured_load:
            with structured_um_loading():
                _load()
        else:
            _load()

    def time_structured_load(self, _, __, ___):
        self.load()
