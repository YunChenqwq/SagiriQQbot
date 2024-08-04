from http import HTTPStatus
import dashscope
from botpy import logging
_log = logging.get_logger()


def chat_text_only(qwen_history, config, qwen_settings):
    dashscope.api_key = config['qwen']['api_key']

    try:
        response = dashscope.Generation.call(
            model=config['qwen']['model'],
            messages=qwen_history,
            seed=qwen_settings['seed'],
            max_tokens=qwen_settings['max_tokens'],
            top_p=qwen_settings['top_p'],
            top_k=qwen_settings['top_k'],
            repetition_penalty=qwen_settings['repetition_penalty'],
            temperature=qwen_settings['temperature'],
            stop=qwen_settings['stop'],
            stream=qwen_settings['stream'],
            enable_search=qwen_settings['enable_search'],
            result_format=qwen_settings['result_format'],
            incremental_output=qwen_settings['incremental_output'],
        )

        # 检查响应状态码
        if response.status_code == HTTPStatus.OK:
            return response
        else:
            _log.error(
                '请求ID: %s, 状态码: %s, 错误代码: %s, 错误信息: %s',
                response.request_id, response.status_code,
                response.code, response.message
            )
            return response  # 返回原始响应以便进一步处理

    except Exception as e:
        _log.error(f"调用 Qwen 模型时发生错误: {str(e)}")
        return {"error": str(e)}  # 返回错误信息

