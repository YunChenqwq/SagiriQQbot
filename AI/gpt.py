from openai import OpenAI


def chat_text_only(chatgpt_history, config, chatgpt_settings):
    client = OpenAI(api_key=config['gpt']['api_key'])

    # 获取 proxy_url
    proxy_url = config['gpt'].get('proxy_url')

    # 只有当 proxy_url 不为 None 且不等于 "none" 时才设置代理
    if proxy_url and proxy_url.lower() != "none":
        if not proxy_url.endswith("/v1"):
            proxy_url += "/v1"
        client.base_url = proxy_url
    # 不使用代理时，不设置 client.base_url，使用默认值

    completion = client.chat.completions.create(
        model=chatgpt_settings['model'],
        messages=chatgpt_history,
        max_tokens=chatgpt_settings['max_tokens'],
        temperature=chatgpt_settings['temperature']
    )

    return completion
