import asyncio
from pathlib import Path
from typing import AsyncGenerator, Any

from app.services.detection_service import detection_service
from app.llm.qwen_client import qwen_client, qwen_available


IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}

VIDEO_SUFFIXES = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".wmv",
    ".flv",
}


def make_event(event_type: str, **kwargs) -> dict[str, Any]:
    return {
        "type": event_type,
        **kwargs,
    }


class DetectionAgent:
    def choose_tool(self, message: str, file_paths: list[str]) -> str:
        message_lower = (message or "").lower()

        if not file_paths:
            return "chat_only"

        suffixes = [
            Path(path).suffix.lower()
            for path in file_paths
        ]

        if len(file_paths) == 1:
            suffix = suffixes[0]

            if suffix == ".zip":
                return "detect_zip"

            if suffix in VIDEO_SUFFIXES:
                return "detect_video"

            return "detect_single"

        if any(suffix in VIDEO_SUFFIXES for suffix in suffixes):
            return "detect_video"

        if "zip" in message_lower:
            return "detect_zip"

        return "detect_batch"

    def make_rule_text_answer(self, message: str) -> str:
        if "缺孔" in message:
            return (
                "PCB 缺孔通常与钻孔工艺、孔位偏移、孔壁异常、阻焊覆盖或图像采集质量有关。"
                "检测时可以重点观察孔区域是否完整、边缘是否清晰，以及是否影响导通。"
            )

        if "短路" in message:
            return (
                "PCB 短路缺陷表示相邻线路之间出现异常连通。"
                "严重程度通常取决于短路位置、连通面积、是否跨越关键走线，以及是否会造成电气功能失效。"
            )

        if "map" in message.lower() or "recall" in message.lower():
            return (
                "mAP50 表示 IoU 阈值为 0.5 时的平均检测精度，Recall 表示真实缺陷中被模型成功检出的比例。"
                "在 PCB 缺陷检测中，Recall 偏低通常意味着漏检风险较高。"
            )

        return (
            "我可以帮助你分析 PCB 缺陷、解释检测结果，也可以在你上传图片、ZIP 或视频后自动调用检测工具。"
            "当前系统支持单图、批量图片、ZIP 和视频检测。"
        )

    async def make_llm_answer(
        self,
        message: str,
        detection_result: dict | None = None,
    ) -> str:
        if not qwen_available():
            if detection_result is not None:
                return self.make_detection_summary(detection_result, detection_result.get("type", "detect_batch"))
            return self.make_rule_text_answer(message)

        try:
            return await asyncio.to_thread(
                qwen_client.chat,
                message,
                detection_result,
            )
        except Exception as exc:
            if detection_result is not None:
                fallback = self.make_detection_summary(
                    detection_result,
                    detection_result.get("type", "detect_batch"),
                )
                return f"{fallback}\n\n注意：Qwen 调用失败，已使用本地规则总结。错误：{exc}"

            return f"{self.make_rule_text_answer(message)}\n\n注意：Qwen 调用失败，已使用本地规则回复。错误：{exc}"

    def make_detection_summary(self, result: dict[str, Any], tool_name: str) -> str:
        result_type = result.get("type") or tool_name

        if result_type in {"single", "detect_single"}:
            total_objects = result.get("total_objects", 0)
            class_stats = result.get("class_stats", [])

            if total_objects == 0:
                return "单图检测完成：当前图片未检测到明显 PCB 缺陷。"

            stats_text = self.format_stats(class_stats)
            return f"单图检测完成：共检测到 {total_objects} 个疑似缺陷。类别统计：{stats_text}。"

        if result_type in {"video", "detect_video"}:
            total_objects = result.get("total_objects", 0)
            processed_frames = result.get("processed_frames", 0)
            total_frames = result.get("total_frames", 0)
            duration_seconds = result.get("duration_seconds", 0)
            class_stats = result.get("class_stats", [])
            stats_text = self.format_stats(class_stats)

            return (
                f"视频检测完成：视频总帧数 {total_frames}，采样处理 {processed_frames} 个关键帧，"
                f"视频时长约 {duration_seconds} 秒，共检测到 {total_objects} 个疑似缺陷。"
                f"类别统计：{stats_text}。"
            )

        total_images = result.get("total_images", 0)
        success_images = result.get("success_images", 0)
        failed_images = result.get("failed_images", 0)
        total_objects = result.get("total_objects", 0)
        class_stats = result.get("class_stats", [])
        stats_text = self.format_stats(class_stats)

        if result_type in {"zip", "detect_zip"}:
            return (
                f"ZIP 检测完成：共解析 {total_images} 张图片，成功检测 {success_images} 张，"
                f"失败 {failed_images} 张，共发现 {total_objects} 个疑似缺陷。类别统计：{stats_text}。"
            )

        return (
            f"批量检测完成：共检测 {total_images} 张图片，成功 {success_images} 张，"
            f"失败 {failed_images} 张，共发现 {total_objects} 个疑似缺陷。类别统计：{stats_text}。"
        )

    def format_stats(self, stats: list[dict[str, Any]]) -> str:
        if not stats:
            return "无明显缺陷"

        return "，".join(
            f"{item.get('class_name', 'unknown')} × {item.get('count', 0)}"
            for item in stats
        )

    async def chat_stream(
        self,
        message: str,
        file_paths: list[str] | None = None,
        conf: float = 0.25,
        iou: float = 0.45,
        device: str = "0",
    ) -> AsyncGenerator[dict[str, Any], None]:
        file_paths = file_paths or []

        try:
            yield make_event(
                "thinking",
                content="正在理解用户意图...",
            )
            await asyncio.sleep(0.05)

            tool_name = self.choose_tool(message, file_paths)

            yield make_event(
                "thinking",
                content=f"已选择处理方式：{tool_name}",
            )
            await asyncio.sleep(0.05)

            if tool_name == "chat_only":
                if qwen_available():
                    yield make_event(
                        "thinking",
                        content="正在调用 Qwen 大模型生成回答...",
                    )
                else:
                    yield make_event(
                        "thinking",
                        content="Qwen 未配置，使用本地规则回答...",
                    )

                answer = await self.make_llm_answer(message)

                for chunk in self.split_text(answer):
                    yield make_event(
                        "text_chunk",
                        content=chunk,
                    )
                    await asyncio.sleep(0.03)

                yield make_event(
                    "done",
                    content=answer,
                    result=None,
                    tool=tool_name,
                )
                return

            yield make_event(
                "tool_call",
                tool=tool_name,
                input={
                    "file_count": len(file_paths),
                    "conf": conf,
                    "iou": iou,
                    "device": device,
                },
            )
            await asyncio.sleep(0.05)

            if tool_name == "detect_single":
                result = detection_service.detect_single(
                    image_path=file_paths[0],
                    conf=conf,
                    iou=iou,
                    device=device,
                )

            elif tool_name == "detect_batch":
                result = detection_service.detect_batch(
                    image_paths=file_paths,
                    conf=conf,
                    iou=iou,
                    device=device,
                )

            elif tool_name == "detect_zip":
                result = detection_service.detect_zip(
                    zip_path=file_paths[0],
                    conf=conf,
                    iou=iou,
                    device=device,
                )

            elif tool_name == "detect_video":
                result = detection_service.detect_video(
                    video_path=file_paths[0],
                    conf=conf,
                    iou=iou,
                    frame_sample_rate=5,
                    max_frames=50,
                    device=device,
                )

            else:
                raise RuntimeError(f"未知工具：{tool_name}")

            yield make_event(
                "tool_result",
                tool=tool_name,
                result=result,
            )
            await asyncio.sleep(0.05)

            if qwen_available():
                yield make_event(
                    "thinking",
                    content="检测完成，正在调用 Qwen 分析检测结果...",
                )

                answer = await self.make_llm_answer(
                    message=message,
                    detection_result=result,
                )
            else:
                answer = self.make_detection_summary(result, tool_name)

            for chunk in self.split_text(answer):
                yield make_event(
                    "text_chunk",
                    content=chunk,
                )
                await asyncio.sleep(0.03)

            yield make_event(
                "done",
                content=answer,
                result=result,
                tool=tool_name,
            )

        except Exception as exc:
            yield make_event(
                "error",
                content=f"处理失败：{exc}",
            )

    def split_text(self, text: str, chunk_size: int = 16) -> list[str]:
        if not text:
            return []

        return [
            text[index:index + chunk_size]
            for index in range(0, len(text), chunk_size)
        ]


detection_agent = DetectionAgent()