"""editor_bridge — VS Code 扩展的薄桥接层。

供 VS Code 扩展通过子进程调用，格式为：
  python -m 周道.editor_bridge check <file>
  python -m 周道.editor_bridge run <file>

每次调用只向 stdout 输出一个合法 JSON 对象。
不建立第二套编译器，不发明新诊断分类。
"""

import sys
import os
import io
import json
import traceback

# ── 编码修复 ──
for _s in (sys.stdout, sys.stderr):
    if _s and hasattr(_s, 'reconfigure'):
        try: _s.reconfigure(encoding='utf-8', errors='replace')
        except Exception: pass
    elif _s and hasattr(_s, 'detach'):
        try: _s = io.TextIOWrapper(_s.detach(), encoding='utf-8', errors='replace')
        except Exception: pass
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception: pass

PROTOCOL_VERSION = 1


def _result(mode: str, file: str, ok: bool = True, stdout: str = "",
            stderr: str = "", diagnostics: list = None) -> str:
    return json.dumps({
        "protocolVersion": PROTOCOL_VERSION,
        "ok": ok,
        "mode": mode,
        "file": os.path.abspath(file),
        "stdout": stdout,
        "stderr": stderr,
        "diagnostics": diagnostics or [],
    }, ensure_ascii=False)


def _diag(severity: str, stage: str, msg: str, file: str,
          start_line: int = 1, start_col: int = 1,
          end_line: int = None, end_col: int = None) -> dict:
    return {
        "severity": severity,
        "stage": stage,
        "code": None,
        "message": msg,
        "file": os.path.abspath(file),
        "startLine": start_line,
        "startColumn": start_col,
        "endLine": end_line or start_line,
        "endColumn": end_col or start_col + 1,
    }


def cmd_check(file: str) -> str:
    if not os.path.isfile(file):
        return _result("check", file, ok=False, diagnostics=[
            _diag("error", "runtime", f"文件不存在: {file}", file)])
    try:
        from 周道 import 转译
        py = 转译(open(file, encoding="utf-8").read())
        compile(py, "<周道>", "exec")
        return _result("check", file, ok=True, stdout="语法检查通过")
    except SyntaxError as e:
        行 = e.lineno or 1
        return _result("check", file, ok=False, diagnostics=[
            _diag("error", "backend", str(e), file, start_line=行)])
    except Exception as e:
        stage = "runtime"
        msg = str(e)
        line = 1
        col = 1
        if hasattr(e, "位置") and e.位置:
            line = e.位置.行
            col = e.位置.列 if hasattr(e.位置, "列") else 1
        return _result("check", file, ok=False, diagnostics=[
            _diag("error", stage, msg, file, start_line=line, start_col=col)])


def cmd_run_selection(code: str) -> str:
    """运行选中的周道代码片段（不依赖文件）。"""
    try:
        import io as _io
        from contextlib import redirect_stdout, redirect_stderr
        from 周道 import 转译
        py_code = 转译(code)
        buf_out = _io.StringIO()
        buf_err = _io.StringIO()
        env = {"__name__": "__周道__"}
        from 周道.runtime_environment import 注入运行时助手
        注入运行时助手(env)
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            exec(py_code, env)
        return _result("run_selection", "(选中代码)", True,
                        stdout=buf_out.getvalue(), stderr=buf_err.getvalue())
    except Exception as e:
        return _result("run_selection", "(选中代码)", ok=False,
                        stderr=f"[runtime] {e}",
                        diagnostics=[_diag("error", "runtime", str(e), "(选中代码)")])


def cmd_run(file: str) -> str:
    if not os.path.isfile(file):
        return _result("run", file, ok=False, stderr=f"文件不存在: {file}")
    try:
        import io as _io
        from contextlib import redirect_stdout, redirect_stderr
        from 周道 import 转译
        src = open(file, encoding="utf-8").read()
        py_code = 转译(src)
        buf_out = _io.StringIO()
        buf_err = _io.StringIO()
        env = {"__name__": "__周道__"}
        from 周道.runtime_environment import 注入运行时助手
        注入运行时助手(env)
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            exec(py_code, env)
        return _result("run", file, True, stdout=buf_out.getvalue(), stderr=buf_err.getvalue())
    except Exception as e:
        stage = "runtime"
        msg = str(e)
        line = 1
        col = 1
        if hasattr(e, "位置") and e.位置:
            line = e.位置.行
            col = getattr(e.位置, "列", 1)
        return _result("run", file, ok=False,
                        stderr=f"[{stage}] {msg}",
                        diagnostics=[_diag("error", stage, msg, file,
                                          start_line=line, start_col=col)])


def main():
    args = sys.argv[1:]
    if not args:
        result = json.dumps({
            "protocolVersion": PROTOCOL_VERSION,
            "ok": False,
            "error": "用法: python -m 周道.editor_bridge check|run|run_selection [<file>]",
        }, ensure_ascii=False)
        print(result)
        sys.exit(1)

    mode = args[0]
    if mode not in ("check", "run", "run_selection"):
        result = json.dumps({
            "protocolVersion": PROTOCOL_VERSION,
            "ok": False,
            "error": f"未知模式: {mode}（可用: check|run|run_selection）",
        }, ensure_ascii=False)
        print(result)
        sys.exit(1)

    if mode == "run_selection" and len(args) > 1:
        # 允许 run_selection 从参数读取代码（兼容 CLI 测试）
        code = args[1]
    else:
        code = None

    try:
        if mode == "check":
            output = cmd_check(args[1])
        elif mode == "run":
            output = cmd_run(args[1])
        elif mode == "run_selection":
            # 从参数或 stdin 读取选中代码
            if code:
                output = cmd_run_selection(code)
            else:
                code = sys.stdin.read()
                output = cmd_run_selection(code)
        else:
            output = json.dumps({"protocolVersion": PROTOCOL_VERSION, "ok": False,
                "error": f"未知模式: {mode}"}, ensure_ascii=False)
        print(output)
    except Exception as e:
        print(_result(mode, args[1] if len(args) > 1 else "(代码)",
                       ok=False, stderr=f"桥接内部错误: {e}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
