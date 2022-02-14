from iris import load_cube as iris_loadcube
from iris.experimental.ugrid import PARSE_UGRID_ON_LOAD

from .. import BENCHMARK_DATA, run_function_elsewhere
from .stock import (
    create_file__xios_2d_face_half_levels,
    create_file__xios_3d_face_half_levels,
)


def generate_cube_like_2d_cubesphere(
    n_cube: int, with_mesh: bool, output_path: str
):
    """
    Construct and save to file an LFRIc cubesphere-like cube for a given
    cubesphere size, *or* a simpler structured (UM-like) cube of equivalent
    size.

    NOTE: this function is *NEVER* called from within this actual package.
    Instead, it is to be called via benchmarks.remote_data_generation,
    so that it can use up-to-date facilities, independent of the ASV controlled
    environment which contains the "Iris commit under test".
    This means:
      * it must be completely self-contained : i.e. it includes all its
        own imports, and saves results to an output file.

    """
    from iris import save
    from iris.tests.stock.mesh import sample_mesh, sample_mesh_cube

    n_face_nodes = n_cube * n_cube
    n_faces = 6 * n_face_nodes

    # Set n_nodes=n_faces and n_edges=2*n_faces
    # : Not exact, but similar to a 'real' cubesphere.
    n_nodes = n_faces
    n_edges = 2 * n_faces
    if with_mesh:
        mesh = sample_mesh(
            n_nodes=n_nodes, n_faces=n_faces, n_edges=n_edges, lazy_values=True
        )
        cube = sample_mesh_cube(mesh=mesh, n_z=1)
    else:
        cube = sample_mesh_cube(nomesh_faces=n_faces, n_z=1)

    # Strip off the 'extra' aux-coord mapping the mesh, which sample-cube adds
    # but which we don't want.
    cube.remove_coord("mesh_face_aux")

    # Save the result to a named file.
    save(cube, output_path)


def make_cube_like_2d_cubesphere(n_cube: int, with_mesh: bool):
    """
    Generate an LFRIc cubesphere-like cube for a given cubesphere size,
    *or* a simpler structured (UM-like) cube of equivalent size.

    All the cube data, coords and mesh content are LAZY, and produced without
    allocating large real arrays (to allow peak-memory testing).

    NOTE: the actual cube generation is done in a stable Iris environment via
    benchmarks.remote_data_generation, so it is all channeled via cached netcdf
    files in our common testdata directory.

    """
    identifying_filename = (
        f"cube_like_2d_cubesphere_C{n_cube}_Mesh={with_mesh}.nc"
    )
    filepath = BENCHMARK_DATA / identifying_filename
    if not filepath.exists():
        # Create the required testfile, by running the generation code remotely
        #  in a 'fixed' python environment.
        run_function_elsewhere(
            generate_cube_like_2d_cubesphere,
            n_cube,
            with_mesh=with_mesh,
            output_path=str(filepath),
        )

    # File now *should* definitely exist: content is simply the desired cube.
    with PARSE_UGRID_ON_LOAD.context():
        cube = iris_loadcube(str(filepath))
    return cube


def make_cubesphere_testfile(c_size, n_levels=0, n_times=1):
    """
    Build a C<c_size> cubesphere testfile in a given directory, with a standard naming.
    If n_levels > 0 specified: 3d file with the specified number of levels.
    Return the file path.

    """
    n_faces = 6 * c_size * c_size
    stem_name = f"mesh_cubesphere_C{c_size}_t{n_times}"
    kwargs = dict(
        temp_file_dir=None,
        dataset_name=stem_name,  # N.B. function adds the ".nc" extension
        n_times=n_times,
        n_faces=n_faces,
    )

    three_d = n_levels > 0
    if three_d:
        kwargs["n_levels"] = n_levels
        kwargs["dataset_name"] += f"_{n_levels}levels"
        func = create_file__xios_3d_face_half_levels
    else:
        func = create_file__xios_2d_face_half_levels

    file_path = func(**kwargs)
    return file_path