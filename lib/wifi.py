# 导入必要的库
import network
import time


def connect_wifi(WIFI_SSID, WIFI_PASSWORD):
    """
    连接 Wi-Fi 网络
    返回: 
        wlan 对象 (连接成功)
        None (连接失败)
    """
    # 创建 WLAN 对象（STA 模式）
    wlan = network.WLAN(network.STA_IF)

    # 如果当前已连接，先断开
    if wlan.isconnected():
        print("已连接，正在断开...")
        wlan.disconnect()
        time.sleep(1)

    # 激活接口
    wlan.active(True)

    # 开始连接
    print(f"正在连接: {WIFI_SSID}")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # 等待连接结果（最多等待100秒）
    max_wait = 100
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print("等待连接...", max_wait)
        time.sleep(1)

    # 检查最终连接状态
    if wlan.isconnected():
        print("连接成功!")
        print("网络配置:", wlan.ifconfig())
        return wlan
    else:
        print("连接失败!")
        wlan.active(False)
        return None
