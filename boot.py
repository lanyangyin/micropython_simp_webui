# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
import network

# from lib.wifi import connect_wifi
#
# # 配置 Wi-Fi 账号密码
# WIFI_SSID = "cce"
# WIFI_PASSWORD = "335zou335"
#
# # 执行连接wifi
# wifi = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
# if wifi:
#     # 在此处添加其他需要网络的操作
#     pass
# else:
#     # 处理连接失败的情况
#     print("请检查 Wi-Fi 配置或信号强度")

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='ESP-AP', password='00000000', authmode=3)
print("网络配置:", ap.ifconfig())
