from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# 正则提取 --- 分隔符之间的 YAML frontmatter
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def _parse_skill(skill_path: Path) -> tuple[dict, str]:
    """将 SKILL.md 文件解析为 (frontmatter_dict, body_content)。"""
    raw = skill_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    if match:
        frontmatter = yaml.safe_load(match.group(1)) or {}
        body = raw[match.end():]
    else:
        frontmatter = {}
        body = raw
    return frontmatter, body


def discover_skills() -> list[dict]:
    """扫描 SKILLS_DIR 中的有效技能目录并返回元数据。

    每个有效技能是包含 SKILL.md 的子目录，SKILL.md 的 YAML
    frontmatter 必须包含 'name' 和 'description' 字段。

    返回 dict 列表: [{"name": ..., "description": ...}, ...]
    """
    skills: list[dict] = []
    if not SKILLS_DIR.is_dir():
        return skills

    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            fm, _ = _parse_skill(skill_md)
        except Exception:
            continue
        name = fm.get("name", child.name)
        description = fm.get("description", "")
        if name and description:
            skills.append({"name": name, "description": description})

    return skills


async def execute_use_skill(args: dict, ctx: ToolContext) -> str:
    skill_name = args.get("skill_name", "").strip()
    if not skill_name:
        return json.dumps({"error": "请提供技能名称（skill_name）"}, ensure_ascii=False)

    # 防止路径遍历：只允许小写字母、数字和连字符
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", skill_name):
        return json.dumps(
            {"error": "技能名称只能包含小写字母、数字和连字符"},
            ensure_ascii=False,
        )

    skill_path = (SKILLS_DIR / skill_name / "SKILL.md").resolve()
    if not str(skill_path).startswith(str(SKILLS_DIR.resolve())):
        return json.dumps({"error": "无效的技能名称"}, ensure_ascii=False)

    if not skill_path.is_file():
        available = discover_skills()
        return json.dumps(
            {
                "error": f"技能「{skill_name}」不存在",
                "available_skills": available,
            },
            ensure_ascii=False,
        )

    _, body = _parse_skill(skill_path)
    return body.strip()


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

def register_skill_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="use_skill",
            description=(
                "加载专业技能的详细执行指南。传入技能名称（小写字母、数字和连字符），"
                "返回该技能的完整步骤和格式要求。加载后严格按照指南执行，不要跳步。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "技能名称",
                    },
                },
                "required": ["skill_name"],
            },
        ),
        execute=execute_use_skill,
        display_name="加载技能",
    ))
