import threading
import logging
import os
import socket
import sys


class InterceptHandler(logging.Handler):
    def __init__(
        self,
        shadow_logger,
        show_stdout: bool = True,
        hook: callable = lambda x: None
    ):
        """
        InterceptHandler intercepts and logs print statements, file operations, and network operations.

        :param shadow_logger:
        :param show_stdout:
        :param hook: A callback function to process log entries.
        """
        super().__init__()
        self.__original_sys_stdout = {
            "displayhook": None,
            "excepthook": None,
            "exc_info": None,
            "exit": None,
            "getdlopenflags": None,
            "getprofile": None,
            "getrefcount": None,
            "getrecursionlimit": None,
            "getsizeof": None,
            "gettrace": None,
            "setdlopenflags": None,
            "setprofile": None,
            "setrecursionlimit": None,
            "settrace": None,
        }
        self.__hook = hook
        self.__original_os_functions = {
            # "path": None,
            # "name": None,
            # "curdir": None,
            # "pardir": None,
            # "sep": None,
            # "extsep": None,
            # "altsep": None,
            # "pathsep": None,
            # "linesep": None,
            # "defpath": None,
            # "devnull": None,
        }
        self.__original_socket_functions = {
            # "socket": None,
            # "socketpair": None,
            # "fromfd": None,
            # "send_fds": None,
            # "recv_fds": None,
            # "fromshare": None,
            # "gethostname": None,
            # "gethostbyname": None,
            # "gethostbyaddr": None,
            # "getservbyname": None,
            # "getprotobyname": None,
            # "ntohs": None,
            # "htons": None,
            # "ntohl": None,
            # "htonl": None,
            # "inet_aton": None,
            # "inet_ntoa,": None,
            # "getdefaulttimeout": None,
            # "setdefaulttimeout": None,
            # "create_connection": None,
        }
        self.shadow_logger = shadow_logger
        self.lock = threading.Lock()
        self.__show_stdout = show_stdout

        with self.lock:
            # Overriding sys.stdout to capture print statements
            sys.stdout = self.LogStream(self.emit_record, show_stdout=self.show_stdout)
            for k, v in self.__original_sys_stdout.items():
                self.__original_sys_stdout[k] = getattr(sys, k, None)
                setattr(sys, k, self.__override_sys_stdout(getattr(sys, k, None)))

            # Overriding file writes
            for k, v in self.__original_os_functions.items():
                self.__original_os_functions[k] = getattr(os, k, None)
                setattr(os, k, self.__override_os_function(getattr(os, k, None)))

            # Overriding network operations
            for k, v in self.__original_socket_functions.items():
                self.__original_socket_functions[k] = getattr(socket, k, None)
                setattr(socket, k, self.__override_socket_function(getattr(socket, k, None)))

    @property
    def show_stdout(self):
        return self.__show_stdout

    @show_stdout.setter
    def show_stdout(self, value):
        self.__show_stdout = value

    def restore_original_functions(self):
        self.__restore_sys_stdout()
        self.__restore_os_functions()
        self.__restore_socket_functions()

    def __restore_sys_stdout(self):
        with self.lock:
            for k, v in self.__original_sys_stdout.items():
                setattr(sys, k, v)

    def __restore_os_functions(self):
        with self.lock:
            for k, v in self.__original_os_functions.items():
                setattr(os, k, v)

    def __restore_socket_functions(self):
        with self.lock:
            for k, v in self.__original_socket_functions.items():
                setattr(socket, k, v)

    def __override_sys_stdout(self, original_function):
        """Override sys.stdout to capture print statements."""

        def custom_stdout(*args, **kwargs):
            with self.lock:
                if original_function:
                    return original_function(*args, **kwargs)

        return custom_stdout

    def __override_os_function(self, original_function):
        """Override os functions to capture file operations."""

        def custom_os_function(*args, **kwargs):
            with self.lock:
                logging.info(f"Performing file operation: {original_function.__name__}")
                return original_function(*args, **kwargs)

        return custom_os_function

    def __override_socket_function(self, original_function):
        """Override socket functions to capture network operations."""

        def custom_socket_function(*args, **kwargs):
            with self.lock:
                logging.info(f"Performing network operation: {original_function.__name__}")
                return original_function(*args, **kwargs)

        return custom_socket_function

    def emit(self, record):
        # Process log record
        self.process_log_record(record)

    def emit_record(self, message, level=logging.INFO):
        # Manually emit log record from captured print statements
        record = self.shadow_logger.makeRecord(self.shadow_logger.name, level, fn='', lno='', msg=message, args=None, exc_info=None)
        self.process_log_record(record)

    def process_log_record(self, record):
        log_entry: str = self.__sanitized_log_entry(record)
        log_info = self.prepare_log_info(record, log_entry)
        if "Shadowlogger" not in log_entry:
            self.shadow_logger.handle_message(log_entry, record.levelno, log_info)
        self.__hook(log_entry)

    def prepare_log_info(self, record, log_entry):
        """Prepare log information dictionary with enhanced details."""
        return {
            'name': record.name,
            'level': record.levelno,
            'message': log_entry,
            'module': record.module,
            'filename': record.filename,
            'lineno': record.lineno,
            'funcName': record.funcName,
            'created': record.created,
            'file_op': record.__dict__.get('file_op'),  # Check for file operation
        }

    def __sanitized_log_entry(self, record: logging.LogRecord) -> str:
        """Sanitize log entries to prevent injection attacks and handle sensitive information."""
        original_entry = self.format(record)
        sanitized_entry = self._sanitize_log_entry(original_entry)
        return sanitized_entry

    @staticmethod
    def _sanitize_log_entry(log_entry: str) -> str:
        """Customizable method to further sanitize log entries."""
        # Default implementation: HTML escape
        return log_entry.replace('<', '&lt;').replace('>', '&gt;')

    def handle(self, record: logging.LogRecord) -> bool:
        """Handle records, potentially logging additional operations."""
        if record.__dict__.get('file_op'):
            os_info = f"{record.__dict__['file_op']} on {record.filename}"
            logging.info(os_info)
        self.emit(record)
        return True

    def override_os_write(self, original_function):
        """Override the os.write function to capture file operations."""

        def custom_write(fd, data):
            with self.lock:
                logging.info(f"Writing to file descriptor {fd}: {data}")
                return original_function(fd, data)

        return custom_write

    def override_socket_send(self, original_function):
        """Override the socket.send function to capture network operations."""

        def custom_send(data, *args, **kwargs):
            with self.lock:
                logging.info(f"Sending data over network: {data}")
                return original_function(data, *args, **kwargs)

        return custom_send

    class LogStream:
        """Stream object to capture print statements and redirect them as log entries."""

        def __init__(self, log_function, show_stdout:bool = True):
            self.log_function = log_function
            self.__show_stdout = show_stdout

        def write(self, message):
            if message.strip() != "":
                self.log_function(message.strip())
                if self.__show_stdout:
                    sys.__stdout__.write((message.strip() + '\n'))

        def flush(self):
            pass


class LogHandler:
    def handle(self, log):
        # Nicely format the log
        formatted_log = f"{log['name']} ({log['module']}:{log['lineno']}) {log['level']}: {log['message']}"
        print(formatted_log)
