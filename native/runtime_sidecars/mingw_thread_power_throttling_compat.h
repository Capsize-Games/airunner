/*
 * mingw_thread_power_throttling_compat.h
 *
 * Compatibility shim for mingw-w64 toolchains whose headers predate the
 * thread power-throttling API declarations.  llama.cpp's ggml-cpu.c uses
 * THREAD_POWER_THROTTLING_STATE / THREAD_POWER_THROTTLING_CURRENT_VERSION /
 * THREAD_POWER_THROTTLING_EXECUTION_SPEED behind `#if _WIN32_WINNT >= 0x0602`
 * (ggml_thread_apply_priority).  Newer mingw-w64 headers declare these, but
 * several distro packages (e.g. the mingw-w64 shipped on GitHub's
 * ubuntu-latest runner) do not, so the cross-compile fails with "unknown
 * type name 'THREAD_POWER_THROTTLING_STATE'" (issue #2077).
 *
 * The build script (scripts/build_runtime_sidecars.sh) force-includes this
 * header with `-include` only when a configure-time probe shows the toolchain
 * headers lack the API, so it never conflicts with toolchains that already
 * declare it.  The layout matches the Windows SDK definition.
 */
#ifndef AIRUNNER_MINGW_THREAD_POWER_THROTTLING_COMPAT_H
#define AIRUNNER_MINGW_THREAD_POWER_THROTTLING_COMPAT_H

#if defined(_WIN32) && !defined(THREAD_POWER_THROTTLING_CURRENT_VERSION)

typedef struct _THREAD_POWER_THROTTLING_STATE {
    unsigned long Version;
    unsigned long ControlMask;
    unsigned long StateMask;
} THREAD_POWER_THROTTLING_STATE;

#define THREAD_POWER_THROTTLING_CURRENT_VERSION 1
#define THREAD_POWER_THROTTLING_EXECUTION_SPEED 0x1

#endif /* _WIN32 && !THREAD_POWER_THROTTLING_CURRENT_VERSION */

#endif /* AIRUNNER_MINGW_THREAD_POWER_THROTTLING_COMPAT_H */
