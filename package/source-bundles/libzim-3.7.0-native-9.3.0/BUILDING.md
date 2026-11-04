# Building the libzim native source bundle

This directory contains the source for Python `libzim` 3.7.0 and its bundled
native `libzim` 9.3.0 library, plus the exact pinned native dependency source
archives used for the Linux x86_64 candidate build. `source-manifest.json`
records each input's version, origin, and SHA-256. The source archive for
Python `libzim` is from tag `v3.7.0-capsize.2` in the private maintenance copy;
the tag points to merged commit `854ffa91605d6406517147ca05f3878b840c8727`
and source tree `e8c1c25f966db52f9599b6c63bc393965d247eb5`. The private
release is published under tag `v3.7.0-capsize.2`.

The native build was performed with GCC/G++ 13.3, Meson 1.12.1, Ninja 1.12.1,
and Python 3.13.5 on x86_64 Linux. It used no network access or source-fetching
Meson wraps. Build tools and system headers are build prerequisites, not
included source inputs. Do not run the original kiwix-build dependency download
action; it downloads and extracts an archive without verifying a digest.

The wrapper build used the hash-verified Cython 3.0.11 universal wheel
(`0e25f6425ad4a700d7f77cd468da9161e63658837d1bc34861a9861a4ef6346d`) and
the already reviewed setuptools 84.2.1, wheel 0.48.0, and packaging 26.3
wheel inputs. Cython's PyPI sdist hash is
`7146dd2af8682b4ca61331851e6aebce9fe5158e75300343f80c07ca80b1faff`.
Those build tools were installed in a separate uv environment from
hash-pinned local wheels; they are not runtime dependencies or included in
this GPL source bundle.

The commands below describe the candidate build. They assume the source files
in `input-sources/` have been verified against `source-manifest.json`, and that
`meson`, `ninja`, a C/C++ toolchain, `pkg-config`, `make`, and `dpkg-source` are
already available. The source package files are extracted locally; the recipe
does not install packages or fetch inputs.

```sh
set -eu
bundle=$(cd "$(dirname "$0")" && pwd)
work=${TMPDIR:-/tmp}/libzim-rebuild
prefix="$work/prefix"
mkdir -p "$work/src" "$prefix"
cd "$work/src"

tar -xf "$bundle/input-sources/xz-5.2.11.tar.xz"
tar -xf "$bundle/input-sources/zstd-1.5.4.tar.gz"
tar -xf "$bundle/input-sources/icu4c-79.1-sources.tgz"
tar -xf "$bundle/input-sources/xapian-core-1.4.32.tar.xz"
dpkg-source -x "$bundle/input-sources/zlib_1.3.dfsg+really1.3.1-1.dsc" zlib
dpkg-source -x "$bundle/input-sources/util-linux_2.41.5-0+deb13u1.dsc" util-linux

cd xz-5.2.11
CFLAGS='-O2 -fPIC' ./configure --prefix="$prefix" --disable-shared --enable-static --disable-doc
make -j1
make check
make install

cd "$work/src/zstd-1.5.4/build/meson"
meson setup "$work/zstd-build" "$work/src/zstd-1.5.4/build/meson" --prefix="$prefix" \
  --default-library=static -Dbin_tests=false -Dbin_programs=false \
  -Dbin_contrib=false
ninja -C "$work/zstd-build" -j1
ninja -C "$work/zstd-build" install

cd "$work/src/icu/source"
CFLAGS='-O2 -fPIC' CXXFLAGS='-O2 -fPIC' ./configure --prefix="$prefix" \
  --disable-shared --enable-static --disable-dyload --disable-extras \
  --disable-icuio --disable-tests --disable-samples --with-data-packaging=static
make -j1
make install

cd "$work/src/xapian-core-1.4.32"
CFLAGS='-O2 -fPIC' CXXFLAGS='-O2 -fPIC' ./configure --prefix="$prefix" \
  --enable-static --disable-shared --disable-backend-chert \
  --disable-backend-remote --disable-documentation --disable-sse
make -j1
make install

# Build PIC static zlib and UUID archives from the included Debian source.
cd "$work/src/zlib"
CFLAGS='-O2 -fPIC' ./configure --static --prefix="$prefix"
make -j1
make install

cd "$work/src/util-linux"
meson setup "$work/uuid-build" . --prefix="$prefix" --default-library=static \
  -Dbuild-libuuid=enabled -Dbuild-libblkid=disabled \
  -Dbuild-libfdisk=disabled -Dbuild-libmount=disabled \
  -Dbuild-libsmartcols=disabled -Dbuild-liblastlog2=disabled \
  -Dbuild-python=disabled -Dbuild-uuidd=disabled -Dprogram-tests=false \
  -Dnls=disabled -Dtranslate-docs=disabled
ninja -C "$work/uuid-build" libuuid/libuuid.a -j1
cp "$work/uuid-build/libuuid/libuuid.a" "$prefix/lib/libuuid.a"
cp "$work/uuid-build/meson-private/uuid.pc" "$prefix/lib/pkgconfig/uuid.pc"

# Xapian's installed pkg-config file names UUID and zlib with `-l` flags. On
# the recorded host Meson resolved those names to non-PIC system archives.
# Point that build-local metadata at the source-built PIC archives before
# configuring libzim. This changes only the private build prefix, not sources.
sed -i "s/Libs.private: -luuid -lz/Libs.private: $prefix\/lib\/libuuid.a $prefix\/lib\/libz.a/" \
  "$prefix/lib/pkgconfig/xapian-core.pc"

cd "$work/src"
tar -xf "$bundle/input-sources/libzim-9.3.0.tar.gz"
PKG_CONFIG_PATH="$prefix/lib/pkgconfig:$prefix/lib/x86_64-linux-gnu/pkgconfig" \
  CFLAGS='-O2 -fPIC' CXXFLAGS='-O2 -fPIC' \
  meson setup libzim-build libzim-9.3.0 --prefix="$prefix" \
    --wrap-mode=nodownload --default-library=shared \
    -Dstatic-linkage=true -Dwith_xapian=true -Dtests=true \
    -Dexamples=false -Ddoc=false -Dtest_data_dir=none \
    -Dwith_xapian_fuller=false
ninja -C libzim-build -j1
meson test -C libzim-build --print-errorlogs
```

The candidate was built with `WITH_TEST_DATA=0`; all 28 native unit tests
passed. The patched Python wrapper source was then compiled against the
candidate native library using the reviewed Cython 3.0.11 wheel and the
hash-pinned setuptools 84.2.1, wheel 0.48.0, and packaging 26.3 build tools.
The build ran with `DONT_DOWNLOAD_LIBZIM=1`, an empty environment, and package
indexes disabled. It produced `libzim-3.7.0+capsize.2-cp313-cp313-linux_x86_64.whl`.
That wheel passed RECORD verification, import, synthetic create/read/full-text
search, the wrapper's focused tests, and the service's ZIM document-loader
path. The service probe loaded this exact candidate wheel from its separate
runtime environment. The wheel was built on Debian 13 with glibc 2.41 and has a generic
`linux_x86_64` tag; it is an isolated acceptance candidate, not a manylinux
distribution artifact. No real ZIM corpus was used. The current selected
public Python wheel does not contain this candidate.

To build that wrapper wheel after the native commands above, prepare a clean
source directory from `python-libzim-3.7.0-capsize.tar.gz`. Copy
`libzim-9.3.0/include/zim/` into the wrapper's `include/zim/` directory, then
copy the generated `zim_config.h` from the native Meson build into that same
directory. Copy the candidate `libzim.so.9.3.0` to `libzim/libzim.so.9` and
create `libzim/libzim.so` as a link to `libzim.so.9`. With the reviewed Python
build environment on PATH, run from that clean wrapper source directory:

```sh
env -i HOME=/tmp/libzim-build-home TMPDIR=/tmp/libzim-build-tmp \
  PATH="/path/to/reviewed-build-env/bin:/usr/bin:/bin" \
  DONT_DOWNLOAD_LIBZIM=1 LIBZIM_DL_VERSION=9.3.0-1 \
  PIP_NO_INDEX=1 UV_OFFLINE=1 CC=gcc CXX=g++ CXXFLAGS='-O2 -fPIC' \
  /path/to/reviewed-build-env/bin/python setup.py bdist_wheel \
  --dist-dir /tmp/libzim-wheelhouse
```

This host build's generic `linux_x86_64` wheel tag reflects the Debian 13
builder. Do not relabel it as manylinux. The source review record contains its
wheel hash, ELF requirements, and the remaining Ubuntu 24 target-runtime check.

License texts for the wrapper, native library, and native dependencies are
preserved in `licenses/` and in the original source archives. The Python
wrapper is GPL-3.0-or-later; the native library is GPL-2.0-or-later. This
bundle is corresponding source/build material for the candidate native build,
not a claim that an unmodified upstream wheel has been rebuilt or released.
