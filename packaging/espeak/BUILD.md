# eSpeak NG native payload

This recipe prepares the eSpeak NG 1.52.0 command-line program and voice data
for a later Linux service bundle. It consumes the commit and archive hash in
`source-lock.json`, applies the local offline patch, and builds in Ubuntu 24.04
x86_64. It does not install files into the host or change service configuration.

The input archive is created from the owner-maintained bare Git mirror with
`scripts/intake_espeak_source.py`. The build recipe requires the archive and an
empty output directory. Run it in the project's pinned Ubuntu 24.04 build
container with networking disabled and only the source archive, repository
scripts, and output directory mounted. The container needs Python, Git, CMake,
a C compiler, and GNU make or Ninja. The pinned CUDA base image alone was
inspected and provides the compiler and Make, but lacks Python, Git and CMake.
Use a target build environment with those tools present and record its image
identity and tool versions. The recipe does not install build dependencies.

The source patch removes CMake's automatic Sonic FetchContent path. The
acceptance payload disables Sonic, MBROLA, PcAudio, the speech-player, async
support, compatibility links, and manpage generation. Klatt support remains
enabled. The CLI retains native eSpeak rate control. Without Sonic, the
high-rate processing path may differ in speed and voice character from builds
that use Sonic; the recipe makes no latency or output-equivalence claim for the
service's accepted range of 50–400 words per minute (the renderer maps speed
values 0.5–4.0 to those rates). In particular, compare rates above 350 before
claiming unchanged behavior.

The staged payload contains `bin/espeak-ng`, `share/espeak-ng-data`, all four
license notices from the locked source, the exact source archive, the local
patch, both build/intake scripts, this build note, the source lock, and a build
receipt with tool versions and file hashes. The `license_git_blob_ids` in the
lock are Git object IDs for the notice files; they are not SHA-256 checksums.
Keep the complete corresponding notices and source when distributing the
binary. The source review for this revision was bounded to identity, license,
and build configuration; it was not a complete security review of the full C
codebase.

No native build or speech execution is implied by the presence of these
recipes. The source archive and payload must be generated and checked in the
target container before a later packaging integration can consume them.
