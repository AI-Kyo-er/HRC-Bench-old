#!/usr/bin/env python3
"""查询EGL设备的CUDA PCI地址；不创建GL/CUDA计算上下文。"""
import ctypes as c
import json


def main():
    egl=c.CDLL('libEGL.so.1')
    egl.eglGetProcAddress.restype=c.c_void_p
    devices_fn=c.CFUNCTYPE(c.c_uint,c.c_int,c.POINTER(c.c_void_p),c.POINTER(c.c_int))(
        egl.eglGetProcAddress(b'eglQueryDevicesEXT'))
    attribute_fn=c.CFUNCTYPE(c.c_uint,c.c_void_p,c.c_int,c.POINTER(c.c_ssize_t))(
        egl.eglGetProcAddress(b'eglQueryDeviceAttribEXT'))
    cuda=c.CDLL('libcuda.so.1')
    if cuda.cuInit(0)!=0:raise RuntimeError('无法查询CUDA设备PCI地址')
    devices=(c.c_void_p*64)();count=c.c_int()
    if not devices_fn(64,devices,c.byref(count)):raise RuntimeError('无法枚举EGL设备')
    result=[]
    for index in range(count.value):
        ordinal=c.c_ssize_t(-1)
        if not attribute_fn(devices[index],0x323A,c.byref(ordinal)):continue
        bus=c.create_string_buffer(32)
        if cuda.cuDeviceGetPCIBusId(bus,32,ordinal.value)!=0:raise RuntimeError('无法对应EGL与CUDA设备')
        result.append({'egl_ordinal':index,'cuda_ordinal':ordinal.value,'pci_bus':bus.value.decode().lower()})
    print(json.dumps(result))


if __name__=='__main__':main()
