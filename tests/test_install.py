"""验证 Skill 安装入口：完整包可安装、可从不同工作目录运行、重复安装行为安全。

通过子进程运行仓库根目录 install.py 的真实命令，只观察退出码、输出与目标目录
结果，不调用其内部函数。安装源默认是仓库内 skills/zeno-waytoagi 完整包；
--source 仅用于构造含临时文件的受控源，验证排除行为。
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).parents[1]
INSTALL = REPO_ROOT / "install.py"
SKILL_PACKAGE = REPO_ROOT / "skills" / "zeno-waytoagi"


def run_install(arguments, cwd):
    """以指定工作目录运行 install.py；输入参数列表和 cwd，返回 CompletedProcess。"""
    return subprocess.run(
        [sys.executable, str(INSTALL), *arguments],
        capture_output=True, text=True, cwd=cwd, check=False,
    )


def package_files(root):
    """收集目录下包文件的相对路径，不含缓存等临时产物；输入目录 Path，返回排序列表。"""
    transient = {".DS_Store", "__pycache__"}
    return sorted(
        str(path.relative_to(root)) for path in root.rglob("*")
        if path.is_file() and not any(part in transient for part in path.relative_to(root).parts)
    )


class FreshInstallTests(unittest.TestCase):
    """完整包从未安装过的目标目录应可安装，且与调用方工作目录无关。"""

    def test_fresh_install_from_other_cwd(self):
        """从任意工作目录执行安装后，目标出现与源一致的完整 Skill 包。"""
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as other_cwd:
            process = run_install(["--target", target_dir], cwd=other_cwd)
            self.assertEqual(process.returncode, 0, process.stderr)
            installed = Path(target_dir) / "zeno-waytoagi"
            self.assertEqual(package_files(installed), package_files(SKILL_PACKAGE))
            self.assertEqual(
                (installed / "SKILL.md").read_text(),
                (SKILL_PACKAGE / "SKILL.md").read_text(),
            )

    def test_install_excludes_transient_files(self):
        """源目录中的 Python 缓存与系统垃圾文件不进入安装结果。"""
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source = Path(source_dir) / "zeno-waytoagi"
            shutil.copytree(SKILL_PACKAGE, source)
            (source / "scripts" / "__pycache__").mkdir(exist_ok=True)
            (source / "scripts" / "__pycache__" / "waytoagi_daily.cpython-314.pyc").write_text("cache")
            (source / ".DS_Store").write_text("junk")
            process = run_install(["--source", str(source), "--target", target_dir], cwd=target_dir)
            self.assertEqual(process.returncode, 0, process.stderr)
            installed = Path(target_dir) / "zeno-waytoagi"
            self.assertEqual(package_files(installed), package_files(SKILL_PACKAGE))


class ReinstallSafetyTests(unittest.TestCase):
    """目标已存在时的重复安装必须安全：一致跳过，冲突保全，不静默覆盖。"""

    def test_reinstall_identical_content_is_safe(self):
        """目标内容与安装源一致时，重复安装安全跳过且不改动任何文件。"""
        with tempfile.TemporaryDirectory() as target_dir:
            first = run_install(["--target", target_dir], cwd=target_dir)
            self.assertEqual(first.returncode, 0, first.stderr)
            installed = Path(target_dir) / "zeno-waytoagi"
            before = {path: (installed / path).stat().st_mtime_ns for path in package_files(installed)}
            second = run_install(["--target", target_dir], cwd=target_dir)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("already_installed", second.stdout)
            after = {path: (installed / path).stat().st_mtime_ns for path in package_files(installed)}
            self.assertEqual(before, after)

    def test_conflicting_target_is_preserved(self):
        """目标已有不同内容时默认拒绝安装、原内容原样保留、输出说明冲突。"""
        with tempfile.TemporaryDirectory() as target_dir:
            first = run_install(["--target", target_dir], cwd=target_dir)
            self.assertEqual(first.returncode, 0, first.stderr)
            installed = Path(target_dir) / "zeno-waytoagi"
            marker = installed / "SKILL.md"
            marker.write_text("用户本地修改过的内容")
            second = run_install(["--target", target_dir], cwd=target_dir)
            self.assertEqual(second.returncode, 1)
            self.assertIn("TARGET_CONFLICT", second.stdout)
            self.assertEqual(marker.read_text(), "用户本地修改过的内容")

    def test_force_preserves_existing_as_backup(self):
        """显式 --force 时原目录被重命名备份，新内容完整就位，两者并存。"""
        with tempfile.TemporaryDirectory() as target_dir:
            first = run_install(["--target", target_dir], cwd=target_dir)
            self.assertEqual(first.returncode, 0, first.stderr)
            installed = Path(target_dir) / "zeno-waytoagi"
            (installed / "SKILL.md").write_text("用户本地修改过的内容")
            second = run_install(["--target", target_dir, "--force"], cwd=target_dir)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("installed_with_backup:", second.stdout)
            backup = Path(target_dir) / second.stdout.split("installed_with_backup:", 1)[1].strip()
            self.assertEqual((backup / "SKILL.md").read_text(), "用户本地修改过的内容")
            self.assertEqual((installed / "SKILL.md").read_text(), (SKILL_PACKAGE / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
