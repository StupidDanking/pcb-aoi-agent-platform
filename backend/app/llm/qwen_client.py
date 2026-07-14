import json
from typing import Any

from openai import OpenAI

from app.config.settings import settings


def qwen_available() -> bool:
    return bool(settings.QWEN_API_KEY and settings.QWEN_API_KEY.strip())


def remove_large_fields(data: Any) -> Any:
    """
    去掉 base64 图片，避免把超长图片内容发给大模型。
    只保留检测统计、类别、bbox、置信度等结构化信息。
    """

    if isinstance(data, dict):
        cleaned = {}

        for key, value in data.items():
            if key in {
                "annotated_image_base64",
                "image_path",
                "annotated_image_path",
            }:
                continue

            cleaned[key] = remove_large_fields(value)

        return cleaned

    if isinstance(data, list):
        return [remove_large_fields(item) for item in data]

    return data


class QwenClient:
    def __init__(self):
        self.client = None

    def get_client(self) -> OpenAI:
        if self.client is None:
            self.client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
            )

        return self.client

    def chat(
        self,
        user_message: str,
        detection_result: dict | None = None,
    ) -> str:
        if not qwen_available():
            raise RuntimeError("QWEN_API_KEY 未配置")

        system_prompt = """
你是一个 PCB AOI 缺陷检测智能助手。
你需要用中文回答用户问题。

规则：
1. 如果提供了 detection_result JSON，你必须优先基于 JSON 回答。
2. 不要编造检测结果中不存在的类别、数量、置信度或 bbox。
3. 如果用户问“有几个 missing_hole / short / open_circuit / spur / mouse_bite / spurious_copper”，你需要从 class_stats 或每张图的 class_stats 中统计。
4. 如果是批量检测，你可以说明总数，也可以按每张图片分别说明。
5. 如果用户问模型指标，比如 mAP50、Recall、Precision，需要用通俗语言解释。
6. 回答要简洁、像项目系统里的智能分析助手。
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt.strip(),
            }
        ]

        if detection_result is not None:
            compact_result = remove_large_fields(detection_result)

            messages.append({
                "role": "user",
                "content": (
                    "下面是 PCB 缺陷检测模型输出的 JSON 结果，请基于它回答用户问题。\n\n"
                    f"detection_result = {json.dumps(compact_result, ensure_ascii=False)}"
                ),
            })

        messages.append({
            "role": "user",
            "content": user_message,
        })

        completion = self.get_client().chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=messages,
            temperature=0.2,
        )

        return completion.choices[0].message.content or ""


qwen_client = QwenClient()