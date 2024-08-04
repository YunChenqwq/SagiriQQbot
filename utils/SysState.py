import os
import psutil

def get_system_status():
    # 收集系统信息
    core_mem = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)  # 进程内存占用 (MB)
    sysmem_info = psutil.virtual_memory()  # 系统内存信息
    cpu_info = psutil.cpu_times()  # CPU时间信息
    disk_info = psutil.disk_usage('/')  # 磁盘使用信息
    cpu_freq = psutil.cpu_freq()  # CPU频率信息

    # 获取 CPU 使用率
    cpu_percent = psutil.cpu_percent(interval=1)

    # 格式化输出结果
    res = f"""
    ====系统状态====
进程内存占用: {core_mem:.2f}MB
总内存: {sysmem_info.total / (1024 * 1024):.2f}MB
已用内存: {sysmem_info.used / (1024 * 1024):.2f}MB
空闲内存: {sysmem_info.free / (1024 * 1024):.2f}MB
内存使用率: {sysmem_info.percent:.2f}%
用户态CPU时间: {cpu_info.user:.2f}秒
系统态CPU时间: {cpu_info.system:.2f}秒
空闲CPU时间: {cpu_info.idle:.2f}秒
CPU使用率: {cpu_percent:.2f}%
CPU逻辑核心数: {psutil.cpu_count()}
CPU物理核心数: {psutil.cpu_count(logical=False)}
CPU当前频率: {cpu_freq.current:.2f}MHz
总磁盘空间: {disk_info.total / (1024 * 1024 * 1024):.2f}GB
已用磁盘空间: {disk_info.used / (1024 * 1024 * 1024):.2f}GB
空闲磁盘空间: {disk_info.free / (1024 * 1024 * 1024):.2f}GB
磁盘使用率: {disk_info.percent:.2f}%
============"""

    return res.strip()
