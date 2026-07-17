"""周道 v0.0.10: 语言服务器 (LSP)。

复用正式编译前端。不复制第二套 Parser/SemanticAnalyzer。
"""
from __future__ import annotations
import json
import sys
from typing import Any


class 周道LSP:
    """周道语言服务器。"""

    def __init__(self):
        self.工作区根: str = ""
        self.文档: dict[str, str] = {}
        self._上次诊断: dict[str, Any] = {}

    def 处理消息(self, 消息: dict):
        msg_id = 消息.get("id")
        method = 消息.get("method")
        params = 消息.get("params", {})

        if not method:
            return  # response

        # 通知（无 id）：didOpen, didChange, didClose, 等
        if msg_id is None:
            self._处理通知(method, params)
            return

        # 请求（有 id）
        self._处理请求(msg_id, method, params)

    def _处理通知(self, method: str, params: dict):
        if method == "textDocument/didOpen":
            uri = params["textDocument"]["uri"]
            self.文档[uri] = params["textDocument"]["text"]
        elif method == "textDocument/didChange":
            uri = params["textDocument"]["uri"]
            changes = params.get("contentChanges", [])
            if changes:
                self.文档[uri] = changes[-1]["text"]
        elif method == "textDocument/didClose":
            self.文档.pop(params["textDocument"]["uri"], None)

    def _处理请求(self, 请求ID: int, method: str, params: dict):
        分发 = {
            "initialize": self._初始化,
            "textDocument/diagnostic": self._诊断,
            "textDocument/semanticTokens/full": self._语义高亮,
            "textDocument/hover": self._悬停,
            "textDocument/definition": self._跳转定义,
            "textDocument/references": self._查找引用,
            "textDocument/completion": self._补全,
            "textDocument/signatureHelp": self._签名提示,
            "textDocument/formatting": self._格式化,
            "shutdown": self._关闭,
        }
        处理函数 = 分发.get(method)
        if 处理函数:
            结果 = 处理函数(params)
            self._发送响应(请求ID, 结果)
        else:
            self._发送响应(请求ID, None)

    # ── 初始化 ──

    def _初始化(self, params: dict) -> dict:
        self.工作区根 = params.get("rootUri", "").replace("file://", "")
        return {
            "capabilities": {
                "textDocumentSync": {"openClose": True, "change": 1},
                "semanticTokensProvider": {
                    "full": True,
                    "legend": {
                        "tokenTypes": [
                            "keyword", "operator", "punctuation", "string", "number",
                            "boolean", "variable", "parameter", "function", "method",
                            "class", "property", "namespace", "type",
                        ],
                        "tokenModifiers": [
                            "declaration", "definition", "readonly", "imported",
                            "async", "generator", "deprecated", "unresolved",
                        ],
                    },
                },
                "hoverProvider": True,
                "definitionProvider": True,
                "referencesProvider": True,
                "completionProvider": {"triggerCharacters": ["。", "的", "（"]},
                "signatureHelpProvider": {"triggerCharacters": ["（"]},
                "documentFormattingProvider": True,
            },
        }

    # ── 编译辅助 ──

    def _编译(self, uri: str):
        """编译文档，返回 (SemanticProgram, tokens, 源码)。"""
        text = self.文档.get(uri, "")
        if not text:
            return None, [], text
        from .lexer import 扫描
        from .parser import 解析器
        from .lowering import 降低
        from .semantic_analyzer import 分析 as 语义分析
        try:
            tokens = 扫描(text)
            parser = 解析器(tokens)
            surface_ast = parser.解析()
            result = 降低(surface_ast)
            sem_prog = 语义分析(result.ir, result.位置映射)
            return sem_prog, tokens, text
        except Exception:
            return None, [], text

    # ── 诊断 ──

    def _诊断(self, params: dict) -> dict:
        uri = params.get("textDocument", {}).get("uri", "")
        sem_prog, tokens, text = self._编译(uri)
        if sem_prog is None:
            return {"kind": "full", "items": []}

        items = []
        for d in sem_prog.诊断列表:
            if d.位置 is None:
                continue
            items.append({
                "range": {
                    "start": {"line": d.位置.行 - 1, "character": d.位置.列 - 1},
                    "end": {"line": d.位置.行 - 1, "character": d.位置.列},
                },
                "severity": 1 if d.级别 == "ERROR" else 2,
                "message": d.消息,
                "source": "周道",
            })
        self._上次诊断[uri] = items
        return {"kind": "full", "items": items}

    # ── 语义高亮 ──

    def _语义高亮(self, params: dict) -> dict:
        uri = params.get("textDocument", {}).get("uri", "")
        sem_prog, tokens, text = self._编译(uri)
        from .tokens import NUMBER, STRING, IDENTIFIER
        from .tokens import K_SET, K_MAKE, K_DEFINE, K_SETUP, K_CATEGORY
        from .tokens import K_PRINT, K_IF, K_WHILE, K_FROM, K_TRY
        from .tokens import K_IMPORT, K_RAISE, K_YIELD, K_AWAIT, K_ENTRY
        from .tokens import K_RERAISE, K_PASS, K_MATCH, K_INTERFACE
        from .tokens import WORD_NEG

        T_KEYWORD = 0
        T_STRING = 3
        T_NUMBER = 4
        T_VARIABLE = 6
        T_FUNCTION = 8
        T_METHOD = 9
        T_CLASS = 10

        # 识别上下文关键字：作为普通名称时的 token
        上下文关键字 = {"集合", "元组", "固定序列", "映射", "错误", "错误内容", "自己"}

        data = []
        prev_line, prev_col = 0, 0

        # 第一遍：收集定义位置
        定义位置: set[tuple[int, int]] = set()
        for i, tok in enumerate(tokens):
            if tok.token_type == K_DEFINE and i + 1 < len(tokens):
                n = tokens[i+1]
                定义位置.add((n.位置.行 - 1, n.位置.列 - 1))
            if tok.token_type == K_SET and i + 1 < len(tokens):
                if tokens[i+1].token_type == IDENTIFIER:
                    n = tokens[i+1]
                    定义位置.add((n.位置.行 - 1, n.位置.列 - 1))

        for tok in tokens:
            line = tok.位置.行 - 1
            col = tok.位置.列 - 1
            length = len(tok.值)
            ttype = T_VARIABLE
            mods = 0

            if tok.token_type == NUMBER:
                ttype = T_NUMBER
            elif tok.token_type == STRING:
                ttype = T_STRING
            elif tok.token_type in (K_DEFINE, K_SET, K_MAKE, K_SETUP, K_PRINT,
                                     K_IF, K_WHILE, K_FROM, K_TRY, K_IMPORT,
                                     K_RAISE, K_YIELD, K_AWAIT, K_ENTRY,
                                     K_RERAISE, K_PASS, K_MATCH, K_INTERFACE,
                                     K_CATEGORY):
                ttype = T_KEYWORD
            elif tok.token_type.startswith("K_"):
                ttype = T_KEYWORD
            elif tok.token_type.startswith("OP_"):
                ttype = T_KEYWORD
            elif tok.token_type.startswith("SYM_"):
                ttype = T_KEYWORD
            elif tok.token_type == WORD_NEG:
                ttype = T_KEYWORD
            elif tok.token_type == IDENTIFIER:
                if tok.是否精确:
                    mods = 2  # readonly
                elif tok.值 in 上下文关键字:
                    mods = 1  # declaration - contextual keyword
                if (line, col) in 定义位置:
                    mods |= 1  # definition modifier

            data.append(line - prev_line)
            if line == prev_line:
                data.append(col - prev_col)
            else:
                data.append(col)
            data.append(length)
            data.append(ttype)
            data.append(mods)
            prev_line, prev_col = line, col

        return {"data": data}

    # ── 悬停 ──

    def _悬停(self, params: dict) -> dict | None:
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line, col = pos.get("line", 0), pos.get("character", 0)
        sem_prog, tokens, text = self._编译(uri)
        if sem_prog is None:
            return None

        # 查找光标所在 token
        for tok in tokens:
            t_line = tok.位置.行 - 1
            t_col = tok.位置.列 - 1
            t_end = t_col + len(tok.值)
            if t_line == line and t_col <= col <= t_end:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"**{tok.值}**\n\n类型: `{tok.token_type}`\n来源: 周道",
                    }
                }
        return None

    # ── 跳转定义 ──

    def _跳转定义(self, params: dict) -> dict | None:
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line, col = pos.get("line", 0), pos.get("character", 0)
        sem_prog, tokens, text = self._编译(uri)
        if not tokens:
            return None

        # 找到光标下的名称
        from .tokens import IDENTIFIER
        target_name = None
        for tok in tokens:
            t_line = tok.位置.行 - 1
            t_col = tok.位置.列 - 1
            t_end = t_col + len(tok.值)
            if tok.token_type == IDENTIFIER and t_line == line and t_col <= col <= t_end:
                target_name = tok.值
                break

        if not target_name:
            return None

        # 查找定义位置：设<名称> 或 定义<名称> 所在行
        for i, tok in enumerate(tokens):
            if (tok.token_type in (self._K_SET(), self._K_DEFINE())
                    and i + 1 < len(tokens)
                    and tokens[i+1].token_type == IDENTIFIER
                    and tokens[i+1].值 == target_name):
                t = tokens[i+1]
                return {
                    "uri": uri,
                    "range": {
                        "start": {"line": t.位置.行 - 1, "character": t.位置.列 - 1},
                        "end": {"line": t.位置.行 - 1, "character": t.位置.列 - 1 + len(t.值)},
                    },
                }

        return None

    def _K_SET(self):
        from .tokens import K_SET
        return K_SET

    def _K_DEFINE(self):
        from .tokens import K_DEFINE
        return K_DEFINE

    # ── 查找引用 ──

    def _查找引用(self, params: dict) -> dict:
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line, col = pos.get("line", 0), pos.get("character", 0)
        sem_prog, tokens, text = self._编译(uri)
        if not tokens:
            return {"data": []}

        from .tokens import IDENTIFIER
        target_name = None
        for tok in tokens:
            t_line = tok.位置.行 - 1
            t_col = tok.位置.列 - 1
            if tok.token_type == IDENTIFIER and t_line == line and t_col <= col <= t_col + len(tok.值):
                target_name = tok.值
                break

        if not target_name:
            return {"data": []}

        locations = []
        for tok in tokens:
            if tok.token_type == IDENTIFIER and tok.值 == target_name:
                locations.append({
                    "uri": uri,
                    "range": {
                        "start": {"line": tok.位置.行 - 1, "character": tok.位置.列 - 1},
                        "end": {"line": tok.位置.行 - 1, "character": tok.位置.列 - 1 + len(tok.值)},
                    },
                })

        return {"data": locations}

    # ── 补全 ──

    def _补全(self, params: dict) -> dict:
        uri = params.get("textDocument", {}).get("uri", "")
        sem_prog, tokens, text = self._编译(uri)
        items = []
        if sem_prog:
            # 从作用域列表提供名称补全
            seen: set[str] = set()
            for scope in sem_prog.作用域列表:
                for name in scope.名称列表:
                    if name not in seen and not name.startswith("__"):
                        seen.add(name)
                        items.append({"label": name, "kind": 6, "detail": "变量"})
        return {"isIncomplete": False, "items": items[:50]}

    # ── 签名提示 ──

    def _签名提示(self, params: dict) -> dict | None:
        return None

    # ── 格式化 ──

    def _格式化(self, params: dict) -> list[dict]:
        uri = params.get("textDocument", {}).get("uri", "")
        text = self.文档.get(uri, "")
        if not text:
            return []
        from .formatter import 格式化
        options = params.get("options", {})
        tab_size = options.get("tabSize", 4)
        行宽 = tab_size * 2 + 60
        结果 = 格式化(text, 行宽)
        lines = text.split("\n")
        return [{"newText": 结果, "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": len(lines), "character": 0},
        }}]

    def _关闭(self) -> None:
        sys.exit(0)

    # ── 协议 ──

    def _发送(self, 消息: dict):
        body = json.dumps(消息, ensure_ascii=False)
        header = f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n"
        sys.stdout.buffer.write(header.encode())
        sys.stdout.buffer.write(body.encode("utf-8"))
        sys.stdout.buffer.flush()

    def _发送响应(self, 请求ID: int, 结果: Any):
        self._发送({"id": 请求ID, "result": 结果})


def 启动LSP(项目目录: str = "."):
    """启动 LSP 服务器主循环。"""
    server = 周道LSP()
    buffer = ""
    while True:
        try:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                break
            buffer += chunk.decode("utf-8")
            while "\r\n\r\n" in buffer:
                header, buffer = buffer.split("\r\n\r\n", 1)
                length = 0
                for line in header.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        length = int(line.split(":")[1].strip())
                if len(buffer) >= length:
                    body = buffer[:length]
                    buffer = buffer[length:]
                    try:
                        server.处理消息(json.loads(body))
                    except json.JSONDecodeError:
                        pass
        except (EOFError, KeyboardInterrupt, ConnectionError):
            break
