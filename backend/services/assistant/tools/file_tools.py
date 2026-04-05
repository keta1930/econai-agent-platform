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

# Limit rows returned to keep token usage reasonable
MAX_PREVIEW_ROWS = 200


def _parse_xlsx(data: bytes) -> list[list[str]]:
    """Parse .xlsx/.xls bytes into a list of rows (header + data)."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []

    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])
        if len(rows) >= MAX_PREVIEW_ROWS + 1:  # +1 for header
            break

    wb.close()
    return rows


def _parse_csv(data: bytes) -> list[list[str]]:
    """Parse CSV bytes into a list of rows.

    Tries UTF-8 (with BOM) first, then falls back to GB18030 for
    files exported from Chinese Windows Excel.
    """
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = data.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        raise ValueError("Unable to decode CSV: unsupported encoding")

    reader = csv.reader(io.StringIO(text))
    rows: list[list[str]] = []
    for row in reader:
        rows.append(row)
        if len(rows) >= MAX_PREVIEW_ROWS + 1:
            break
    return rows


# Dispatch by MIME type
_PARSERS: dict[str, type] = {}  # unused, dispatch via suffix below

_XLSX_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
_CSV_MIMES = {
    "text/csv",
    "application/csv",
}


async def execute_read_file(args: dict, ctx: ToolContext) -> str:
    file_id = args.get("file_id", "").strip()
    if not file_id:
        return json.dumps({"error": "请提供文件 ID（file_id）"}, ensure_ascii=False)

    # file_id is the MinIO object path stored when the file was uploaded
    try:
        data = await asyncio.to_thread(storage_service.get_object, file_id)
    except Exception:
        logger.exception("Failed to download file: %s", file_id)
        return json.dumps({"error": "文件不存在或无法下载"}, ensure_ascii=False)

    # Determine format from file extension in the path
    lower_path = file_id.lower()
    try:
        if lower_path.endswith((".xlsx", ".xls")):
            rows = await asyncio.to_thread(_parse_xlsx, data)
        elif lower_path.endswith(".csv"):
            rows = await asyncio.to_thread(_parse_csv, data)
        else:
            return json.dumps(
                {"error": f"不支持的文件格式，仅支持 .xlsx/.xls/.csv"},
                ensure_ascii=False,
            )
    except Exception:
        logger.exception("Failed to parse file: %s", file_id)
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
# Registration
# ---------------------------------------------------------------------------

def register_file_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="read_file",
            description=(
                "读取用户上传的文件，返回结构化数据。"
                "支持 Excel (.xlsx/.xls) 和 CSV (.csv) 格式。"
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
