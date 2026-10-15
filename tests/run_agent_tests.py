"""在已有独立登录的 Docker 容器中重复运行 Agent 场景，结束后恢复 CLI 入口。

用法：python3 tests/run_agent_tests.py --container NAME --report /tmp/results.json
只复制本项目的 Skill 与测试，不复制宿主凭证。容器必须无宿主挂载且非特权。
CLI 原符号链接先保全再替换，finally 恢复；没有活跃测试时阻断业务请求。
此文件是测试驱动，不属于分发给用户的 Skill，也不是安装工具。
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


REPOSITORY = Path(__file__).resolve().parents[1]


def docker(arguments, **options):
    """执行 Docker 参数列表；输入 argv 与进程选项，检查错误并返回进程结果。"""
    return subprocess.run(["docker", *arguments], check=True, text=True, **options)


def container_python(container, source):
    """在目标容器的 root 进程执行本测试的固定管理脚本；输入容器名和脚本，返回结果。"""
    return docker(["exec", "-i", container, "python3", "-"], input=source, capture_output=True)


def install_quarantine(container, directory):
    """保全两个 CLI 符号链接并安装替身入口；输入容器及临时目录，无返回值。

    拦截实际命令入口，避免登录 Shell 重置 PATH 后错误调用真实服务。
    官方指南仅在无活跃合成场景时允许直接读取，业务请求始终不得回落到真实 CLI。
    """
    wrapper = directory + "/quarantine_cli.py"
    active = directory + "/active.json"
    fixture = directory + "/tests/agent_fixture_cli.py"
    source = f'''#!/usr/bin/env python3
import json,os
from pathlib import Path
import sys
active=Path({active!r})
try:
    state=json.loads(active.read_text())
    valid=Path(state['control']).is_dir()
except (OSError,ValueError,KeyError):
    valid=False
if valid:
    os.environ['WAYTOAGI_EVAL_CONTROL']=state['control']
    os.environ['WAYTOAGI_EVAL_CASE']=state['case']
    os.execv('/usr/bin/python3',['python3',{fixture!r},*sys.argv[1:]])
if sys.argv[1:3]==['skills','read'] or sys.argv[1:]==['--version']:
    original=Path({directory!r}+'/original.json').read_text()
    path=json.loads(original)['target']
    os.execv(path,[path,*sys.argv[1:]])
sys.exit('Test quarantine: no active fixture; real business calls blocked')
'''
    management = f'''
import json,os,pwd
from pathlib import Path
directory=Path({directory!r})
links=[Path('/usr/local/bin/lark-cli'),Path('/home/setup-agent/.local/bin/lark-cli')]
if not all(p.is_symlink() and not p.with_name(p.name+'.waytoagi-eval-original').is_symlink() for p in links):
    raise RuntimeError('CLI入口不是预期符号链接，或已有未恢复测试；停止，不覆盖')
targets={{str(p.resolve()) for p in links}}
if len(targets)!=1:
    raise RuntimeError('两个CLI入口指向不同目标，停止')
(directory/'original.json').write_text(json.dumps({{'target':targets.pop()}}))
wrapper=Path({wrapper!r})
wrapper.write_text({source!r})
wrapper.chmod(0o755)
active=Path({active!r})
active.write_text('{{}}')
account=pwd.getpwnam('setup-agent')
os.chown(active,account.pw_uid,account.pw_gid)
for path in links:
    path.rename(path.with_name(path.name+'.waytoagi-eval-original'))
    path.symlink_to(wrapper)
'''
    container_python(container, management)


def restore_quarantine(container, directory):
    """核对仍是本测试入口后恢复原链接；输入容器和临时目录，无返回值，不覆盖外部变化。"""
    management = f'''
from pathlib import Path
wrapper=Path({directory!r})/'quarantine_cli.py'
for path in [Path('/usr/local/bin/lark-cli'),Path('/home/setup-agent/.local/bin/lark-cli')]:
    backup=path.with_name(path.name+'.waytoagi-eval-original')
    if not backup.is_symlink():
        continue
    if not path.is_symlink() or path.resolve()!=wrapper:
        raise RuntimeError('CLI入口在测试中被其他操作改变；保留备份，不覆盖')
    path.unlink()
    backup.rename(path)
'''
    container_python(container, management)


def main():
    """检查隔离容器、复制测试、运行并恢复入口；读取命令行，返回测试进程退出码。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True, help="已独立登录 Codex 并安装 CLI 的测试容器")
    parser.add_argument("--report", type=Path, required=True, help="合成场景证据的本地输出文件")
    parser.add_argument("--case", action="append", help="可选的 unittest -k 场景名筛选，可重复")
    parser.add_argument("--live-setup", action="store_true", help="另启一次真实已授权 setup；只读白名单禁止登录和改权限")
    arguments = parser.parse_args()
    state = json.loads(docker(["inspect", arguments.container], capture_output=True).stdout)[0]
    if state["HostConfig"]["Privileged"] or state["Mounts"]:
        parser.error("仅允许无宿主挂载、非特权的独立测试容器")
    directory = "/tmp/waytoagi-behavior-" + uuid.uuid4().hex[:12]
    docker(["exec", arguments.container, "mkdir", "-p", directory])
    for name in ["skills", "tests"]:
        docker(["cp", str(REPOSITORY / name), arguments.container + ":" + directory + "/"])
    report = directory + "-results.json"
    installed = False
    try:
        install_quarantine(arguments.container, directory)
        installed = True
        command = ["exec", "--user", "setup-agent", "-w", directory,
                   "-e", "WAYTOAGI_AGENT_EVAL=1", "-e", "WAYTOAGI_AGENT_SANDBOX=danger-full-access",
                   "-e", "WAYTOAGI_AGENT_ACTIVE_FILE=" + directory + "/active.json",
                   "-e", "WAYTOAGI_AGENT_REPORT=" + report]
        if arguments.live_setup:
            original = json.loads(container_python(arguments.container, f"from pathlib import Path; print(Path({directory!r}+'/original.json').read_text())").stdout)
            command += ["-e", "WAYTOAGI_AGENT_LIVE=1", "-e", "WAYTOAGI_AGENT_REAL_CLI=" + original["target"]]
        for name in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
            if os.environ.get(name):
                command += ["-e", name + "=" + os.environ[name]]
        command += [arguments.container, "python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_waytoagi_agent.py", "-v"]
        for pattern in arguments.case or []:
            command += ["-k", pattern]
        completed = subprocess.run(["docker", *command])
        docker(["cp", arguments.container + ":" + report, str(arguments.report)])
        return completed.returncode
    finally:
        if installed:
            restore_quarantine(arguments.container, directory)


if __name__ == "__main__":
    sys.exit(main())
