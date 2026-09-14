"""Windows reads anchored to directory handles; never fall back to path rechecks.

NtCreateFile's RootDirectory opens exactly one child of an already opened
directory. Each component rejects reparse points, including directory junctions.
The returned CRT descriptor owns the native handle and is used for the read.
"""

import ctypes
import os
import stat
from contextlib import contextmanager
from ctypes import wintypes
from functools import lru_cache

from .errors import SourceError


class UnicodeString(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT),
                ("Buffer", wintypes.LPWSTR)]


class ObjectAttributes(ctypes.Structure):
    _fields_ = [("Length", wintypes.ULONG), ("RootDirectory", wintypes.HANDLE),
                ("ObjectName", ctypes.POINTER(UnicodeString)), ("Attributes", wintypes.ULONG),
                ("SecurityDescriptor", ctypes.c_void_p), ("SecurityQualityOfService", ctypes.c_void_p)]


class IOStatusBlock(ctypes.Structure):
    _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]


@lru_cache(maxsize=1)
def _api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    native = ctypes.WinDLL("ntdll")
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    native.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.ULONG,
        ctypes.POINTER(ObjectAttributes), ctypes.POINTER(IOStatusBlock), ctypes.c_void_p,
        wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG]
    native.NtCreateFile.restype = wintypes.LONG
    native.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
    native.RtlNtStatusToDosError.restype = wintypes.ULONG
    return kernel, native


def _descriptor(handle):
    import msvcrt

    try:
        return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        _api()[0].CloseHandle(handle)
        raise


def _open_root(root):
    kernel, _ = _api()
    # FILE_TRAVERSE | FILE_READ_ATTRIBUTES | SYNCHRONIZE, all share modes,
    # OPEN_EXISTING, BACKUP_SEMANTICS | OPEN_REPARSE_POINT. Identity is checked
    # on this opened object, not on the path that led to it.
    handle = kernel.CreateFileW(str(root), 0x1000A0, 7, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    return _descriptor(handle)


def _open_child(parent_fd, name, directory):
    import msvcrt

    _, native = _api()
    buffer = ctypes.create_unicode_buffer(name)
    length = len(name.encode("utf-16-le"))
    text = UnicodeString(length, length + 2, ctypes.cast(buffer, wintypes.LPWSTR))
    # OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE; RootDirectory is the held handle.
    attrs = ObjectAttributes(ctypes.sizeof(ObjectAttributes), msvcrt.get_osfhandle(parent_fd),
                             ctypes.pointer(text), 0x1040, None, None)
    result, status_block = wintypes.HANDLE(), IOStatusBlock()
    access = 0x1000A0 if directory else 0x100081  # traverse/read data, attributes, synchronize
    options = 0x200020 | (1 if directory else 0x40)  # no reparse, synchronous, dir/non-dir
    status = native.NtCreateFile(ctypes.byref(result), access, ctypes.byref(attrs),
        ctypes.byref(status_block), None, 0, 7, 1, options, None, 0)  # FILE_OPEN only
    if status < 0:
        raise ctypes.WinError(native.RtlNtStatusToDosError(status))
    return _descriptor(result.value)


def _check_directory(fd):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_file_attributes & 0x400:
        raise SourceError("AUTH_REQUIRED", "local", "源码目录包含不允许的重解析点。", 403)
    return info


@contextmanager
def open_authorized(root, parts, identity):
    descriptors = []
    try:
        current = _open_root(root)
        descriptors.append(current)
        info = _check_directory(current)
        if (info.st_dev, info.st_ino) != identity:
            raise SourceError("AUTH_REQUIRED", "local", "授权根目录已被替换。", 403)
        for part in parts[:-1]:
            current = _open_child(current, part, True)
            descriptors.append(current)
            _check_directory(current)
        final = _open_child(current, parts[-1], False)
        descriptors.append(final)
        if os.fstat(final).st_file_attributes & 0x400:
            raise SourceError("AUTH_REQUIRED", "local", "源码文件包含不允许的重解析点。", 403)
        yield final
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
