import base64


def build_image_block(image_bytes: bytes, mime_type: str) -> dict:
    """Build an OpenAI-format image_url content block from raw bytes.

    Returns:
        {"type": "image_url", "image_url": {"url": "data:{mime};base64,{data}"}}
    """
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
    }


def build_multimodal_content(
    text: str, images: list[tuple[bytes, str]]
) -> list[dict]:
    """Build a content block array with text and images.

    Args:
        text: Text content (placed first).
        images: List of (image_bytes, mime_type) tuples.

    Returns:
        OpenAI-format content block array.
    """
    blocks: list[dict] = [{"type": "text", "text": text}]
    for img_bytes, mime in images:
        blocks.append(build_image_block(img_bytes, mime))
    return blocks
