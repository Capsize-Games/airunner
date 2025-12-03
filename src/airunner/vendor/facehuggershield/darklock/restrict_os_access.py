from airunner.vendor.facehuggershield.darklock.singleton import Singleton
import builtins
import os
import sys
import logging
import threading

# Store the true built-in import function at module load time
_TRUE_BUILTIN_IMPORT = builtins.__import__

# Basic logging configuration for debugging this module.
# Consider a more centralized logging setup for the application.
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(lineno)d - %(message)s')
# Get a logger specific to this module.
logger = logging.getLogger(__name__)


class RestrictOSAccess(metaclass=Singleton):
    """
    Restricts OS-level operations for security. WARNING: Do NOT call activate() from module-level code or __init__.
    Only call activate() from your main application entry point, after all imports are complete.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.original_open = builtins.open
            self.original_os_write = os.write
            self.original_makedirs = os.makedirs
            self.original_mkdir = os.mkdir
            self.original_remove = os.remove  # Capture original os.remove
            self.original_rmdir = os.rmdir  # Capture original os.rmdir
            self.original_unlink = os.unlink  # Capture original os.unlink (alias for remove)
            self.original_rename = os.rename  # Capture original os.rename
            self.original_replace = os.replace  # Capture original os.replace
            self.original_link = getattr(os, 'link', None)  # os.link may not exist on all platforms
            self.original_symlink = getattr(os, 'symlink', None)  # os.symlink may not exist on all platforms
            # self.original_import = _TRUE_BUILTIN_IMPORT # Use module-level for consistency

            self.whitelisted_directories = []
            self.whitelisted_files = set()
            self.whitelisted_modules = set()
            self.allow_network = False
            self._import_guard = threading.local()
            # thread-local structure to allow temporary user-initiated overrides
            self._user_override = threading.local()
            self._initialized = True
            logger.debug("RestrictOSAccess initialized.")

    def restricted_import(
        self, name, globals=None, locals=None, fromlist=(), level=0
    ):
        # This method is currently not patched onto builtins.__import__
        # logger.debug(f"restricted_import called: name={name}, fromlist={fromlist}, level={level} - (Currently not enforcing import restrictions)")
        # Add import restriction logic here if re-enabled.
        # For now, directly use the true import.
        return _TRUE_BUILTIN_IMPORT(name, globals, locals, fromlist, level)

    def activate(
        self,
        whitelisted_directories=None,
        whitelisted_modules=None,
        allow_network=False,
    ):
        logger.debug(
            f"RestrictOSAccess.activate called. Current sys._airunner_os_restriction_activated: {getattr(sys, '_airunner_os_restriction_activated', False)}"
        )
        logger.debug(
            f"Provided whitelisted_directories: {whitelisted_directories}"
        )
        logger.debug(f"Provided whitelisted_modules: {whitelisted_modules}")
        logger.debug(f"Provided allow_network: {allow_network}")

        # Update whitelists regardless of prior activation state.
        self.whitelisted_directories = (
            [
                os.path.abspath(os.path.normpath(d))
                for d in whitelisted_directories
            ]
            if whitelisted_directories
            else []
        )
        self.whitelisted_modules = (
            set(whitelisted_modules) if whitelisted_modules else set()
        )
        self.allow_network = allow_network
        logger.debug(
            f"Set self.whitelisted_directories to: {self.whitelisted_directories}"
        )
        logger.debug(
            f"Set self.whitelisted_modules to: {self.whitelisted_modules}"
        )
        logger.debug(f"Set self.allow_network to: {self.allow_network}")

        if (
            hasattr(sys, "_airunner_os_restriction_activated")
            and sys._airunner_os_restriction_activated
        ):
            logger.warning(
                "OS restriction was already activated. Whitelists and settings have been updated."
            )
            return

        logger.info("Activating OS access restrictions.")
        builtins.open = self.restricted_open
        os.write = self.restricted_os_write
        os.makedirs = self.restricted_makedirs
        os.mkdir = self.restricted_mkdir  # Patch os.mkdir
        os.remove = self.restricted_remove  # Patch os.remove
        os.rmdir = self.restricted_rmdir  # Patch os.rmdir
        os.unlink = self.restricted_unlink  # Patch os.unlink (alias for remove)
        os.rename = self.restricted_rename  # Patch os.rename
        os.replace = self.restricted_replace  # Patch os.replace
        # Patch os.link and os.symlink if they exist on this platform
        if self.original_link is not None:
            os.link = self.restricted_link
        if self.original_symlink is not None:
            os.symlink = self.restricted_symlink

        # builtins.__import__ = self.restricted_import # Patching import is DISABLED
        # logger.info("Import restriction patching is currently DISABLED.")

        sys._airunner_os_restriction_activated = True
        logger.info("OS access restrictions activated.")

    def deactivate(self):
        if (
            not hasattr(sys, "_airunner_os_restriction_activated")
            or not sys._airunner_os_restriction_activated
        ):
            logger.debug("OS restriction not active, no need to deactivate.")
            return

        logger.info("Deactivating OS access restrictions.")
        builtins.open = self.original_open
        os.write = self.original_os_write
        os.makedirs = self.original_makedirs
        os.mkdir = self.original_mkdir  # Restore os.mkdir
        os.remove = self.original_remove  # Restore os.remove
        os.rmdir = self.original_rmdir  # Restore os.rmdir
        os.unlink = self.original_unlink  # Restore os.unlink
        os.rename = self.original_rename  # Restore os.rename
        os.replace = self.original_replace  # Restore os.replace
        # Restore os.link and os.symlink if they exist
        if self.original_link is not None:
            os.link = self.original_link
        if self.original_symlink is not None:
            os.symlink = self.original_symlink

        # if builtins.__import__ == self.restricted_import: # Only restore if we patched it
        #    builtins.__import__ = _TRUE_BUILTIN_IMPORT # Restore true import
        # logger.info("Import restrictions deactivated (if they were enabled).")

        del sys._airunner_os_restriction_activated
        logger.info("OS access restrictions deactivated.")

    def is_path_whitelisted(self, file_path: str) -> bool:
        logger.debug(f"is_path_whitelisted: Checking file path '{file_path}'")
        if not file_path:
            logger.warning(
                "is_path_whitelisted called with empty or None file_path."
            )
            return False
        abs_file_path = os.path.abspath(os.path.normpath(file_path))
        directory = os.path.dirname(abs_file_path)
        logger.debug(
            f"is_path_whitelisted: Checking directory '{directory}' for file '{abs_file_path}'"
        )
        return self.is_directory_whitelisted(directory)

    def is_directory_whitelisted(self, directory_path: str) -> bool:
        if not directory_path:  # Check for None or empty string
            logger.warning(
                "is_directory_whitelisted called with empty or None directory_path."
            )
            return False

        abs_path_to_check = os.path.abspath(os.path.normpath(directory_path))
        logger.debug(
            f"is_directory_whitelisted: Checking absolute path '{abs_path_to_check}'"
        )
        logger.debug(f"Current whitelist: {self.whitelisted_directories}")

        for whitelisted_dir_processed in self.whitelisted_directories:
            # whitelisted_dir_processed is already abspath'd and normpath'd during activate()
            logger.debug(
                f"Comparing '{abs_path_to_check}' with whitelisted_dir '{whitelisted_dir_processed}'"
            )

            if abs_path_to_check == whitelisted_dir_processed:
                logger.debug(
                    f"Exact match: '{abs_path_to_check}' is whitelisted."
                )
                return True

            # Check if abs_path_to_check is a subdirectory of whitelisted_dir_processed
            # Ensure whitelisted_dir_processed ends with a separator for correct prefix check,
            # unless it's the root directory itself.
            if (
                whitelisted_dir_processed == os.sep
            ):  # Whitelisted directory is the root '/'
                # Any absolute path starts with root. This effectively whitelists everything if '/' is given.
                if abs_path_to_check.startswith(
                    whitelisted_dir_processed
                ):  # Should always be true for absolute paths
                    logger.debug(
                        f"Path '{abs_path_to_check}' is whitelisted via root '{whitelisted_dir_processed}'."
                    )
                    return True
            elif abs_path_to_check.startswith(
                whitelisted_dir_processed + os.sep
            ):
                logger.debug(
                    f"Path '{abs_path_to_check}' is whitelisted as subdirectory of '{whitelisted_dir_processed}'."
                )
                return True

        logger.debug(
            f"Path '{abs_path_to_check}' is NOT whitelisted after checking all rules."
        )
        return False

    def is_file_operation_allowed(self, path: str, operation: str) -> bool:
        logger.debug(
            f"is_file_operation_allowed: Checking file operation '{operation}' for path '{path}'"
        )
        if not path:
            logger.warning(
                "is_file_operation_allowed called with empty or None path."
            )
            return False
        abs_path = os.path.abspath(os.path.normpath(path))
        logger.debug(
            f"is_file_operation_allowed: Normalized absolute path '{abs_path}'"
        )

        # For now, allow all operations if the path is whitelisted.
        # This should be refined based on specific operation requirements.
        # First, check for a temporary user override on this thread.
        try:
            if getattr(self._user_override, "allow_any", False):
                logger.debug(
                    "is_file_operation_allowed: thread-local user override 'allow_any' is set. Allowing operation."
                )
                return True
            allowed_paths = getattr(self._user_override, "allowed_paths", None)
            if allowed_paths:
                for p in allowed_paths:
                    # allow if the file is exactly the allowed path or under an allowed directory
                    if abs_path == p or abs_path.startswith(p + os.sep):
                        logger.debug(
                            "is_file_operation_allowed: path '%s' is allowed by thread-local override.",
                            abs_path,
                        )
                        return True
        except Exception:
            # Any issue with override checking should fall back to whitelist behavior.
            logger.exception(
                "Error while checking thread-local user override. Falling back to whitelist."
            )

        allowed = self.is_path_whitelisted(abs_path)
        logger.debug(
            f"is_file_operation_allowed: Path '{abs_path}' whitelisted: {allowed}"
        )
        return allowed

    def clear_whitelists(self) -> None:
        """Clears all whitelists."""
        logger.debug("Clearing whitelists.")
        self.whitelisted_directories.clear()
        self.whitelisted_files.clear()
        self.whitelisted_modules.clear()

    def restricted_open(
        self,
        file,
        mode="r",
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
    ):
        logger.debug(
            f"restricted_open called for file: '{file}', mode: '{mode}'"
        )

        file_path_str = None
        if isinstance(file, int):  # File descriptor
            logger.debug(
                f"Allowing open for already opened file descriptor: {file}"
            )
            return self.original_open(
                file,
                mode,
                buffering,
                encoding,
                errors,
                newline,
                closefd,
                opener,
            )
        elif isinstance(file, bytes):
            try:
                file_path_str = os.fsdecode(file)
                logger.debug(f"Decoded bytes path for open: '{file_path_str}'")
            except Exception as e:
                logger.error(
                    f"Cannot decode bytes path for open: {file}. Error: {e}. Denying access."
                )
                raise PermissionError(
                    f"File system open operation with non-decodable bytes path '{file!r}' is not allowed."
                ) from e
        else:
            file_path_str = str(file)

        abs_file_path = os.path.abspath(os.path.normpath(file_path_str))
        logger.debug(
            f"Checking whitelist for absolute file path: '{abs_file_path}' (original: '{file_path_str}')"
        )

        # Check for thread-local user override first (allows explicit user actions)
        try:
            if getattr(self._user_override, "allow_any", False):
                logger.info(
                    f"Thread-local override 'allow_any' set. Allowing open for '{abs_file_path}'."
                )
                return self.original_open(
                    file,
                    mode,
                    buffering,
                    encoding,
                    errors,
                    newline,
                    closefd,
                    opener,
                )
            allowed_paths = getattr(self._user_override, "allowed_paths", None)
            if allowed_paths:
                for p in allowed_paths:
                    if abs_file_path == p or abs_file_path.startswith(
                        p + os.sep
                    ):
                        logger.info(
                            f"Thread-local override allows open for '{abs_file_path}' via allowed_paths."
                        )
                        return self.original_open(
                            file,
                            mode,
                            buffering,
                            encoding,
                            errors,
                            newline,
                            closefd,
                            opener,
                        )
        except Exception:
            logger.exception(
                "Error while checking thread-local user override in restricted_open. Falling back to whitelist check."
            )

        if self.is_path_whitelisted(abs_file_path):
            logger.info(
                f"Path '{abs_file_path}' is whitelisted for open. Proceeding."
            )
            return self.original_open(
                file,
                mode,
                buffering,
                encoding,
                errors,
                newline,
                closefd,
                opener,
            )
        else:
            logger.error(
                f"File system open operation to '{abs_file_path}' (from original path '{file}') is not allowed."
            )
            raise PermissionError(
                f"File system open operation to '{abs_file_path}' (from original path '{file}') is not allowed."
            )

    from contextlib import contextmanager

    @contextmanager
    def user_override(self, paths=None, allow_any: bool = False):
        """Context manager to temporarily allow file operations on the current thread.

        - paths: optional iterable of file or directory paths to allow (they will be normalized to absolute paths).
        - allow_any: if True, allows any file operation on this thread for the duration of the context. Use sparingly.

        Example:
            with RestrictOSAccess().user_override(paths=["/tmp/workspace"]):
                open('/tmp/workspace/file.png', 'rb')  # allowed inside context

        This operates per-thread using thread-local storage to avoid broad process-wide disabling.
        """
        # Normalize inputs
        saved_allow_any = getattr(self._user_override, "allow_any", False)
        saved_allowed_paths = getattr(
            self._user_override, "allowed_paths", None
        )
        try:
            self._user_override.allow_any = bool(allow_any)
            if paths:
                processed = []
                for p in paths:
                    try:
                        processed.append(
                            os.path.abspath(os.path.normpath(str(p)))
                        )
                    except Exception:
                        logger.exception(
                            "Failed to normalize path for user_override: %s", p
                        )
                self._user_override.allowed_paths = processed
            else:
                # ensure attribute exists but is falsy
                self._user_override.allowed_paths = None
            yield
        finally:
            # Restore previous state
            try:
                self._user_override.allow_any = saved_allow_any
                if saved_allowed_paths is None:
                    if hasattr(self._user_override, "allowed_paths"):
                        delattr(self._user_override, "allowed_paths")
                else:
                    self._user_override.allowed_paths = saved_allowed_paths
            except Exception:
                # Best-effort cleanup; don't raise from cleanup path
                logger.exception(
                    "Error while restoring thread-local user override state."
                )

    def restricted_os_write(self, fd, data):
        # This operates on file descriptors. Mapping fd to path is non-trivial.
        # Assumption: if fd was obtained via a whitelisted open, write is okay.
        # This is a known simplification.
        logger.debug(
            f"restricted_os_write called for fd: {fd}. Allowing by default (relies on secure open)."
        )
        return self.original_os_write(fd, data)

    def restricted_makedirs(self, name, mode=0o777, exist_ok=False):
        logger.debug(
            f"restricted_makedirs called for path: '{name}', mode: {oct(mode)}, exist_ok: {exist_ok}"
        )
        abs_target_path = os.path.abspath(os.path.normpath(name))
        logger.debug(
            f"Normalized absolute target path for makedirs: '{abs_target_path}'"
        )

        # Handle exist_ok=True: if path exists and is a dir
        if exist_ok and os.path.exists(abs_target_path):
            if os.path.isdir(abs_target_path):
                logger.debug(
                    f"Path '{abs_target_path}' exists and is a directory."
                )
                if self.is_directory_whitelisted(abs_target_path):
                    logger.info(
                        f"Makedirs: Path '{abs_target_path}' exists, is whitelisted, and exist_ok=True. No operation needed."
                    )
                    return None
                else:
                    logger.error(
                        f"Makedirs: Path '{abs_target_path}' exists and exist_ok=True, but it's NOT whitelisted. Denying."
                    )
                    raise PermissionError(
                        f"File system makedirs operation on existing but non-whitelisted path '{abs_target_path}' is not allowed (exist_ok=True)."
                    )
            else:  # Path exists but is not a directory
                # This case would typically cause os.makedirs to raise FileExistsError.
                # We check whitelist status first. If not whitelisted, deny.
                # If whitelisted, let original_makedirs raise the FileExistsError.
                logger.warning(
                    f"Makedirs: Path '{abs_target_path}' exists but is not a directory. Original os.makedirs would likely error."
                )
                if not self.is_directory_whitelisted(
                    abs_target_path
                ):  # Check if the location is permissible for creation
                    logger.error(
                        f"Makedirs: Path '{abs_target_path}' (existing non-directory) is also not in a whitelisted location. Denying."
                    )
                    raise PermissionError(
                        f"File system makedirs operation on '{abs_target_path}' (existing non-directory) is not allowed as its location is not whitelisted."
                    )
                logger.debug(
                    f"Makedirs: Path '{abs_target_path}' (existing non-directory) is in a whitelisted location. Letting original_makedirs handle."
                )
                # Fall through to call original_makedirs, which will raise FileExistsError.

        # If path doesn't exist, or exist_ok=False (original will handle error if it exists)
        # we must check if the operation is permissible based on whitelist.
        # is_directory_whitelisted checks if abs_target_path itself or any of its parents are whitelisted.
        if self.is_directory_whitelisted(abs_target_path):
            logger.info(
                f"Makedirs: Path '{abs_target_path}' is whitelisted for creation. Calling original os.makedirs."
            )
            try:
                return self.original_makedirs(name, mode, exist_ok=exist_ok)
            except Exception as e:
                logger.error(
                    f"Original os.makedirs failed for '{name}': {type(e).__name__} - {e}"
                )
                raise  # Re-raise the original error
        else:
            logger.error(
                f"Makedirs: Path '{abs_target_path}' is NOT whitelisted for creation. Denying operation."
            )
            raise PermissionError(
                f"File system makedirs operation to '{abs_target_path}' is not allowed."
            )

    def restricted_mkdir(self, path, mode=0o777, *, dir_fd=None):
        logger.debug(
            f"restricted_mkdir called for path: '{path}', mode: {oct(mode)}, dir_fd: {dir_fd}"
        )

        # Handling dir_fd correctly for security is complex.
        # If path is relative, its absolute resolution depends on dir_fd's actual directory.
        # os.path.abspath(path) might not be correct if dir_fd is used and path is relative.
        # For now, we log a warning and proceed with os.path.abspath, which assumes CWD for relative paths if dir_fd is not None.
        # This is a limitation for dir_fd usage.
        if dir_fd is not None:
            logger.warning(
                f"restricted_mkdir with dir_fd: Whitelist check for path '{path}' will use os.path.abspath, which may not correctly resolve relative paths against dir_fd. This scenario is not fully secured by the current whitelist logic if 'path' is relative."
            )
            # A truly robust solution would need to get the absolute path of dir_fd and join.
            # This is OS-specific and non-trivial (e.g. os.readlink(f"/proc/self/fd/{dir_fd}") on Linux).

        abs_target_path = os.path.abspath(os.path.normpath(path))
        logger.debug(
            f"Normalized absolute target path for mkdir: '{abs_target_path}'"
        )

        # is_directory_whitelisted checks if abs_target_path is itself whitelisted OR is a child of a whitelisted directory.
        # This is sufficient for mkdir, as it creates the final directory component.
        if self.is_directory_whitelisted(abs_target_path):
            logger.info(
                f"Mkdir: Path '{abs_target_path}' is whitelisted. Calling original os.mkdir."
            )
            try:
                # Pass dir_fd explicitly as it's a keyword-only argument
                return self.original_mkdir(path, mode, dir_fd=dir_fd)
            except FileExistsError as e:
                # FileExistsError is expected when Path.mkdir(exist_ok=True) is used
                logger.debug(
                    f"Original os.mkdir for '{path}': Directory already exists (expected with exist_ok=True)"
                )
                raise  # Re-raise for Path.mkdir to handle
            except Exception as e:
                logger.error(
                    f"Original os.mkdir failed for '{path}': {type(e).__name__} - {e}"
                )
                raise  # Re-raise the original error
        else:
            logger.error(
                f"Mkdir: Path '{abs_target_path}' is NOT whitelisted. Denying operation."
            )
            raise PermissionError(
                f"File system mkdir operation to '{abs_target_path}' is not allowed."
            )

    def restricted_remove(self, path, *, dir_fd=None):
        logger.debug(
            f"restricted_remove called for path: '{path}', dir_fd: {dir_fd}"
        )
        # Similar to mkdir, dir_fd makes absolute path resolution complex if path is relative.
        if dir_fd is not None:
            logger.warning(
                f"restricted_remove with dir_fd: Whitelist check for path '{path}' will use os.path.abspath. This scenario is not fully secured if 'path' is relative."
            )

        abs_target_path = os.path.abspath(os.path.normpath(path))
        logger.debug(
            f"Normalized absolute target path for remove: '{abs_target_path}'"
        )

        # is_path_whitelisted checks the directory of the file.
        # For removing a file, the file itself (or its containing directory) must be in a whitelisted location.
        if self.is_path_whitelisted(abs_target_path):
            logger.info(
                f"Remove: Path '{abs_target_path}' is whitelisted for removal. Calling original os.remove."
            )
            try:
                return self.original_remove(path, dir_fd=dir_fd)
            except Exception as e:
                logger.error(
                    f"Original os.remove failed for '{path}': {type(e).__name__} - {e}"
                )
                raise
        else:
            logger.error(
                f"Remove: Path '{abs_target_path}' is NOT whitelisted for removal. Denying operation."
            )
            raise PermissionError(
                f"File system remove operation on '{abs_target_path}' is not allowed."
            )

    def restricted_rmdir(self, path, *, dir_fd=None):
        logger.debug(
            f"restricted_rmdir called for path: '{path}', dir_fd: {dir_fd}"
        )
        if dir_fd is not None:
            logger.warning(
                f"restricted_rmdir with dir_fd: Whitelist check for path '{path}' will use os.path.abspath. This scenario is not fully secured if 'path' is relative."
            )

        abs_target_path = os.path.abspath(os.path.normpath(path))
        logger.debug(
            f"Normalized absolute target path for rmdir: '{abs_target_path}'"
        )

        # For rmdir, the directory being removed must be whitelisted (or be a subdir of a whitelisted one).
        if self.is_directory_whitelisted(abs_target_path):
            logger.info(
                f"Rmdir: Path '{abs_target_path}' is whitelisted for removal. Calling original os.rmdir."
            )
            try:
                return self.original_rmdir(path, dir_fd=dir_fd)
            except Exception as e:
                logger.error(
                    f"Original os.rmdir failed for '{path}': {type(e).__name__} - {e}"
                )
                raise
        else:
            logger.error(
                f"Rmdir: Path '{abs_target_path}' is NOT whitelisted for removal. Denying operation."
            )
            raise PermissionError(
                f"File system rmdir operation on '{abs_target_path}' is not allowed."
            )

    def restricted_unlink(self, path, *, dir_fd=None):
        """Restricted os.unlink - alias for os.remove with same security checks."""
        logger.debug(
            f"restricted_unlink called for path: '{path}', dir_fd: {dir_fd}"
        )
        # os.unlink is functionally identical to os.remove
        return self.restricted_remove(path, dir_fd=dir_fd)

    def restricted_rename(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        """Restricted os.rename - both source and destination must be whitelisted."""
        logger.debug(
            f"restricted_rename called: src='{src}', dst='{dst}'"
        )
        if src_dir_fd is not None or dst_dir_fd is not None:
            logger.warning(
                f"restricted_rename with dir_fd: Whitelist check may not correctly resolve relative paths."
            )

        abs_src = os.path.abspath(os.path.normpath(src))
        abs_dst = os.path.abspath(os.path.normpath(dst))
        
        # Both source and destination must be in whitelisted directories
        src_allowed = self.is_path_whitelisted(abs_src)
        dst_allowed = self.is_path_whitelisted(abs_dst)
        
        if src_allowed and dst_allowed:
            logger.info(
                f"Rename: Both '{abs_src}' and '{abs_dst}' are whitelisted. Calling original os.rename."
            )
            try:
                return self.original_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
            except Exception as e:
                logger.error(
                    f"Original os.rename failed: {type(e).__name__} - {e}"
                )
                raise
        else:
            if not src_allowed:
                logger.error(f"Rename: Source path '{abs_src}' is NOT whitelisted.")
            if not dst_allowed:
                logger.error(f"Rename: Destination path '{abs_dst}' is NOT whitelisted.")
            raise PermissionError(
                f"File system rename operation from '{abs_src}' to '{abs_dst}' is not allowed."
            )

    def restricted_replace(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        """Restricted os.replace - both source and destination must be whitelisted."""
        logger.debug(
            f"restricted_replace called: src='{src}', dst='{dst}'"
        )
        if src_dir_fd is not None or dst_dir_fd is not None:
            logger.warning(
                f"restricted_replace with dir_fd: Whitelist check may not correctly resolve relative paths."
            )

        abs_src = os.path.abspath(os.path.normpath(src))
        abs_dst = os.path.abspath(os.path.normpath(dst))
        
        # Both source and destination must be in whitelisted directories
        src_allowed = self.is_path_whitelisted(abs_src)
        dst_allowed = self.is_path_whitelisted(abs_dst)
        
        if src_allowed and dst_allowed:
            logger.info(
                f"Replace: Both '{abs_src}' and '{abs_dst}' are whitelisted. Calling original os.replace."
            )
            try:
                return self.original_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
            except Exception as e:
                logger.error(
                    f"Original os.replace failed: {type(e).__name__} - {e}"
                )
                raise
        else:
            if not src_allowed:
                logger.error(f"Replace: Source path '{abs_src}' is NOT whitelisted.")
            if not dst_allowed:
                logger.error(f"Replace: Destination path '{abs_dst}' is NOT whitelisted.")
            raise PermissionError(
                f"File system replace operation from '{abs_src}' to '{abs_dst}' is not allowed."
            )

    def restricted_link(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
        """Restricted os.link - both source and destination must be whitelisted.
        
        Hard links can be security risks as they can create additional references
        to sensitive files. Both source and destination are strictly checked.
        """
        logger.debug(
            f"restricted_link called: src='{src}', dst='{dst}'"
        )
        if src_dir_fd is not None or dst_dir_fd is not None:
            logger.warning(
                f"restricted_link with dir_fd: Whitelist check may not correctly resolve relative paths."
            )

        abs_src = os.path.abspath(os.path.normpath(src))
        abs_dst = os.path.abspath(os.path.normpath(dst))
        
        # Both source and destination must be in whitelisted directories
        src_allowed = self.is_path_whitelisted(abs_src)
        dst_allowed = self.is_path_whitelisted(abs_dst)
        
        if src_allowed and dst_allowed:
            logger.info(
                f"Link: Both '{abs_src}' and '{abs_dst}' are whitelisted. Calling original os.link."
            )
            try:
                return self.original_link(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks)
            except Exception as e:
                logger.error(
                    f"Original os.link failed: {type(e).__name__} - {e}"
                )
                raise
        else:
            if not src_allowed:
                logger.error(f"Link: Source path '{abs_src}' is NOT whitelisted.")
            if not dst_allowed:
                logger.error(f"Link: Destination path '{abs_dst}' is NOT whitelisted.")
            raise PermissionError(
                f"File system hard link operation from '{abs_src}' to '{abs_dst}' is not allowed."
            )

    def restricted_symlink(self, src, dst, target_is_directory=False, *, dir_fd=None):
        """Restricted os.symlink - destination must be whitelisted.
        
        Symlinks can be security risks as they can point to arbitrary locations.
        The destination (where the symlink is created) must be in a whitelisted directory.
        Note: We don't restrict where the symlink points to (src) because symlinks
        often need to point to system libraries or other locations.
        """
        logger.debug(
            f"restricted_symlink called: src='{src}', dst='{dst}'"
        )
        if dir_fd is not None:
            logger.warning(
                f"restricted_symlink with dir_fd: Whitelist check may not correctly resolve relative paths."
            )

        abs_dst = os.path.abspath(os.path.normpath(dst))
        
        # Destination (where symlink is created) must be in a whitelisted directory
        if self.is_path_whitelisted(abs_dst):
            logger.info(
                f"Symlink: Destination '{abs_dst}' is whitelisted. Calling original os.symlink."
            )
            try:
                return self.original_symlink(src, dst, target_is_directory=target_is_directory, dir_fd=dir_fd)
            except Exception as e:
                logger.error(
                    f"Original os.symlink failed: {type(e).__name__} - {e}"
                )
                raise
        else:
            logger.error(
                f"Symlink: Destination path '{abs_dst}' is NOT whitelisted for symlink creation."
            )
            raise PermissionError(
                f"File system symlink creation at '{abs_dst}' is not allowed."
            )


# Ensure the logger for this module is configured if not done globally
if not logger.hasHandlers():
    handler = logging.StreamHandler(
        sys.stderr
    )  # Or your preferred stream/file
    # Be cautious with log level in production for security modules
    # For debugging, DEBUG is fine. For production, INFO or WARNING.
    # level = logging.DEBUG if os.environ.get("AIRUNNER_DEBUG") else logging.INFO
    level = logging.DEBUG  # Set to DEBUG for this troubleshooting phase
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)  # Set level on logger itself too
    logger.propagate = (
        False  # Avoid duplicate logs if root logger is also configured
    )
