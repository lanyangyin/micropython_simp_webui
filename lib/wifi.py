# 导入必要的库
import network
import time

import network
import time


class connect_wifi:
    def __init__(self, WIFI_SSID, WIFI_PASSWORD):
        """
        初始化 WiFi 连接器
        :param WIFI_SSID: WiFi 名称
        :param WIFI_PASSWORD: WiFi 密码
        """
        self.WIFI_SSID = WIFI_SSID
        self.WIFI_PASSWORD = WIFI_PASSWORD
        self.wlan = network.WLAN(network.STA_IF)

        # 连接状态变量（新增）
        self.connection_state = {
            'code': 0,  # 状态代码
            'message': '未初始化',  # 状态描述
            'is_connected': False  # 连接布尔状态
        }
        self._update_state(0, '初始化完成', False)

    def _update_state(self, code, message, is_connected):
        """
        内部方法：更新连接状态
        """
        self.connection_state = {
            'code': code,
            'message': message,
            'is_connected': is_connected
        }

    def connect(self):
        """
        执行 WiFi 连接
        返回:
            wlan 对象 (连接成功)
            None (连接失败)
        """
        try:
            # 如果当前已连接，先断开
            if self.wlan.isconnected():
                print("已连接，正在断开...")
                self._update_state(100, '正在断开旧连接', True)
                self.wlan.disconnect()
                time.sleep(1)

            # 开始连接流程
            self._update_state(200, '开始连接流程', False)
            self.wlan.active(True)

            # 执行连接
            print(f"正在连接: {self.WIFI_SSID}")
            self._update_state(201, f'正在连接 {self.WIFI_SSID}', False)
            self.wlan.connect(self.WIFI_SSID, self.WIFI_PASSWORD)

            # 等待连接结果
            max_wait = 100
            while max_wait > 0:
                if self.wlan.isconnected():
                    break
                max_wait -= 1
                current_msg = f"剩余等待: {max_wait}秒"
                self._update_state(202, current_msg, False)
                print("等待连接...", max_wait)
                time.sleep(1)

            # 处理最终状态
            if self.wlan.isconnected():
                success_msg = f"已连接 {self.WIFI_SSID}"
                print(success_msg)
                self._update_state(300, success_msg, True)
                print("网络配置:", self.wlan.ifconfig())
                return self.wlan
            else:
                raise ConnectionError("连接超时")

        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            print(error_msg)
            self._update_state(400, error_msg, False)
            self.wlan.active(False)
            return None

    def disconnect(self):
        """断开 WiFi 连接"""
        try:
            self.wlan.disconnect()
            self.wlan.active(False)
            self._update_state(500, '已主动断开连接', False)
            print("已断开连接")
        except Exception as e:
            self._update_state(401, f'断开连接异常: {str(e)}', False)

    def get_status(self):
        """
        获取当前Wi-Fi连接状态信息

        Returns:
            dict: 包含连接状态详情的字典，结构如下：
            {
                'code': int,       # 状态代码（见下方代码表）
                'message': str,    # 当前状态描述
                'is_connected': bool  # 是否已建立连接
            }

        状态代码体系：
            [基础状态]
            0   - 初始化完成 (is_connected=False)
            500 - 已主动断开连接 (is_connected=False)

            [连接过程]
            100 - 正在断开旧连接 (is_connected=True)
            200 - 开始连接流程 (is_connected=False)
            201 - 正在尝试连接 (is_connected=False)
            202 - 等待连接中 (剩余秒数) (is_connected=False)

            [连接结果]
            300 - 连接成功 (is_connected=True)
            400 - 连接失败 (is_connected=False)
            401 - 断开连接异常 (is_connected=False)

        典型状态流程示例：
            0 → 200 → 201 → 202... → 300 (成功流程)
            0 → 200 → 201 → 202... → 400 (失败流程)

        Example:
            >>> self.get_status()
            {
                'code': 202,
                'message': '剩余等待: 45秒',
                'is_connected': False
            }
        """
        return self.connection_state
