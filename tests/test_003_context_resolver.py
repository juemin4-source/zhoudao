"""周道 v0.0.3：ContextResolver 单元测试。

覆盖：
- 完全关键字判定
- 命令上下文关键字（设/使 后）
- 条件上下文关键字
- 控制结构上下文关键字
- 普通标识符位置
"""

import pytest
from 周道.context_resolver import ContextResolver, 语法位置
from 周道.tokens import Token, K_SET, K_MAKE, K_IF, IDENTIFIER
from 周道.tokens import K_TRUE_STATE, OP_EQ, K_THEN, K_EXCEPT
from 周道.tokens import K_NONE, K_AS, K_BECOME, K_ELSE
from 周道.errors import 源码位置

P = 源码位置(行=1, 列=1, 索引=0)


class Test上下文关键字判定:
    def setup_method(self):
        self.resolver = ContextResolver()

    def test_完全关键字(self):
        """设/使/如果 始终是关键字"""
        for kw_type in (K_SET, K_MAKE, K_IF):
            tok = Token(kw_type, "", P)
            pos = 语法位置()
            result = self.resolver.判定(tok, pos)
            assert result.是关键字, f"{kw_type} should be keyword"

    def test_设立是关键字(self):
        tok = Token(K_SET, "设", P)
        pos = 语法位置()
        result = self.resolver.判定(tok, pos)
        assert result.是关键字

    def test_成立在命令位置是关键字(self):
        tok = Token(K_TRUE_STATE, "成立", P)
        pos = 语法位置(前导关键字="K_SET")
        result = self.resolver.判定(tok, pos)
        assert result.是关键字
        assert result.关键字类型 == K_TRUE_STATE

    def test_成立在非命令位置是标识符(self):
        tok = Token(K_TRUE_STATE, "成立", P)
        pos = 语法位置()
        result = self.resolver.判定(tok, pos)
        assert not result.是关键字

    def test_等于在条件位置是关键字(self):
        tok = Token(OP_EQ, "等于", P)
        pos = 语法位置(在条件中=True)
        result = self.resolver.判定(tok, pos)
        assert result.是关键字

    def test_等于在非条件位置不是关键字(self):
        tok = Token(OP_EQ, "等于", P)
        pos = 语法位置()
        result = self.resolver.判定(tok, pos)
        assert not result.是关键字

    def test_就_在控制结构中是关键字(self):
        tok = Token(K_THEN, "就", P)
        pos = 语法位置(在控制结构中=True)
        result = self.resolver.判定(tok, pos)
        assert result.是关键字

    def test_就_非控制位置(self):
        tok = Token(K_THEN, "就", P)
        pos = 语法位置()
        result = self.resolver.判定(tok, pos)
        assert not result.是关键字

    def test_标识符不是关键字(self):
        tok = Token(IDENTIFIER, "用户", P)
        pos = 语法位置()
        result = self.resolver.判定(tok, pos)
        assert not result.是关键字


class TestContextResolverIntegration:
    def test_进入离开上下文(self):
        resolver = ContextResolver()
        assert resolver.当前上下文 == "module"
        resolver.进入上下文("function")
        assert resolver.当前上下文 == "function"
        resolver.进入上下文("if")
        assert resolver.当前上下文 == "if"
        assert resolver.离开上下文() == "if"
        assert resolver.当前上下文 == "function"

    def test_重置(self):
        resolver = ContextResolver()
        resolver.在定义内 = True
        resolver.循环深度 = 3
        resolver.进入上下文("if")
        resolver.重置()
        assert not resolver.在定义内
        assert resolver.循环深度 == 0
        assert resolver.当前上下文 == "module"

    def test_检查名称合法_完全关键字(self):
        resolver = ContextResolver()
        with pytest.raises(Exception, match="完全关键字"):
            resolver.检查名称合法("设", P)

    def test_检查名称合法_普通名称(self):
        resolver = ContextResolver()
        # 不应抛出异常
        resolver.检查名称合法("用户", P)

    def test_建议转义(self):
        resolver = ContextResolver()
        assert resolver.建议转义("设") == "{设}"
        assert resolver.建议转义("没有值") == "{没有值}"


if __name__ == "__main__":
    pytest.main([__file__])
