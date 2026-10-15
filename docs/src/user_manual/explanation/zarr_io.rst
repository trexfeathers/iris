.. explanation:: Zarr I/O Handling in Iris
   :tags: topic_load_save

   Read about how Iris loads and saves Zarr stores.

.. include:: ../../common_links.inc

.. _zarr_io:

=========================
Zarr I/O Handling in Iris
=========================

.. readingtime::

`Zarr <https://zarr.dev/>`_ stores an array as many independently compressed
chunks under a prefix, rather than as one file. Iris reads Zarr version 2 and
version 3 stores natively, through
`zarr-python <https://zarr.readthedocs.io/>`_.

``zarr`` is an **optional dependency**, and Iris requires at least version
3.0.8. Install it to load Zarr stores::

    conda install -c conda-forge "zarr>=3.0.8"

Iris without it installs and runs normally, raising an ``ImportError`` that
names the package and the version floor if you ask it to load a store.

Loading
-------

A store is a directory, or a URL, so pass it where you would pass a file::

    cubes = iris.load("/data/forecast.zarr")

Iris recognises a local store by the metadata file at its root -- ``zarr.json``
for version 3, ``.zgroup`` for version 2 -- not by the ``.zarr`` suffix, so a
directory that merely has the suffix is not mistaken for one.

Saving
------

A store is a directory, or a URL, so pass it where you would pass a file::

    iris.save(cubes, "/data/forecast.zarr")

Iris writes Zarr **version 3** stores. A whole :class:`~iris.cube.CubeList`
goes into one store, which is opened once.

Unlike the netCDF saver, this one does **not** overwrite. ``iris.save`` raises
if the target already exists, because replacing a store means deleting many
objects one at a time, and an interrupted replacement destroys what was there
without completing what replaces it. Say so explicitly to opt in::

    iris.save(cubes, "/data/forecast.zarr", mode="w")       # replace
    iris.save(more_cubes, "/data/forecast.zarr", mode="a")  # add what is not there

``mode="a"`` adds a *new* array or group to a store that already holds others.
It never extends, rewrites, resizes or re-chunks an array that is already
there. Saving a cube whose own data variable already exists in the target
group is an error rather than an overwrite, so saving the same cube twice with
``mode="a"`` raises rather than duplicating it. Appending to data is not
supported, for Zarr or for netCDF: deciding whether incoming data is
compatible with what a store already holds is a data-model problem, and the
storage format does not solve it.

Everything else a cube carries -- its coordinates, bounds and cell measures --
is not matched against what the store already holds. Adding a cube to a store
that already carries a ``latitude`` array writes a second one, named
``latitude_0``, rather than reusing the first. Deciding whether two
coordinates are "the same" across unequal values, differing units and
different calendars is its own piece of work, so Iris does not attempt it.

Storage keywords
^^^^^^^^^^^^^^^^

The Zarr saver takes **zarr-python's** vocabulary, not netCDF's::

    iris.save(
        cube,
        "out.zarr",
        chunks=(1, 50, 50),
        shards=(4, 100, 100),
        compressors=[zarr.codecs.BloscCodec(cname="zstd")],
    )

``chunks``, ``shards``, ``compressors``, ``filters``, ``serializer`` and
``order`` are passed through as zarr-python defines them. A netCDF keyword such as
``zlib=True`` raises :class:`TypeError` naming the Zarr replacement where there
is one, and saying there is none where there is not. The two compression models
differ, and a keyword that let you say ``complevel=4`` while quietly giving you
Blosc would be misleading rather than convenient.

``chunks`` defaults to the cube's own lazy chunking, so data is written in the
shape it is held in.

Deferred saving
^^^^^^^^^^^^^^^

``compute=False`` returns a :class:`dask.delayed.Delayed` that writes the lazy
data when computed, and consolidates the store's metadata after the last chunk::

    result = iris.save(cubes, "deferred.zarr", compute=False)
    result.compute()

Consolidated metadata
^^^^^^^^^^^^^^^^^^^^^

Iris writes a consolidated metadata document at the store's root when the save
completes, because it is what makes a remote store usable: a reader fetches one
object instead of one per array. Pass ``consolidate_metadata=False`` to decline.

When Iris adds to a store that already carries one, it rewrites it. A
consolidated document that does not mention what was just written is what a
default reader believes, so stale consolidation hides data.

What an interrupted save leaves behind
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A partial store, and Iris offers no rollback. Zarr has no multi-object
transaction: a store's metadata and its chunks are separate objects, so a save
interrupted between them leaves the two disagreeing, and a missing chunk is not
an error -- it reads back as the fill value, with no warning. The usual
mitigation, writing to a temporary name and renaming on success, is not
adopted: a directory rename is atomic on a local filesystem but object stores
have no equivalent, so the guarantee would evaporate exactly where Zarr is most
used. Callers who need transactional writes want `Icechunk
<https://icechunk.io/>`_.

Meshes
^^^^^^

A cube with an unstructured :class:`~iris.mesh.MeshXY` saves correctly: the
store carries the full CF-UGRID structure, the same mesh, topology and
connectivity variables a netCDF save would write. Loading it back does not
yet rebuild the mesh -- the cube comes back without one, however completely
the store describes it.

Remote stores
-------------

A URL with one of the ``s3``, ``gs``, ``az`` or ``abfs`` schemes, ending in
``.zarr``, is passed to zarr-python unaltered::

    cubes = iris.load("s3://noaa-gfs-bdp-pds/forecast.zarr")

Iris adds no store library of its own and handles no credentials. Install the
one your scheme needs -- ``s3fs``, ``gcsfs``, ``adlfs`` -- and configure it as
that package documents. zarr-python raises an ``ImportError`` naming the
package if it is missing.

Groups
------

A Zarr store may hold several groups, and they need not describe the same
thing. Iris loads **one** group per call, like xarray, rather than merging
them: ``iris.load`` reads the root group, and a store whose root holds no data
variables raises a message naming the groups that do.

To read another group, call the Zarr loader directly::

    from iris.cube import CubeList
    import iris.fileformats.zarr

    cubes = CubeList(
        iris.fileformats.zarr.load_cubes(
            "/data/sentinel.zarr", group="measurements/reflectance/r10m"
        )
    )

Saving takes a group more directly: ``iris.save`` itself takes a ``group=``
keyword, naming a ``/``-separated path within the store::

    iris.save(cubes, "/data/sentinel.zarr", group="measurements/reflectance/r10m")

Passing ``group=`` implies ``mode="a"``, because writing a group into a store
means the store may already hold others. ``iris.load`` and ``iris.load_cube``
have no equivalent keyword: reading a group other than the root means calling
the Zarr loader directly, as above.

Dimension names
---------------

A netCDF dimension has a name, one length, and a meaning shared across the
whole file. A Zarr dimension name is weaker in three ways, and all three are
permitted by the version 3 specification:

* an array need not name its dimensions at all;
* it may name some and not others;
* the same name in two arrays guarantees nothing -- not even the same length.

So Iris matches dimensions on the pair *(name, length)*. Two arrays share a
dimension when they name it identically **and** it is the same length in
both. A dimension with no name is **anonymous**, and never matches anything;
the cube simply has a dimension with no coordinate on it, which is an
ordinary Iris cube. A dimension name used at two different lengths is
reported with a warning and links nothing.

Version 2 stores have no dimension-name field, and carry names in an
``_ARRAY_DIMENSIONS`` attribute instead -- the convention xarray established.
Iris reads it, and does not pass it on to the cube.

Storage bookkeeping is not a CF attribute
-----------------------------------------

Two attributes never reach ``cube.attributes``, because they describe the
store rather than the data: ``_ARRAY_DIMENSIONS``, covered above, and
``_NCProperties``, the provenance stamp netCDF-c's NCZarr writer stamps onto
the root group of every store it writes. netCDF4-python has always hidden
``_NCProperties`` from a cube loaded through netCDF, and Iris hides it on the
Zarr path too, for the same reason. A cube loaded from a version 2 store and
the same cube loaded from a version 3 store therefore carry the same
attributes.

Missing data
------------

Zarr applies no masking of its own, so Iris does it, from the CF attributes:
``_FillValue`` and ``missing_value`` for sentinels,
``valid_min``/``valid_max``/``valid_range`` for a range, and
``scale_factor``/``add_offset`` for packed data.

A Zarr array also has a ``fill_value`` in its metadata. This is **not** a
missing-value declaration: it says what a chunk that was never written reads
back as, and zarr-python defaults it to zero. Iris therefore ignores it as a
mask source on version 3, where it is a required field, and uses it on
version 2 only when the array declares no CF attribute -- which is what
version 2 writers meant by it, and what xarray does.

A version 2 store that declares neither ``_FillValue`` nor ``missing_value``
therefore has its storage ``fill_value`` treated as missing data, so a value
equal to it is masked -- including a genuine zero, since zarr-python defaults
``fill_value`` to zero on every array it creates, version 2 included. Iris
warns about this specific case -- the adopted sentinel is zero -- naming the
variable and the value, because zero is the one value plausible as real data
rather than a sentinel a writer chose on purpose; a non-zero storage fill
value, such as the classic netCDF sentinel ``9.96921e+36`` written by an
older tool, is not warned about. Setting a ``_FillValue`` attribute on the
array prevents the masking and, where it would have fired, the warning.

On save, Iris writes the missing-value declaration as well as the storage fill:
a masked cube gets a ``_FillValue`` attribute even when it carried none of its
own, because on version 3 the attribute is what declares missing data and the
storage ``fill_value`` is not. Without it, every masked point would read back
unmasked. Pass ``fill_value=`` to choose the sentinel; the default is the same
one netCDF uses for that dtype.

A floating ``_FillValue`` is written as the base64 of a little-endian
``float64``, which is what xarray and the wider Zarr ecosystem read. This
deviates from CF section 2.5.1, which asks for a value of the variable's own
type. The deviation is deliberate and load-bearing: a plain JSON number there
makes the whole store unreadable by default xarray, which is a worse outcome
than a convention deviation that every reader understands.

Chunking
--------

Iris chooses Dask chunks from the store's own chunking, as it does for
netCDF, and :data:`~iris.fileformats.cf.loader.CHUNK_CONTROL` works the same
way for both formats.

One rule is specific to Zarr. A Zarr chunk is the atomic unit of storage:
reading any part of one fetches and decompresses the whole object. So Iris
rounds the computed chunking **up** to a whole multiple of the store's
chunking, never below it. When a single store chunk is already larger than
Dask's target chunk size, the store's layout is the binding constraint on
memory per task, and Iris warns to say so.

A **sharded** array is chunked on its inner chunks, not its shards. Zarr's
sharding codec is indexed, so a reader fetches only the inner chunks it
needs.

zarr-python fetches chunks concurrently, under its own ``zarr.config``
setting ``async.concurrency``. Iris does not change it. Dask's worker count
and that concurrency multiply, so a large Dask pool over a remote store can
open far more connections than either number suggests; if you are
rate-limited, lower one of them.

Attributes
----------

A Zarr attribute value may be any JSON literal, including a nested object or
an array of arrays, which CF cannot express at any rank. Iris carries such a
value onto the cube unchanged and does not interpret it. See
:issue:`7288` for the wider question of how the CF attribute model should map
onto JSON.

.. note::

    A cube carrying such an attribute **cannot be saved as netCDF**, because
    netCDF attribute values are scalars, strings and one-dimensional arrays.
    The failure comes from the netCDF library, as a ``TypeError`` naming the
    attribute::

        TypeError: illegal data type for attribute b'stac_discovery', ...

    It does not name the cube; see :issue:`7329`. Delete the attribute
    before saving::

        del cube.attributes["stac_discovery"]

.. _zarr_io_nczarr:

NCZarr
------

Iris also reads and writes Zarr through netCDF-c's NCZarr driver, reached by
way of a URL fragment::

    iris.load("file:///data/forecast.zarr#mode=nczarr,file")

NCZarr implements Zarr version 2, and writes scalar variables as length-one
arrays. The native reader described above handles both versions, and is
what a plain path or URL -- one with no ``#mode=`` fragment -- reaches.
