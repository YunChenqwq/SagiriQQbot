import logging
import os
import random
import string
import traceback
import yaml
import websocket
import json
import requests


character_list = {
    "0": "派蒙 Paimon (Genshin Impact)",
    "1": "特别周 Special Week (Umamusume Pretty Derby)",
    "2": "无声铃鹿 Silence Suzuka (Umamusume Pretty Derby)",
    "3": "东海帝王 Tokai Teio (Umamusume Pretty Derby)",
    "4": "丸善斯基 Maruzensky (Umamusume Pretty Derby)",
}

current_dir = os.path.dirname(os.path.realpath(__file__))

#配置文件的路径
yaml_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'huggingface.yaml')

# 打开并读取 YAML 文件
with open(yaml_file_path, "r", encoding='utf-8') as file:
    config = yaml.load(file.read(), Loader=yaml.FullLoader)
    voice_config = config['huggingface_config']  # 获取语音配置

rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))
character = character_list[voice_config['character']]
audio_speed = voice_config['audio_speed']
hash_session = '{"session_hash":"' + rand_str + '","fn_index":2}'
audio_data = ''
audio_url = ''
base_url = voice_config['download_url']
ws_url = voice_config['websocket']
#保留
host = voice_config['proxy_host'] if 'proxy_host' in voice_config.keys() else None
port = voice_config['proxy_port'] if 'proxy_port' in voice_config.keys() else None
proxy_type = voice_config['proxy_type'] if 'proxy_type' in voice_config.keys() else None


def _get_audio_url():
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    if host and port and proxy_type:
        ws.run_forever(ping_timeout=30, http_proxy_host=host,
                       http_proxy_port=port, proxy_type=proxy_type)
    else:
        ws.run_forever(ping_timeout=30 )
    return base_url + audio_url


def on_message(ws, message):
    global audio_url
    try:
        msg = json.loads(message)
        if msg['msg'] == 'send_hash':
            ws.send(hash_session)
        elif msg['msg'] == 'send_data':
            ws.send(audio_data)
        elif msg['msg'] == 'process_completed':
            if msg['success']:
                audio_url = msg['output']['data'][1]['name']
                logging.info(f"Audio file generated: {audio_url}")
            else:
                logging.error("Processing failed: {}".format(msg['output'].get('error', 'Unknown error occurred')))
    except KeyError as e:
        logging.error(f"KeyError: {e} - Message received was: {message}")
    except Exception as e:
        logging.error(f"Error processing WebSocket message: {e}")
        traceback.print_exc()


def get_audio_wav(text: str, hash_uuid, language):
    global audio_data
    audio_data = '{"fn_index":2,"data":["' + text.replace('"',
                                                          "'") + '","' + character + '","' + language + '",' + audio_speed + ',false],"session_hash":"' + rand_str + '"}'
    file_path = os.getcwd()
    try:
        voice_content = requests.get(_get_audio_url())
        if voice_content.status_code == 200:
            with open(os.path.join(file_path, 'voice_tmp', 'voice_' + hash_uuid + '.wav'), 'wb') as f:
                f.write(voice_content.content)
            return True
        else:
            return False
    except Exception:
        traceback.print_exc()
        return False
