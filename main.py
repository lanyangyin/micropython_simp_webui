import _thread
import time

import ujson
import network
import usocket
import utime
import random
import machine

# -----------
# 定义常量
# -----------
sta_data = {
    "status": "idle",  # idle/connecting/connected/error
    "ssid": "",
    "password": "",
    "message": "闲置"
}
scan_data = {
    "status": "idle",  # idle/scanning/ready/error
    "result": "",
    "last_update": 0
}
AUTH_MODES = {
    "OPEN": 0,
    "WEP": 1,
    "WPA": 2,
    "WPA2": 3,
    "WPA/WPA2": 4
}
STA = network.WLAN(network.STA_IF)
AP = network.WLAN(network.AP_IF)
# 加载配置文件
with open('config.json') as f:
    config = ujson.load(f)
    fun_config = config['functions']
    wifi_config = config['WIFI']


# -----------
# 定义函数
# -----------
def unquote(s):
    """
    简易URL解码实现
    :param s: URL编码字符串
    :return: 解码后的字符串
    """
    parts = s.split('%')
    res = [parts[0]]
    for part in parts[1:]:
        if len(part) >= 2:
            hex_code = part[:2]
            try:
                res.append(bytes([int(hex_code, 16)]).decode('latin-1'))
                res.append(part[2:])
            except:
                res.append('%' + part)
        else:
            res.append('%' + part)
    return ''.join(res)


def safe_ssid_decode(b):
    """多编码尝试解码SSID"""
    encodings = ['utf-8', 'gbk', 'latin-1']
    for enc in encodings:
        try:
            return b.decode(enc).strip()
        except:
            continue
    # 无法解码时显示HEX
    return "Hex:" + ''.join('%02x' % x for x in b)


# -----------
# 预定义函数示例（需与config.json中的name对应）
# -----------
def ap_start(ssid: str, encryption: str = "OPEN", password: str = "00000000"):
    """
    启动热点
    :param ssid: 热点名称
    :param password: 密码
    :param encryption: 加密方式，如"WPA/WPA2"、"WEP"、"OPEN"、"WPA2"、"WPA"
    :return: 热点IP地址
    """
    if not AP.active():
        AP.active(True)
    authmode = AUTH_MODES[encryption]
    if authmode == 0:
        print(f"ap_start: {ssid, encryption}")
        AP.config(essid=ssid, authmode=authmode)
    elif authmode in [1, 2, 3, 4]:
        print(f"ap_start: {ssid, encryption, password}")
        AP.config(essid=ssid, authmode=authmode, password=password)


def sta_start(ssid: str, password: str) -> str:
    """
    安全增强版WiFi连接函数（带完整验证和状态管理）
    """
    # 输入验证阶段
    if not all((ssid, password)):
        sta_data.update(
            status="error",
            message="凭证为空",
            ssid=ssid,
            password=""
        )
        return "错误：SSID和密码不能为空"

    # SSID规范检查
    if not (1 <= len(ssid) <= 32):
        sta_data.update(
            status="error",
            message="SSID长度无效",
            ssid=ssid,
            password=""
        )
        return "错误：SSID长度需为1-32个字符"
    if any(c < '\x20' or c > '\x7e' for c in ssid):
        sta_data.update(
            status="error",
            message="SSID含非法字符",
            ssid=ssid,
            password=""
        )
        return "错误：SSID包含非ASCII可打印字符"

    # 密码规范检查
    if len(password) < 8 or len(password) > 63:
        sta_data.update(
            status="error",
            message="密码长度无效",
            ssid=ssid,
            password=""
        )
        return "错误：密码需8-63个字符"
    if any(ord(c) < 32 or ord(c) > 126 for c in password):
        sta_data.update(
            status="error",
            message="密码含非法字符",
            ssid=ssid,
            password=""
        )
        return "错误：密码包含非法字符"

    # 连接状态冲突检测
    if sta_data["status"] in ("connecting", "connected"):
        current_ssid = STA.config("essid") if STA.isconnected() else ""
        return f"操作冲突：当前状态[{sta_data['status']}], SSID[{current_ssid}]"

    try:
        # 准备连接环境
        if not STA.active():
            STA.active(True)
            utime.sleep_ms(500)  # 精确等待接口激活

        # 启动连接线程
        def _connect_thread():
            start_time = utime.ticks_ms()
            STA.connect(ssid, password)

            while not STA.isconnected():
                # 精确超时计算（30秒）
                if utime.ticks_diff(utime.ticks_ms(), start_time) > 30 * 1000:
                    raise RuntimeError("连接超时")
                utime.sleep_ms(300)  # 更灵敏的检测间隔

            # 连接成功后更新状态
            sta_data.update(
                status="connected",
                message=f"已连接 {STA.config('essid')}",
                ssid=STA.config("essid"),
                password="",  # 清除密码明文
                ip=STA.ifconfig()[0],
                rssi=STA.status("rssi")
            )

        # 更新连接中状态（不存储明文密码）
        sta_data.update(
            status="connecting",
            message="正在验证凭证...",
            ssid=ssid,
            password="",
            ip=""
        )

        # 启动线程
        _thread.start_new_thread(_connect_thread, ())
        return "连接流程已启动"

    except Exception as e:
        sta_data.update(
            status="error",
            message=f"连接异常: {str(e)}",
            ssid=ssid,
            password="",
            ip=""
        )
        STA.disconnect()
        return f"连接失败: {str(e)}"

    finally:
        # 确保不保留密码明文
        sta_data["password"] = ""


def led_control(state, brightness):
    """
    控制LED
    :param state: 开关状态
    :param brightness: 亮度百分比
    """
    print(f"Setting LED: {state} at {brightness}%")
    # 实际硬件控制代码


def get_temperature():
    return f"{random.uniform(20, 30):.1f}°C"  # 示例温度值


def restart():
    machine.reset()


def reorder_functions(new_order):
    """
    功能排序调整函数
    :param new_order: 逗号分隔的功能ID字符串（如"test,led_control"），空字符串表示获取当前顺序
    :return: 当前顺序字符串 | "已完成" | 错误信息
    """
    original_list = config['function_list']
    original_set = set(original_list)

    if not new_order.strip():
        return ",".join(original_list)

    try:
        # 处理解码后的输入
        new_list = [x.strip() for x in new_order.split(',') if x.strip()]

        # 完整校验（包括重复项）
        if len(new_list) != len(original_list):
            return f"错误：元素数量不符（应有{len(original_list)}个）"

        new_set = set(new_list)
        if new_set != original_set:
            missing = original_set - new_set
            extra = new_set - original_set
            return f"错误：缺少{','.join(missing)}，多余{','.join(extra)}"

        duplicates = {x for x in new_list if new_list.count(x) > 1}
        if duplicates:
            return f"错误：重复元素{','.join(duplicates)}"

        if new_list == original_list:
            return "顺序未改变"

        # 更新配置
        config['function_list'] = new_list
        with open('config.json', 'w') as f:
            ujson.dump(config, f)
        return "已完成"

    except Exception as e:
        return f"处理错误：{str(e)}"


def remove_config_function(target_id: str) -> str:
    """
    安全移除功能配置项（修复备份问题版）
    特点：
    1. 增加数据备份机制
    2. 异常处理优化
    3. 原子性操作保障
    """
    # 系统保护校验
    protected_functions = {'wifi_status', 'restart'}
    if target_id in protected_functions:
        return "错误：系统关键功能不可删除"

    # 存在性校验
    if target_id not in config['function_list']:
        return f"错误：ID '{target_id}' 不存在"

    # 创建数据备份
    backup_data = {
        "list": config['function_list'].copy(),
        "function": ujson.loads(ujson.dumps(config['functions'].get(target_id, {})))
    }

    try:
        # 删除关联数据
        del config['functions'][target_id]
        config['function_list'].remove(target_id)

        # 持久化保存
        with open('config.json', 'w') as f:
            ujson.dump(config, f)

        return f"成功移除 '{target_id}'，剩余功能数：{len(config['function_list'])}"

    except Exception as e:
        # 失败回滚（使用备份数据）
        config['function_list'] = backup_data["list"]
        if backup_data["function"]:
            config['functions'][target_id] = backup_data["function"]
        return f"配置删除失败：{str(e)}\n已自动回滚数据"


def wifi_status() -> str:
    """
    获取WIFI状态
    :return: 状态字符串
    """
    if STA.isconnected():
        STA_IP = STA.ifconfig()[0]
    else:
        STA_IP = None
    AP_IP = AP.ifconfig()[0]
    return f"STA_IP: {STA_IP}<br>AP_IP: {AP_IP}"


def update_ap_config(ssid: str, encryption: str, password: str) -> str:
    """
    更新AP热点配置
    :return: 成功信息或错误提示
    """
    # SSID验证
    if len(ssid) < 1 or len(ssid) > 32:
        return "错误：SSID长度需为1-32个字符"
    if any(ord(c) < 32 or ord(c) > 126 for c in ssid):
        return "错误：SSID包含非法字符"

    # 加密方式验证
    if encryption not in AUTH_MODES:
        return f"错误：加密方式无效，可选：{', '.join(AUTH_MODES.keys())}"
    authmode = AUTH_MODES[encryption]

    # 密码验证
    if authmode == 0:  # OPEN
        if password.strip() != "":
            return "错误：OPEN模式不能有密码"
    elif authmode == 1:  # WEP
        if len(password) not in (5, 13, 10, 26):
            return "错误：WEP密码需为5/13(ASCII)或10/26(HEX)"
        if len(password) in (10, 26):
            try:
                int(password, 16)
            except:
                return "错误：WEP HEX密码无效"
    else:  # WPA/WPA2
        if len(password) < 8 or len(password) > 63:
            return "错误：WPA密码需8-63个字符"
        if any(ord(c) < 32 or ord(c) > 126 for c in password):
            return "错误：密码含非法字符"

    # 更新配置
    config['WIFI']['ap'].update(ssid=ssid, encryption=encryption, password=password)
    with open('config.json', 'w') as f:
        ujson.dump(config, f)
    ap_start(**config['WIFI']['ap'])  # 立即生效
    return "AP配置更新成功"


def async_scan_wifi():
    global STA, scan_data

    if scan_data["status"] == "scanning":
        return "⚠️ 扫描正在进行中，请稍后刷新"

    def _scan_task():
        global scan_data
        original_active = STA.active()

        try:
            scan_data.update(status="scanning", result="")
            sta_data["status"] = "scanning"
            sta_data["ssid"] = ""
            sta_data["password"] = ""
            sta_data["message"] = "正在扫描..."
            if not STA.active():
                STA.active(True)
                utime.sleep_ms(300)  # 确保接口激活

            start_time = utime.ticks_ms()
            aps = STA.scan()
            scan_time = utime.ticks_diff(utime.ticks_ms(), start_time)

            if not aps:
                scan_data.update(
                    status="ready",
                    result=f"⏱️ 扫描耗时{scan_time}ms<br>未发现可用WiFi网络",
                    last_update=utime.time()
                )
                sta_data["status"] = "ready"
                sta_data["ssid"] = ""
                sta_data["password"] = ""
                sta_data["message"] = "未发现可用WiFi网络"
                return

            # 处理结果
            result = [f"⏱️ 扫描耗时{scan_time}ms<br>发现{len(aps)}个网络:"]
            sorted_aps = sorted(
                (ap for ap in aps if ap[0]),
                key=lambda x: x[3],
                reverse=True
            )

            for i, ap in enumerate(sorted_aps, 1):
                ssid, essid, channel, strength, authmode, hidden = ap
                ssid = safe_ssid_decode(ssid)
                try:
                    # line = f"{i}. {ssid} 强度:{strength}dBm 频道:{channel}"
                    line = f"<br>{i}. {ssid}"
                    result.append(line)
                except:
                    continue

            scan_data.update(
                status="ready",
                result="\n".join(result),
                last_update=utime.time()
            )
            sta_data["status"] = "ready"
            sta_data["ssid"] = ""
            sta_data["password"] = ""
            sta_data["message"] = "扫描完成"

        except Exception as e:
            scan_data.update(
                status="error",
                result=f"❌ 扫描失败: {str(e)}",
                last_update=utime.time()
            )
            sta_data["status"] = "error"
            sta_data["ssid"] = ""
            sta_data["password"] = ""
            sta_data["message"] = "扫描失败"
        finally:
            if not original_active:
                STA.active(False)

    # 启动后台线程扫描
    _thread.start_new_thread(_scan_task, ())
    return "🔍 后台扫描已启动，请2秒后刷新查看结果"


def scan_status():
    status_map = {
        "idle": "🟢 就绪状态",
        "scanning": "🟡 扫描进行中...",
        "ready": "🟢 最近一次扫描结果：",
        "error": "🔴 最近扫描错误："
    }

    # 添加时间显示本地化
    def format_time(t):
        return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])

    time_info = ""
    if scan_data['last_update'] > 0:
        t = utime.localtime(scan_data['last_update'])
        time_info = f"\n（更新时间：{format_time(t)}）"

    return f"{status_map.get(scan_data['status'], '未知状态')}<br>{scan_data['result']}<br>{time_info}"


def sta_status() -> str:
    """
    获取详细的STA连接状态（安全增强版）
    :return: 格式化后的状态信息
    """
    # 基础状态信息
    status_info = {"status": sta_data["status"], "active": STA.active(), "connected": STA.isconnected(),
                   "ssid": STA.config("essid") if STA.isconnected() else sta_data["ssid"],
                   "ip": STA.ifconfig()[0] if STA.isconnected() else "N/A",
                   "rssi": STA.status("rssi") if STA.isconnected() else 0,
                   "channel": STA.config("channel") if STA.isconnected() else 0, "message": sta_data["message"],
                   "last_update": utime.time(), "password": "********" if sta_data["password"] else "N/A"}
    return (
        f"<b>STA状态</b>: {status_info['status'].upper()}<br>"
        f"<b>SSID</b>: {status_info['ssid']}<br>"
        f"<b>IP地址</b>: {status_info['ip']}<br>"
        f"<b>信号强度</b>: {status_info['rssi']} dBm<br>"
        f"<b>频道</b>: {status_info['channel']}<br>"
        f"<b>状态信息</b>: {status_info['message']}"
    )


def update_sta_config(ssid: str, password: str) -> str:
    """
    更新STA配置并重新连接
    逻辑特点：
    1. 只修改已有SSID对应的密码，不新增SSID
    2. 自动清理空占位项（{"ssid": "", ...}）
    3. 保持原有SSID顺序，仅更新密码
    4. 连接时自动使用第一个有效配置
    """
    # ---------------------
    # 输入验证
    # ---------------------
    # SSID合法性检查
    if not (1 <= len(ssid) <= 32):
        return "错误：SSID长度需为1-32字符"
    if any(ord(c) < 32 or ord(c) > 126 for c in ssid):
        return "错误：SSID含非法字符"

    # 密码基础验证
    if len(password) < 8:
        return "错误：密码至少8个字符"
    if any(ord(c) < 32 or ord(c) > 126 for c in password):
        return "错误：密码含非法字符"

    # ---------------------
    # 配置处理
    # ---------------------
    sta_list = config['WIFI']['sta']
    target_index = -1
    empty_indices = []

    # 扫描列表（带索引记录）
    for i, entry in enumerate(sta_list):
        if entry['ssid'] == ssid:
            target_index = i
        elif entry['ssid'] == "" and entry['password'] == "":
            empty_indices.append(i)

    # 存在目标SSID：直接更新
    if target_index != -1:
        sta_list[target_index]['password'] = password

    # 不存在目标SSID：尝试使用空位
    else:
        if not empty_indices:
            return "错误：SSID不存在且无空位可替换"

        # 使用第一个空位并清理其他空项
        sta_list[empty_indices[0]] = {'ssid': ssid, 'password': password}
        for idx in reversed(empty_indices[1:]):
            del sta_list[idx]

    # 清理残留空项（包括更新后可能产生的）
    config['WIFI']['sta'] = [e for e in sta_list
                             if not (e['ssid'] == "" and e['password'] == "")]

    # 保证至少有一个空项（当列表为空时）
    if not config['WIFI']['sta']:
        config['WIFI']['sta'] = [{'ssid': "", 'password': ""}]

    # ---------------------
    # 持久化与连接
    # ---------------------
    with open('config.json', 'w') as f:
        ujson.dump(config, f)

    valid_configs = [c for c in config['WIFI']['sta']
                     if c['ssid'] and c['password']]

    return "STA配置更新成功，当前有效配置数量：" + str(len(valid_configs))


def delete_sta_config(target_ssid: str) -> str:
    """
    删除指定SSID的STA配置
    特点：
    1. 删除所有匹配项
    2. 删除后列表必含一个空占位符
    3. 自动触发连接更新
    """
    global sta_connector, config

    # 输入验证
    if not target_ssid:
        return "错误：SSID不能为空"

    sta_list = config['WIFI']['sta']
    original_count = len(sta_list)

    # 执行删除
    sta_list[:] = [e for e in sta_list if e['ssid'] != target_ssid]
    deleted_count = original_count - len(sta_list)

    if deleted_count == 0:
        return "未找到指定SSID"

    # 清理现有空项后添加一个占位符
    sta_list[:] = [e for e in sta_list if not (e['ssid'] == "" and e['password'] == "")]
    sta_list.append({"ssid": "", "password": ""})

    # 持久化
    with open('config.json', 'w') as f:
        ujson.dump(config, f)

    # 重新连接
    valid_configs = [c for c in sta_list if c['ssid']]
    # if sta_connector:
    #     sta_connector.disconnect()
    # if valid_configs:
    #     sta_connector = connect_wifi()
    #     sta_connector.connect(valid_configs[0]['ssid'], valid_configs[0]['password'], blocking=False)

    return f"已删除{deleted_count}个配置，剩余有效配置：{len(valid_configs)}"


def add_sta_config(new_ssid: str, new_password: str) -> str:
    """
    新增STA配置
    特点：
    1. 强制检查SSID唯一性
    2. 自动清除空占位符
    3. 新配置添加到列表末尾
    """
    # 输入验证
    if not (1 <= len(new_ssid) <= 32):
        return "错误：SSID长度需为1-32字符"
    if any(ord(c) < 32 or ord(c) > 126 for c in new_ssid):
        return "错误：SSID含非法字符"
    if len(new_password) < 8:
        return "错误：密码至少8个字符"
    if any(ord(c) < 32 or ord(c) > 126 for c in new_password):
        return "错误：密码含非法字符"

    # 检查SSID是否已存在
    sta_list = config['WIFI']['sta']
    if any(e['ssid'] == new_ssid for e in sta_list):
        return "错误：该SSID已存在"

    # 清除所有空项
    sta_list[:] = [e for e in sta_list if not (e['ssid'] == "" and e['password'] == "")]

    # 添加新配置
    sta_list.append({"ssid": new_ssid, "password": new_password})

    # 持久化
    with open('config.json', 'w') as f:
        ujson.dump(config, f)

    return f"已成功添加 {new_ssid}，当前配置数量：{len(sta_list)}"


def sort_sta_config(mode: str = "connection") -> str:
    """
    排序STA配置列表（严格模式，不留空项）
    功能特点：
    1. 完全移除所有空占位符
    2. 支持三种排序模式：字母顺序(asc/desc)/连接时间(connection)
    3. 连接时间数据持久化存储
    4. 自动连接首项配置
    """
    global config

    # ---------------------
    # 输入验证
    # ---------------------
    valid_modes = ("asc", "desc", "connection")
    if mode not in valid_modes:
        return f"错误：无效模式，允许值：{', '.join(valid_modes)}"

    # ---------------------
    # 数据预处理
    # ---------------------
    sta_list = config['WIFI']['sta']

    # 过滤所有空项
    valid_items = [e for e in sta_list if e['ssid'] or e['password']]

    # 防御性检查：列表为空时返回错误
    if not valid_items:
        return "错误：配置列表为空，无法排序"

    # ---------------------
    # 核心排序逻辑
    # ---------------------
    try:
        if mode == "connection":
            # 确保存在最后连接时间字段
            for item in valid_items:
                if 'last_connected' not in item:
                    item['last_connected'] = 0
            valid_items.sort(key=lambda x: x['last_connected'], reverse=True)
        else:
            reverse = (mode == "desc")
            valid_items.sort(
                key=lambda x: x['ssid'].lower(),
                reverse=reverse
            )
    except Exception as e:
        return f"排序错误：{str(e)}"

    # ---------------------
    # 配置更新与持久化
    # ---------------------
    config['WIFI']['sta'] = valid_items
    with open('config.json', 'w') as f:
        ujson.dump(config, f)

    # ---------------------
    # 生成状态报告
    # ---------------------
    status = []
    if mode == "connection":
        last_ts = valid_items[0].get('last_connected', 0)
        if last_ts > 0:
            t = utime.localtime(last_ts)
            status.append(f"最后连接：{t[0]}-{t[1]:02d}-{t[2]:02d}")

    return f"排序完成（模式：{mode}）| 首项：{valid_items[0]['ssid']} " + " ".join(status)


# -----------
# 网页生成函数
# -----------
def generate_html():
    html = """<html><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { 
            background: #f0f2f5; 
            margin: 0;
            padding: 20px;
        }
        [data-theme="dark"] .group {
            background: #2a2a2a;
            border-color: #58a6ff;
        }
        .group { 
            background: white;
            border-left: 4px solid #1890ff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            margin: 15px 0;
            padding: 20px;
            transition: transform 0.2s;
        }
        .group:hover {
            transform: translateY(-2px);
        }
        h3 {
            color: #1890ff;
            margin: 0 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
            font-size: 1.2em;
        }
        input[type="text"] {
            width: 100%;
            padding: 8px;
            margin: 8px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            border-color: #1890ff;
            outline: none;
        }
        input[type="submit"], button {
            background: #1890ff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 10px;
            transition: opacity 0.3s;
        }
        input[type="submit"]:hover, button:hover {
            opacity: 0.9;
        }
        input:invalid {
            border-color: #ff4d4f;
            background: #fff1f0;
        }        
        .output {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            font-size: 1.1em;
            color: #333;
            min-height: 40px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .loading::after {
            content: " ";
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .error-group {
            border-left-color: #ff4d4f !important;
            background: #fff1f0;
        }
        
        .error-group h3 {
            color: #ff4d4f !important;
        }
        
        .error-group .output {
            color: #ff4d4f;
            background: #fff2f0;
            border: 1px solid #ffccc7;
        }        
    </style>
    <script>
        function updateShow(id) {
            fetch('/show/' + id)
            .then(r => r.text())
            .then(t => document.getElementById(id).innerHTML = t)
        }
        
        function handleRutSubmit(event, groupId) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const params = new URLSearchParams();
            for (const [key, value] of formData) {
                params.append(key, value);
            }
            fetch('/' + groupId, {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: params
            })
            .then(r => r.text())
            .then(t => document.getElementById(groupId + '_result').value = t)
        }
    </script></head><body>"""
    # 获取所有已定义的函数名
    available_functions = set(globals().keys())

    for group_id in config['function_list']:
        group_html = ""
        error_occurred = False

        # 检查功能组是否存在
        if group_id not in fun_config:
            html += f'''
            <div class="group error-group">
                <h3>🔴 无效功能组</h3>
                <div class="output">
                    配置错误：未找到 {group_id} 的定义
                </div>
            </div>
            '''
            error_occurred = True
        else:
            group = fun_config[group_id]
            func_name = group['name']

            # 检查函数是否存在
            if func_name not in available_functions:
                html += f'''
                <div class="group error-group">
                    <h3>🔴 {group["name"].upper()}</h3>
                    <div class="output">
                        函数 {func_name} 未实现<br>
                        请检查代码或配置文件
                    </div>
                </div>
                '''
                error_occurred = True

        # 如果有错误直接添加错误信息
        if error_occurred:
            html += group_html
            continue  # 关键点：跳过后续正常处理

        group = fun_config[group_id]
        html += f'<div class="group"><h3>🔹 {group["name"].upper()}</h3>'

        if group['type'] == 'function':
            html += f'<form action="/{group_id}" method="post">'
            for i, param in enumerate(group['data']):
                html += f'<input type="text" name="arg{i}" placeholder="{param}"><br>'
            html += '<input type="submit" value="Run"></form>'

        elif group['type'] == 'show':
            html += f'<div class="output" id="{group_id}">Loading...</div>'
            html += f'<script>setInterval(() => updateShow("{group_id}"), 370)</script>'

        elif group['type'] == 'rut':
            html += f'<form onsubmit="handleRutSubmit(event, \'{group_id}\')">'
            for i, param in enumerate(group['data']):
                html += f'<input type="text" name="arg{i}" placeholder="{param}"><br>'
            html += '<input type="submit" value="Run">'
            html += f'<br><input type="text" id="{group_id}_result" readonly></form>'

        html += '</div>'
    return html + "</body></html>"


# -----------
# 网络服务
# -----------
def start_webserver():
    s = usocket.socket()
    s.bind(('0.0.0.0', 80))
    s.listen(5)

    while True:
        conn, addr = s.accept()
        request = conn.recv(1024).decode()

        # 路由处理
        if request.startswith('GET /'):
            if request.startswith('GET /show/'):
                group_id = request.split('/show/')[1].split()[0]
                func = globals()[fun_config[group_id]['name']]
                result = str(func())
                conn.send('HTTP/1.1 200 OK\nContent-Type: text/plain; charset=utf-8\n\n' + result)
            else:
                conn.send('HTTP/1.1 200 OK\nContent-Type: text/html; charset=utf-8\n\n' + generate_html())

        elif request.startswith('POST /'):
            group_id = request.split()[1].split('/')[1]
            group = fun_config[group_id]

            # 分离headers和body
            header_body = request.split('\r\n\r\n', 1)
            body = header_body[1] if len(header_body) > 1 else ''

            # 解析POST参数
            params = {}
            if body:
                pairs = body.split('&')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        # 解码处理
                        decoded_value = unquote(value.replace('+', ' '))  # 同时处理空格编码
                        params[key] = decoded_value

            # 构建参数列表（带默认值）
            expected_args = len(group['data'])
            args = [params.get(f'arg{i}', '') for i in range(expected_args)]

            # 执行对应函数
            func = globals()[group['name']]

            if group['type'] == 'rut':
                try:
                    result = func(*args)
                    conn.send(f'HTTP/1.1 200 OK\nContent-Type: text/plain\n\n{result}')
                except Exception as e:
                    conn.send(f'HTTP/1.1 500 Error\n\n{str(e)}')
            else:
                # 特殊处理重启函数
                if func == restart:
                    conn.send('HTTP/1.1 303 See Other\r\nLocation: /\r\nConnection: close\r\n\r\n')
                    conn.close()
                    utime.sleep_ms(300)
                    machine.reset()
                else:
                    try:
                        func(*args)
                        conn.send('HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n')
                    except TypeError as e:
                        print("参数错误:", e)
        conn.close()


if __name__ == '__main__':
    # 启动热点
    ap_start(**wifi_config["ap"])
    print(AP.ifconfig())
    # 启动wifi
    # 仅当有有效STA配置时尝试连接
    if wifi_config['sta'][0]['ssid']:
        sta_start(**wifi_config["sta"][0])
        print(STA.ifconfig())
    # 启动网络服务
    start_webserver()
