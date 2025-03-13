from microdot import Microdot, send_file
import ujson
import network
import sys
import time
from machine import Pin, reset

app = Microdot()
current_config_index = 0
config_cache = {}


# 初始化网络
def init_network():
    main_config = load_config('/config.json')
    if main_config and 'Wi-Fi' in main_config:
        wifi_config = main_config['Wi-Fi']

        # 先尝试STA模式
        if wifi_config['STA']:
            sta = network.WLAN(network.STA_IF)
            sta.active(True)
            sta.connect(wifi_config['STA']['ssid'], wifi_config['STA']['password'])
            for _ in range(20):  # 等待10秒
                if sta.isconnected():
                    print('STA Connected:', sta.ifconfig())
                    return
                time.sleep(0.5)

        # 启用AP模式
        ap = network.WLAN(network.AP_IF)
        ap.config(essid=wifi_config['AP']['ssid'],
                  authmode=wifi_config['AP']['authmode'],
                  password=wifi_config['AP']['password'])
        ap.active(True)
        print('AP模式已启动:', ap.ifconfig())
    else:
        # 默认AP配置
        ap = network.WLAN(network.AP_IF)
        ap.config(essid='espap', password='00000000', authmode=3)
        ap.active(True)
        print('使用默认AP配置:', ap.ifconfig())


# 配置文件加载
def load_config(path):
    try:
        if path in config_cache:
            return config_cache[path]

        with open(path, 'r') as f:
            config = ujson.load(f)
            config_cache[path] = config
            return config
    except Exception as e:
        print('加载配置失败:', path, e)
        return None


# 动态导入函数
def import_function(module_path):
    try:
        if module_path in sys.modules:
            return sys.modules[module_path]

        module = __import__(module_path)
        return module
    except Exception as e:
        print('导入模块失败:', module_path, e)
        return None


# HTML页面生成
def generate_html(config_paths, active_index):
    main_config = load_config('/config.json')
    if not main_config:
        return send_file('error.html', status_code=500)

    # 菜单项生成
    menu_items = []
    for index, path in enumerate(main_config['config_path']):
        cfg = load_config(path)
        if not cfg:
            continue

        color = 'lightgrey' if index == active_index else 'cyan'
        menu_items.append(f'''
            <div class="menu-item" style="background:{color};" 
                 onclick="loadConfig({index})">
                {cfg.get('config_name', '未命名')}
            </div>
        ''')

    # 内容区生成
    active_config = load_config(config_paths[active_index])
    function_blocks = []
    if active_config:
        for func_name in active_config.get('fun_list', []):
            func = active_config['function'].get(func_name)
            if not func:
                continue

            # 生成参数控件
            params_html = []
            param_ids = []
            if func['parameters']:
                for param, info in func['parameters'].items():
                    param_id = f'{func_name}_{param}'
                    param_ids.append(f"'{param_id}'")
                    if info['type'] in ['int', 'float'] and len(info['data']) == 2:
                        params_html.append(f'''
                            <div class="param">
                                <label>{param}:</label>
                                <input type="range" id="{param_id}" 
                                       min="{info['data'][0]}" max="{info['data'][1]}" 
                                       step="{1 if info['type'] == 'int' else 0.1}"
                                       oninput="updateValue('{param_id}')">
                                <span id="{param_id}_value">{info['data'][0]}</span>
                            </div>
                        ''')
                    elif info['data']:
                        options = ''.join([f'<option value="{v}">{v}</option>' for v in info['data']])
                        params_html.append(f'''
                            <div class="param">
                                <label>{param}:</label>
                                <select id="{param_id}">{options}</select>
                            </div>
                        ''')
                    else:
                        params_html.append(f'''
                            <div class="param">
                                <label>{param}:</label>
                                <input type="text" id="{param_id}">
                            </div>
                        ''')

            # 生成功能区块
            func_type = func.get('type', 'n')
            result_div = '' if func_type == 'show' else f'<div id="{func_name}_result" class="result"></div>'

            function_blocks.append(f'''
                <fieldset class="function-block" id="{func_name}_block">
                    <legend>
                        <input type="text" value="{func.get('doc', '')}" 
                               class="doc-input" oninput="toggleButtons(this)">
                        <button class="btn" onclick="updateDoc('{func_name}', this)" disabled>更改</button>
                        <button class="btn" onclick="cancelEdit(this)" disabled>取消</button>
                    </legend>
                    {'<div class="show-output" id="' + func_name + '_output"></div>' if func_type == 'show' else ''}
                    {''.join(params_html)}
                    {result_div}
                    {'' if func_type in ['show', 'n'] else f'<button class="exec-btn" onclick="executeFunction(\'{func_name}\', [{",".join(param_ids)}])">执行函数</button>'}
                </fieldset>
            ''')

    return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ margin: 0; font-family: Arial, sans-serif; }}
                .container {{ display: flex; min-height: 100vh; }}
                .menu {{ background: #f0f0f0; min-width: 120px; flex-shrink: 0; }}
                .menu-item {{ padding: 15px; cursor: pointer; transition: background 0.3s; }}
                .content {{ flex-grow: 1; padding: 20px; background: white; }}
                .function-block {{ margin: 20px 0; border: 2px solid #ddd; padding: 15px; border-radius: 5px; }}
                .param {{ margin: 10px 0; display: flex; align-items: center; gap: 10px; }}
                .btn {{ padding: 5px 10px; margin: 0 5px; cursor: pointer; }}
                .exec-btn {{ margin-top: 10px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }}
                .result {{ margin-top: 10px; padding: 10px; background: #f8f8f8; border: 1px solid #ddd; }}
                .show-output {{ padding: 10px; background: #e8e8e8; }}
                @media (orientation: portrait) {{
                    .container {{ flex-direction: column; }}
                    .menu {{ display: flex; flex-wrap: wrap; }}
                    .menu-item {{ flex: 1 0 100px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="menu">
                    {''.join(menu_items)}
                </div>
                <div class="content">
                    {''.join(function_blocks) if function_blocks else '<p>无可用功能</p>'}
                </div>
            </div>
            <script>
                let currentDoc = {{}};

                function loadConfig(index) {{
                    window.location.href = '/config/' + index;
                }}

                function toggleButtons(input) {{
                    const buttons = input.parentElement.getElementsByTagName('button');
                    buttons[0].disabled = input.value === currentDoc[input.parentElement.parentElement.id];
                    buttons[1].disabled = input.value === currentDoc[input.parentElement.parentElement.id];
                }}

                async function updateDoc(funcName, btn) {{
                    const input = btn.parentElement.querySelector('input');
                    const response = await fetch('/update_doc', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            func: funcName,
                            doc: input.value
                        }})
                    }});
                    if(response.ok) {{
                        currentDoc[funcName + '_block'] = input.value;
                        btn.disabled = true;
                        btn.nextElementSibling.disabled = true;
                    }}
                }}

                async function executeFunction(funcName, paramIds) {{
                    const params = {{}};
                    paramIds.forEach(id => {{
                        const el = document.getElementById(id);
                        params[id.split('_')[1]] = el.type === 'range' ? parseFloat(el.value) : el.value;
                    }});

                    try {{
                        const response = await fetch('/execute/' + funcName, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(params)
                        }});
                        const result = await response.text();
                        document.getElementById(funcName + '_result').innerText = result;
                    }} catch (e) {{
                        console.error('执行错误:', e);
                    }}
                }}

                // 实时更新show类型函数
                setInterval(async () => {{
                    const showBlocks = document.querySelectorAll('.show-output');
                    showBlocks.forEach(async block => {{
                        const funcName = block.id.split('_')[0];
                        try {{
                            const response = await fetch('/execute/' + funcName);
                            block.innerText = await response.text();
                        }} catch (e) {{ console.error(e); }}
                    }});
                }}, 700);

                // 初始化文档内容
                document.querySelectorAll('.doc-input').forEach(input => {{
                    currentDoc[input.parentElement.parentElement.id] = input.value;
                }});
            </script>
        </body>
        </html>
    '''


# 路由处理
@app.route('/')
def index(request):
    main_config = load_config('/config.json')
    if not main_config:
        return send_file('error.html', status_code=500)
    return generate_html(main_config['config_path'], current_config_index)


@app.route('/config/<index>')
def config_page(request, index):
    global current_config_index
    current_config_index = int(index)
    main_config = load_config('/config.json')
    return generate_html(main_config['config_path'], current_config_index)


@app.route('/execute/<func_name>', methods=['POST'])
def execute_function(request, func_name):
    main_config = load_config('/config.json')
    config = load_config(main_config['config_path'][current_config_index])
    func_info = config['function'].get(func_name)

    if not func_info:
        return '函数不存在', 404

    try:
        module = import_function(func_info['path'])
        func = getattr(module, func_name)
        params = ujson.loads(request.body)

        # 类型转换
        for param, info in func_info['parameters'].items():
            if param in params:
                if info['type'] == 'int':
                    params[param] = int(params[param])
                elif info['type'] == 'float':
                    params[param] = float(params[param])

        result = func(**params) if params else func()

        if func_info['type'] in ['fun_r', 'show']:
            return str(result)
        else:
            return '执行成功'
    except Exception as e:
        return f'执行错误: {str(e)}', 500


@app.route('/update_doc', methods=['POST'])
def update_doc(request):
    data = ujson.loads(request.body)
    main_config = load_config('/config.json')
    config_path = main_config['config_path'][current_config_index]
    config = load_config(config_path)

    if config and data['func'] in config['function']:
        config['function'][data['func']]['doc'] = data['doc']
        try:
            with open(config_path, 'w') as f:
                ujson.dump(config, f)
            config_cache[config_path] = config
            return '更新成功'
        except Exception as e:
            return f'保存失败: {str(e)}', 500
    return '更新失败', 400


# 启动服务
if __name__ == '__main__':
    init_network()
    try:
        app.run(port=80)
    except:
        reset()