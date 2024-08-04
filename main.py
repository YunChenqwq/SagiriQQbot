import os
import sys
import QQBot
import botpy
import yaml

"""
public_messages 群/C2C公域消息事件
public_guild_messages	公域消息事件
guild_messages	消息事件 (仅 私域 机器人能够设置此 intents)
direct_message	私信事件
guild_message_reactions	消息相关互动事件
guilds	频道事件
guild_members	频道成员事件
interaction	互动事件
message_audit	消息审核事件
forums	论坛事件 (仅 私域 机器人能够设置此 intents)
audio_action	音频事件
"""
sys_path = os.path.dirname(os.path.realpath(sys.argv[0]))

if __name__ == '__main__':
    with open(sys_path + "/config/config.yaml", "r", encoding='utf-8') as file:
        config = yaml.load(file.read(), Loader=yaml.FullLoader)

    with open(sys_path + "/config/gpt.yaml", "r", encoding='utf-8') as file:
        chatgpt_settings = yaml.load(file.read(), Loader=yaml.FullLoader)

    with open(sys_path + "/config/qwen.yaml", "r", encoding='utf-8') as file:
        qwen_settings = yaml.load(file.read(), Loader=yaml.FullLoader)


    help_text = (
        "\n"
        "✰✰✰✰下面是纱雾目前掌握的技能哦✰✰✰✰\n"
        "/help：获取纱雾的使用帮助\n"
        "/reset：清除和纱雾之前的对话历史\n"
        "/gpt：切换到gpt模型\n"
        "/qwen：切换到通义千问"
    )

    bot = ""
    if config['gpt']['api_key'] == "" and config['qwen']['api_key'] == "":
        print("ERROR：config未配置，请配置后再启动程序！")
        sys.exit()
    else:
        bot = config['system']['default_ai']
        print("config已配置，默认启动" + bot)

    intents = botpy.Intents(public_guild_messages=True,public_messages=True,direct_message=True)
    client = QQBot.MyClient(intents=intents, bot=bot)
    client.valid_commands = ["/help", "/gpt", "/qwen", "/reset"]
    client.config = config
    client.chatgpt_settings = chatgpt_settings
    client.qwen_settings = qwen_settings
    client.help = help_text
    client.sys_path = sys_path
    appid = config['QQBot']['appid']
    secret = config['QQBot']['secret']

    print('start!')
    client.run(appid=appid, secret=secret)
