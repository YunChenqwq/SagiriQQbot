import asyncio
from collections import defaultdict
import botpy
from http import HTTPStatus
from botpy.message import Message, GroupMessage, C2CMessage
import AI.gpt as gpt
import AI.qwen as qwen
import utils.SysState
from utils.voice import generate_voice_url
from utils.image import get_image_url
from botpy import logging
import re

_log = logging.get_logger()


class MyClient(botpy.Client):
    sys_path = ""
    config = None
    chatgpt_settings = None
    qwen_settings = None
    help = None
    reply_text = ""
    SysState = ""
    reply_image = None
    # 用于速率限制
    rate_limit_10s = defaultdict(list)  # 10秒内消息时间戳
    rate_limit_60s = defaultdict(list)  # 60秒内消息时间戳

    chatgpt_history = {}
    qwen_history = {}

    # 用于保存每个用户的状态
    user_states = defaultdict(lambda: {"MessageType": 0, "FileType": 0})

    valid_commands = []
    intents = botpy.Intents(
        public_guild_messages=True,
        public_messages=True,
        direct_message=True
    )

    def __init__(self, intents, bot):
        super().__init__(intents)
        if bot == "gpt":
            self.chatbot = gpt
        elif bot == "qwen":
            self.chatbot = qwen

    async def on_c2c_message_create(self, message: C2CMessage):
        text = message.content.strip()
        user_openid = message.author.user_openid

        # 打印收到消息的日志
        _log.info(f"收到C2C消息: {text}, 发送用户ID: {user_openid}")

        # 为每条消息创建独立的任务
        asyncio.create_task(self.process_message(message, user_openid))

    async def on_group_at_message_create(self, message: GroupMessage):
        text = message.content.strip()
        group_openid = message.group_openid

        # 打印收到消息的日志
        _log.info(f"收到群组消息: {text}, 发送用户ID: {group_openid}")

        # 为每条消息创建独立的任务
        asyncio.create_task(self.process_message(message, group_openid))

    async def process_message(self, message, identifier):
        self.reply_text = ""
        text = message.content.strip()

        # 检查速率限制
        if not self.check_rate_limit(identifier):
            self.reply_text = "你发送的消息太快了，请稍等一会再试。"
            await self.send_reply(message, identifier, 0, 0)
            return

        if self.is_url(text):
            await self.send_reply(message, identifier, 0, 0)  # 假设 0, 0 表示文本消息
            return
        if 'say' in text:
            self.reply_text = text.replace('/say', '').strip()  # 拙劣的办法 强行适配say命令
            await self.send_reply(message, identifier, 7, 3)
            return

        # 获取用户特定的消息类型和文件类型
        user_state = self.user_states[identifier]
        user_message_type = user_state["MessageType"]
        user_file_type = user_state["FileType"]

        # 选择历史记录
        if isinstance(message, C2CMessage):
            if identifier not in self.chatgpt_history:
                self.chatgpt_history[identifier] = [
                    {"role": "system", "content": self.chatgpt_settings['preset']}
                ]
            history = self.chatgpt_history[identifier]
            await self.chat_with_chatgpt(history, text, identifier, message)
        else:
            if identifier not in self.qwen_history:
                self.qwen_history[identifier] = [
                    {"role": "system", "content": self.qwen_settings['preset']}
                ]
            history = self.qwen_history[identifier]
            await self.chat_with_qwen(history, text, identifier, message)

        # 处理命令和用户输入
        new_user_message_type, new_user_file_type = await self.handle_commands(text, identifier, message, history)

        # 更新用户状态
        if new_user_message_type is not None and new_user_file_type is not None:
            user_state["MessageType"] = new_user_message_type
            user_state["FileType"] = new_user_file_type

        # 发送回复
        """
        if user_message_type != 8:
            
        else:
        """
        await self.send_reply(message, identifier, user_state["MessageType"], user_state["FileType"])

    def is_url(self, text):
        # 简单的 URL 正则表达式
        url_pattern = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # IPv4
            r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # IPv6
            r'(?::\d+)?'  # 端口
            r'(?:(?:/?|[/?]\S+)$)', re.IGNORECASE
        )
        return re.match(url_pattern, text) is not None  # 返回是否匹配

    def check_rate_limit(self, identifier):
        current_time = asyncio.get_event_loop().time()

        self.rate_limit_10s[identifier] = [
            t for t in self.rate_limit_10s[identifier] if current_time - t < 10
        ]
        if len(self.rate_limit_10s[identifier]) >= 2:
            return False  # 超过10秒内限制

        self.rate_limit_60s[identifier] = [
            t for t in self.rate_limit_60s[identifier] if current_time - t < 60
        ]
        if len(self.rate_limit_60s[identifier]) >= 10:
            return False  # 超过60秒内限制

        # 添加当前时间戳
        self.rate_limit_10s[identifier].append(current_time)
        self.rate_limit_60s[identifier].append(current_time)
        return True

    async def handle_commands(self, text, identifier, message, history):
        user_message_type = None  # 默认值
        user_file_type = None  # 默认值

        if text == "/help":
            self.reply_text = self.help
        elif text == "/gpt":
            self.chatbot = gpt
            self.reply_text = '已切换至gpt3.5模型啦'
        elif text == "/qwen":
            self.chatbot = qwen
            self.reply_text = '已切换至通义千问模型啦'
        elif text == "/reset":
            self.chatgpt_history[identifier] = [
                {"role": "system", "content": self.chatgpt_settings['preset']}
            ]
            self.qwen_history[identifier] = [
                {"role": "system", "content": self.qwen_settings['preset']}
            ]
            self.reply_text = '对话记录已清空，期待和哥哥的崭新聊天哦~'
        elif text == "/state":
            self.reply_text = utils.SysState.get_system_status()
        elif text == "/voice":
            self.reply_text = '已经开启语音聊天啦'
            return 7, 3  # 返回语音类型
        elif text == "/offvoice":
            self.reply_text = '已经关闭语音聊天啦'
            return 0, 0  # 返回文本类型
        elif text.startswith("/say "):
            # 获取/say后面的文本
            custom_text = text[5:].strip()
            if custom_text:
                upload_url = await generate_voice_url(custom_text)  #生成语音
                if upload_url:
                    self.reply_text = "say" + upload_url
                else:
                    self.reply_text = "语音生成失败，请重试。"
            else:
                self.reply_text = "请提供要转换为语音的文本。"
        elif text == "/来点纱雾":
            self.reply_image = "https://so1.360tres.com/t01d47905c72afe46f8.jpg"
            return 8, 1  # 傻逼腾讯 我自定义 8为图像消息
        else:
            if text.startswith("/") and text not in self.valid_commands:
                self.reply_text = "未知的命令哦~ 请使用 /help 来获取纱雾会的技能吧"

        return user_message_type, user_file_type  # 返回之前的状态值

    async def send_reply(self, message, identifier, user_message_type, user_file_type):
        # 打印发送回复的日志
        log_type = "文本" if user_message_type == 0 else "语音" if user_message_type == 3 else "未知类型"
        _log.info(f"发送{log_type}消息: {self.reply_text}, 用户ID: {identifier}")

        # user_message_type为8 调用send_reply_image方法发送图像

        #  reply_text 是否为 URL
        if self.is_url(self.reply_text):
            upload_url = self.reply_text

        # 判断消息类型是否为0，发送文本消息
        if user_message_type == 0:
            if isinstance(message, C2CMessage):
                await message._api.post_c2c_message(
                    openid=identifier,
                    msg_type=0,
                    msg_id=message.id,
                    content=self.reply_text
                )
            elif isinstance(message, GroupMessage):
                await message._api.post_group_message(
                    group_openid=identifier,
                    msg_type=0,
                    msg_id=message.id,
                    content=self.reply_text
                )
            return

        # 发送语音消息
        if user_message_type == 7 and user_file_type == 3:  # 只处理语音消息 其他富媒体的处理放在image函数
            upload_url = await generate_voice_url(self.reply_text)  # 生成语音的 URL

            if upload_url:
                if isinstance(message, C2CMessage):
                    uploadMedia = await message._api.post_c2c_file(
                        openid=identifier,
                        file_type=user_file_type,
                        url=upload_url
                    )
                    await message._api.post_c2c_message(
                        openid=identifier,
                        msg_type=7,
                        msg_id=message.id,
                        media=uploadMedia
                    )
                elif isinstance(message, GroupMessage):
                    uploadMedia = await message._api.post_group_file(
                        group_openid=identifier,
                        file_type=user_file_type,
                        url=upload_url
                    )
                    await message._api.post_group_message(
                        group_openid=identifier,
                        msg_type=7,
                        msg_id=message.id,
                        media=uploadMedia
                    )

    async def send_reply_image(self, file_type, message, user_message_type=None) -> None:
        try:
            if isinstance(self.reply_image, bytes):
                # 如果是字节数据，直接发送
                await message.reply(file_image=self.reply_image)
            elif isinstance(self.reply_image, str):
                # 如果是字符串，先判断是否为URL
                if self.is_url(self.reply_image):
                    # 如果是URL，发送富媒体
                    url = self.reply_image

                    if isinstance(message, C2CMessage):
                        uploadMedia = await message._api.post_c2c_file(
                            openid=message.author.user_openid,
                            file_type=file_type,
                            url=url
                        )
                        await message._api.post_c2c_message(
                            openid=message.author.user_openid,
                            msg_type=7,  # 7为富媒体消息类型
                            msg_id=message.id,
                            media=uploadMedia
                        )
                    elif isinstance(message, GroupMessage):
                        uploadMedia = await message._api.post_group_file(
                            group_openid=message.group_openid,
                            file_type=file_type,
                            url=url
                        )
                        await message._api.post_group_message(
                            group_openid=message.group_openid,
                            msg_type=7,  # 7为富媒体消息类型
                            msg_id=message.id,
                            media=uploadMedia
                        )
                else:
                    # 如果不是URL，那就为文件路径
                    with open(self.reply_image, "rb") as img:
                        await message.reply(file_image=img)

            else:
                raise ValueError("reply_image 的类型不正确，必须是字节数据、有效的 URL 或文件路径。")
        except FileNotFoundError:
            _log.error(f"图片文件未找到: {self.reply_image}")
            await message.reply(content="没有照片给哥哥看了")
        except Exception as e:
            _log.error(f"发送富媒体时发生错误: {str(e)}")
            await message.reply(content="发送富媒体时发生错误")
        finally:
            # 重置 reply_image
            self.reply_image = None



    async def chat_with_chatgpt(self, history, text, identifier, message):
        if not message.attachments:
            history.append({"role": "user", "content": text})

            try:
                response = gpt.chat_text_only(history, self.config, self.chatgpt_settings)

                if response and hasattr(response, 'choices') and len(response.choices) > 0:
                    ChatCompletionMessage = response.choices[0].message
                    history.append({'role': ChatCompletionMessage.role, 'content': ChatCompletionMessage.content})
                    self.reply_text = ChatCompletionMessage.content
                    return response

                else:
                    self.reply_text = "抱歉，我没有收到有效的回复。请再试一次。"
                    _log.error("无效的API响应: 没有有效的回复。")
                    return None

            except Exception as e:
                error_message = str(e)
                self.reply_text = "发生错误，请稍后再试。"

                if "401" in error_message:
                    self.reply_text = "请检查APIkey是否正确"
                elif "429" in error_message:
                    if "rate limit" in error_message:
                        self.reply_text = "啊哦，纱雾去摸鱼去啦~尼桑耐心等待一会哦~"
                    elif "quota" in error_message:
                        self.reply_text = "APIkey已超出配额，请联系开发者QQ393925220更新"
                    else:
                        self.reply_text = "纱雾目前访问属于高峰期，请稍后再试哦"
                elif "500" in error_message:
                    self.reply_text = "啊哦，纱雾去摸鱼去啦~尼桑耐心等待一会哦~"
                else:
                    self.reply_text = "发生未知错误，请哥哥稍等一下哦"

                _log.error(f"与 GPT 通信时发生错误: {error_message}")
                return None
        else:
            self.reply_text = "我还无法看到除了文本消息以外的消息哦"
            _log.warning("用户尝试发送非文本消息。")
            return None

    async def chat_with_qwen(self, history, text, identifier, message):
        if not message.attachments:
            history.append({"role": "user", "content": text})

            response = qwen.chat_text_only(history, self.config, self.qwen_settings)

            if isinstance(response, dict) and "error" in response:
                self.reply_text = f"发生错误: {response['error']}"
                return None

            if response.status_code != HTTPStatus.OK:
                error_code = response.code
                error_message = response.message

                if error_code == "InvalidParameter":
                    self.reply_text = "请求参数不合法，请检查请求参数。"
                elif error_code == "DataInspectionFailed":
                    self.reply_text = "请不要问纱雾一些奇怪的问题哦，不然会将你关进小黑屋哦"
                elif error_code == "InvalidApiKey":
                    self.reply_text = "请检查APIkey是否正确"
                elif error_code == "RequestTimeOut":
                    self.reply_text = "啊哦，纱雾去摸鱼去啦~尼桑耐心等待一会哦~"
                elif error_code == "InternalError":
                    self.reply_text = "内部错误，请稍后再试或联系服务支持。"
                elif error_code == "Throttling":
                    self.reply_text = "纱雾目前访问属于高峰期，请稍后再试哦"
                else:
                    self.reply_text = f"发生未知错误，有可能是APIkey已超出配额，请联系开发者QQ393925220更新"

                _log.error("请求失败: %s, 状态码: %s, 错误信息: %s", response.request_id, response.status_code,
                           error_message)
                return None

            ChatCompletionMessage = response.output.choices[0].message
            history.append({'role': ChatCompletionMessage.role, 'content': ChatCompletionMessage.content})
            self.reply_text = ChatCompletionMessage.content
            return response
        else:
            self.reply_text = "我还无法看到除了文本消息以外的消息哦"
            _log.warning("用户尝试发送非文本消息。")
            return None
