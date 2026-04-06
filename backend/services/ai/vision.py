import base64
import logging

logger = logging.getLogger(__name__)


def build_image_block(image_bytes: bytes, mime_type: str) -> dict:
    """从原始字节构建 OpenAI 格式的 image_url 内容块。

    返回:
        {"type": "image_url", "image_url": {"url": "data:{mime};base64,{data}"}}
    """
    b64 = base64.b64encode(image_bytes).decode("ascii")
    logger.info("图片编码完成 — 类型=%s, 大小=%d 字节", mime_type, len(image_bytes))
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
    }


def build_multimodal_content(
    text: str, images: list[tuple[bytes, str]]
) -> list[dict]:
    """构建包含文本和图片的内容块数组。

    参数:
        text: 文本内容（放在最前面）。
        images: (image_bytes, mime_type) 元组列表。

    返回:
        OpenAI 格式的内容块数组。
    """
    logger.info("构建多模态内容 — 图片数量=%d", len(images))
    blocks: list[dict] = [{"type": "text", "text": text}]
    for img_bytes, mime in images:
        blocks.append(build_image_block(img_bytes, mime))
    return blocks
