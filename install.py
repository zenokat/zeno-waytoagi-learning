"""将仓库内 skills/zeno-waytoagi 完整包安装到用户选定的 Skill 目录。

只复制 Skill 包内容（SKILL.md、scripts、references 等包内文件），排除 Python
缓存等临时产物，不携带仓库工程文件、Git 历史或任何凭证。目标目录已有
zeno-waytoagi 时逐文件对比：内容一致则安全跳过；内容不同则保全原目录并拒绝
静默覆盖，由调用方决定删除重装或显式 --force（先把原目录备份到旁边再安装）。
退出码：0 安装成功或已一致；1 冲突、源不完整或目标不可写；2 参数用法错误。
"""

import argparse
import filecmp
from pathlib import Path
import shutil
import sys


SKILL_NAME = "zeno-waytoagi"
DEFAULT_SOURCE = Path(__file__).resolve().parent / "skills" / SKILL_NAME
TRANSIENT_NAMES = {".DS_Store", "__pycache__"}


def package_files(root):
    """收集目录下全部文件的相对路径；输入目录 Path，返回相对 Path 的集合。"""
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def ignore_transient(directory, names):
    """shutil.copytree 的排除回调；输入当前目录与条目名，返回应排除的临时产物名。"""
    return {name for name in names if name in TRANSIENT_NAMES or name.endswith((".pyc", ".pyo"))}


def validate_source(source):
    """确认安装源是完整的 Skill 包；输入源目录 Path，缺失关键文件时抛 ValueError。"""
    if not (source / "SKILL.md").is_file():
        raise ValueError(f"SOURCE_INCOMPLETE: 安装源缺少 SKILL.md：{source}")


def directories_match(source, target):
    """逐文件对比两个目录内容；输入两个 Path，完全一致返回 True，否则 False。"""
    source_files = {path for path in package_files(source) if not any(part in TRANSIENT_NAMES for part in path.parts)}
    target_files = {path for path in package_files(target) if not any(part in TRANSIENT_NAMES for part in path.parts)}
    if source_files != target_files:
        return False
    _match, mismatch, errors = filecmp.cmpfiles(source, target, [str(path) for path in source_files], shallow=False)
    return not mismatch and not errors


def install(source, target_root, force=False):
    """执行安装；输入源目录、目标父目录和是否强制，返回描述结果的字符串。

    目标不存在时直接复制；已存在且内容一致时返回 already_installed；
    已存在且内容不同时，force 为假抛 FileExistsError 保全原目录，
    force 为真先把原目录重命名为带序号的备份再安装。
    """
    validate_source(source)
    target = target_root / SKILL_NAME
    if target.exists():
        if directories_match(source, target):
            return "already_installed"
        if not force:
            raise FileExistsError(f"TARGET_CONFLICT: {target} 已存在且内容与安装源不同；未做任何改动")
        backup = target.with_name(f"{SKILL_NAME}.backup")
        counter = 1
        while backup.exists():
            backup = target.with_name(f"{SKILL_NAME}.backup-{counter}")
            counter += 1
        target.rename(backup)
        shutil.copytree(source, target, ignore=ignore_transient)
        return f"installed_with_backup:{backup}"
    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=ignore_transient)
    return "installed"


def main():
    """解析参数并执行安装；返回 0 表示成功或已一致，1 表示冲突或失败。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="用户选定的 Skill 父目录，包安装为其下 zeno-waytoagi")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="安装源目录；省略时为仓库内 skills/zeno-waytoagi")
    parser.add_argument("--force", action="store_true", help="目标内容不同时先备份原目录再安装")
    args = parser.parse_args()
    try:
        outcome = install(args.source.resolve(), args.target.expanduser().resolve(), force=args.force)
    except (OSError, ValueError) as error:
        print(str(error))
        return 1
    print(outcome)
    return 0


if __name__ == "__main__":
    sys.exit(main())
