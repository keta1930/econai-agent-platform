from __future__ import annotations

import asyncio
import csv
import io
import json
import logging

from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry
from services.storage import storage_service

logger = logging.getLogger(__name__)

# 限制返回行数以控制 token 用量
MAX_PREVIEW_ROWS = 200
MAX_TEXT_CHARS = 50_000


def _parse_xlsx(data: bytes) -> list[list[str]]:
    """将 .xlsx/.xls 字节解析为行列表（表头 + 数据）。"""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []

    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])
        if len(rows) >= MAX_PREVIEW_ROWS + 1:  # +1 表头行
            break

    wb.close()
    return rows


def _parse_csv(data: bytes) -> list[list[str]]:
    """将 CSV 字节解析为行列表。

    先尝试 UTF-8（含 BOM），再回退到 GB18030
    以兼容中文 Windows Excel 导出的文件。
    """
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = data.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        raise ValueError("无法解码 CSV：不支持的编码")

    reader = csv.reader(io.StringIO(text))
    rows: list[list[str]] = []
    for row in reader:
        rows.append(row)
        if len(rows) >= MAX_PREVIEW_ROWS + 1:
            break
    return rows


# 按 MIME 类型分发
_PARSERS: dict[str, type] = {}  # 未使用，通过后缀分发

_XLSX_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
_CSV_MIMES = {
    "text/csv",
    "application/csv",
}


def _parse_text(data: bytes) -> str:
    """解析纯文本 / Markdown 字节，先尝试 UTF-8 再 GB18030。"""
    text: str | None = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        return json.dumps({"error": "文件编码不支持"}, ensure_ascii=False)

    truncated = False
    total_chars = len(text)
    if total_chars > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
        truncated = True

    return json.dumps(
        {
            "content": text,
            "total_chars": total_chars,
            "truncated": truncated,
        },
        ensure_ascii=False,
    )


async def execute_read_file(args: dict, ctx: ToolContext) -> str:
    file_id = args.get("file_id", "").strip()
    if not file_id:
        return json.dumps({"error": "请提供文件 ID（file_id）"}, ensure_ascii=False)

    logger.info("读取文件 — file_id=%s", file_id)

    # file_id 是文件上传时存储的 MinIO 对象路径
    try:
        data = await asyncio.to_thread(storage_service.get_object, file_id)
    except Exception:
        logger.exception("文件下载失败 — file_id=%s", file_id)
        return json.dumps({"error": "文件不存在或无法下载"}, ensure_ascii=False)

    # 根据路径中的文件扩展名确定格式
    lower_path = file_id.lower()
    try:
        if lower_path.endswith((".xlsx", ".xls")):
            rows = await asyncio.to_thread(_parse_xlsx, data)
        elif lower_path.endswith(".csv"):
            rows = await asyncio.to_thread(_parse_csv, data)
        elif lower_path.endswith((".md", ".txt")):
            return await asyncio.to_thread(_parse_text, data)
        else:
            return json.dumps(
                {"error": "不支持的文件格式，仅支持 .xlsx/.xls/.csv/.md/.txt"},
                ensure_ascii=False,
            )
    except Exception:
        logger.exception("文件解析失败 — file_id=%s", file_id)
        return json.dumps({"error": "文件解析失败，请检查文件格式"}, ensure_ascii=False)

    if not rows:
        return json.dumps({"error": "文件为空"}, ensure_ascii=False)

    header = rows[0]
    data_rows = rows[1:]
    truncated = len(data_rows) >= MAX_PREVIEW_ROWS

    return json.dumps(
        {
            "header": header,
            "rows": data_rows,
            "total_rows": len(data_rows),
            "truncated": truncated,
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

def register_file_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="read_file",
            description=(
                "读取教师上传的文件。file_id 从消息中的 [附件: ... | file_id: ...] 标记提取，不要自行编造。\n"
                "支持格式：.xlsx/.xls（表格，最多 200 行预览）、.csv、.md、.txt（最多 50000 字符）。\n"
                "表格返回 header + rows 数组，文本返回 content 字符串。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "上传文件的 ID（即存储路径）",
                    },
                },
                "required": ["file_id"],
            },
        ),
        execute=execute_read_file,
        display_name="读取文件",
    ))
