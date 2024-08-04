import os
import traceback
import yaml
import base64
import simpleaudio as sa
import oss2  # 阿里云OSS
import logging
import asyncio
from uuid import uuid4
from .huggingface.wav2silk import convert_to_silk
from .huggingface.huggingface_session_hash import get_audio_wav

current_dir = os.path.dirname(os.path.realpath(__file__))

#配置文件的路径
yaml_file_path = os.path.join(current_dir, "..", "config", "huggingface.yaml")

with open(yaml_file_path, "r", encoding='utf-8') as file:
    config = yaml.load(file.read(), Loader=yaml.FullLoader)
    voice_config = config['huggingface_config']  # 获取语音配置
    oss_config = config['oss_config']  # 获取 OSS 配置
    auth = oss2.Auth(oss_config['access_key_id'], oss_config['access_key_secret'])
    bucket = oss2.Bucket(auth, oss_config['endpoint'], oss_config['bucket_name'])


def _get_voice_wav(input_text):
    print(f"文本长度: {len(input_text)}")
    # 检查输入文本长度限制
    if voice_config["limitLength"] != 0 and len(input_text) > voice_config["limitLength"]:

        input_text = input_text[:voice_config["limitLength"]]  # 超过限长截取

    hash_uuid = str(uuid4()).replace("-", "")[:9]  # 生成唯一标识符

    """" 防止AI抽象中英混用 且训练模型效果以中日为主 
    if any(char.isalpha() for char in input_text):  # 含有英文字母
        language = "English"
    elif any('\u3040' <= char <= '\u309F' for char in input_text) or any('\u30A0' <= char <= '\u30FF' for char in input_text):  # 含有平假名或片假名
        language = "日本語"
    else:
        language = "简体中文"
    """""
    if any('\u3040' <= char <= '\u309F' for char in input_text) or any(
            '\u30A0' <= char <= '\u30FF' for char in input_text):  # 含有平假名或片假名
        language = "日本語"
    else:
        language = "简体中文"
    print(language)
    # 直接使用 get_audio_wav 函数生成音频
    try:
        if not get_audio_wav(input_text, hash_uuid, language):
            logging.error(f"wav生成失败")
            return hash_uuid, ""
    except Exception as e:
        logging.error(f"调用 get_audio_wav 时发生错误: {e}")
        return hash_uuid, ""

    return hash_uuid, _wav2silk(hash_uuid)


def _wav2silk(hash_uuid):
    wav_path = os.path.join(os.getcwd(), "voice_tmp", "voice_" + hash_uuid + ".wav")
    silk_path = convert_to_silk(wav_path)  # 生成silk文件
    if os.path.exists(silk_path):
        with open(silk_path, "rb") as audio_file:
            audio_data = audio_file.read()
        base64_silk = base64.b64encode(audio_data).decode("utf-8")
        return silk_path  # 返回silk文件路径
    else:
        return "未找到silk位置"


def _remove_tmp(hash_uuid):
    try:
        os.remove(os.path.join(os.getcwd(), "voice_tmp", "voice_" + hash_uuid + ".wav"))
        os.remove(os.path.join(os.getcwd(), "voice_tmp", "voice_" + hash_uuid + ".pcm"))
    except FileNotFoundError:
        logging.warning("未找到wav,pcm与silk文件")
    except Exception:
        traceback.print_exc()


def _upload_file_to_oss(local_file, object_name):
    """将文件上传到OSS并返回URL"""
    try:
        bucket.put_object_from_file(object_name, local_file)
        file_url = f"https://{bucket.bucket_name}.{bucket.endpoint.split('://')[1]}/{object_name}"
        return file_url
    except Exception as e:
        logging.error(f"上传文件失败: {e}")
        return None


def play_voice(file_path):
    """播放音频文件 测试用"""
    wave_obj = sa.WaveObject.from_wave_file(file_path)
    play_obj = wave_obj.play()
    play_obj.wait_done()  # 等待播放完成


async def generate_voice_url(text_input):
    """异步生成语音并返回上传后的文件URL"""
    # 创建临时文件夹
    temp_dir = os.path.join(os.getcwd(), "voice_tmp")
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    # 调用同步函数在线程中执行
    uuid, silk_file_path = await asyncio.to_thread(_get_voice_wav, text_input)

    if silk_file_path:
        """
        # 播放生成的语音 测试用
        wav_path = os.path.join(temp_dir, "voice_" + uuid + ".wav")
        await asyncio.to_thread(play_voice, wav_path)
        """
        # 上传silk文件到OSS并返回URL
        object_name = f"voice_{uuid}.silk"
        file_url = await asyncio.to_thread(_upload_file_to_oss, silk_file_path, object_name)
        return file_url
    else:
        logging.error("生成语音失败，无法返回URL")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    text_input = input("请输入要转换为语音的文本：")
    url = generate_voice_url(text_input)
    if url:
        print(f"文件上传成功，访问URL: {url}")
