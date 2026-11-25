#!/usr/bin/env python3
import ctypes
import json
import uuid
from ctypes import byref, c_char, c_int, c_size_t

lib = ctypes.CDLL("libcuda.so.1")
def call(name, *args):
    rc = getattr(lib, name)(*args)
    if rc:
        raise RuntimeError(f"{name} returned CUDA driver error {rc}")

call("cuInit", 0)
count = c_int()
call("cuDeviceGetCount", byref(count))
devices = []
for ordinal in range(count.value):
    device = c_int()
    call("cuDeviceGet", byref(device), ordinal)
    raw_uuid = (ctypes.c_ubyte * 16)()
    call("cuDeviceGetUuid_v2", byref(raw_uuid), device)
    name = (c_char * 128)()
    call("cuDeviceGetName", name, len(name), device)
    memory = c_size_t()
    call("cuDeviceTotalMem_v2", byref(memory), device)
    major, minor = c_int(), c_int()
    call("cuDeviceGetAttribute", byref(major), 75, device)
    call("cuDeviceGetAttribute", byref(minor), 76, device)
    devices.append(dict(ordinal=ordinal, uuid="GPU-"+str(uuid.UUID(bytes=bytes(raw_uuid))),
                        name=name.value.decode(), memory_bytes=memory.value,
                        capability=f"{major.value}.{minor.value}"))
print(json.dumps(devices, indent=2))
