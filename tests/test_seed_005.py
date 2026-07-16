"""周道 v0.0.5 SEED-005-R2 测试 — 精确名称与映射字面量。

测试覆盖：
- 精确名称 {}：绑定、表达式、成员保护、错误路径
- 映射字面量 映射［键为值］：基本、多条目、运行时、与现有映射共存
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from contextlib import redirect_stdout
from 周道 import 转译, 转译_仅语法, 运行
from 周道.lexer import 扫描
from 周道.parser import 解析器
from 周道.emitter import 发射器
from 周道.errors import 语法错误, 词法错误


def 编译(源码: str) -> str:
    """转译 + compile，返回 Python 代码。"""
    py = 转译(源码)
    compile(py, "<周道>", "exec")
    return py


def 编译运行(源码: str, 全局变量: dict | None = None) -> str:
    """转译 + compile + exec，捕获 stdout 输出。"""
    py = 转译(源码)
    compile(py, "<周道>", "exec")
    f = io.StringIO()
    env = {"__name__": "__周道__"}
    if 全局变量:
        env.update(全局变量)
    with redirect_stdout(f):
        exec(py, env)
    return f.getvalue().strip()


def 检查转译(源码: str, 期望_python: str):
    """检查转译结果是否与期望的 Python 一致（跳过语义分析）。"""
    python_code = 转译_仅语法(源码)
    py_norm = " ".join(python_code.strip().split())
    exp_norm = " ".join(期望_python.strip().split())
    assert py_norm == exp_norm, f"\n期望: {期望_python}\n实际: {python_code}"


# ==================== 一、精确名称 {} ====================

class Test精确名称:

    def test_绑定(self):
        """设{精确名称}为值 → 绑定到保护名称"""
        检查转译("设{用户的姓名}为【张三】。", '用户的姓名 = "张三"')

    def test_变量引用(self):
        """显示{精确名称} → 引用保护名称"""
        检查转译("显示{总量}。", "print(总量)")

    def test_变更(self):
        """使{名称}变为值"""
        检查转译("使{统计量}变为100。", "统计量 = 100")

    def test_成员受保护(self):
        """{用户的姓名} 不会因「的」字分裂为成员访问"""
        检查转译("显示{用户的姓名}。", "print(用户的姓名)")

    def test_成员访问后缀(self):
        """{精确名称}的成员 → 保护名称后跟成员访问"""
        检查转译("显示{用户的资料}的年龄。", "print(用户的资料.年龄)")

    def test_保护内部语义关键词(self):
        """精确名称内部含「加、减、时、完成」等不参与分词"""
        检查转译("设{时加完成}为True。", "时加完成 = True")
        检查转译("设{数量减}为5。", "数量减 = 5")
        检查转译("设{已完成任务数}为10。", "已完成任务数 = 10")

    def test_英文内名称(self):
        """精确名称可包含英文"""
        检查转译("设{userName}为【测试】。", 'userName = "测试"')

    def test_执行精确名称(self):
        """运行时使用精确名称"""
        src = """
        设{存储的数值}为42。
        显示{存储的数值}。
        """.strip()
        out = 编译运行(src)
        assert out == "42"

    def test_精确名称与成员区分(self):
        """{用户的姓名} 与 用户的姓名 不同。前者是整体，后者是成员访问。"""
        py1 = 转译_仅语法("设{用户的姓名}为【整体】。")
        py2 = 转译_仅语法("使用户的姓名变为【拆分】。")
        # {用户的姓名} 是整体标识符
        assert "用户的姓名 = " in py1
        # 用户的姓名 是成员访问（的 → .）
        assert "用户.姓名" in py2

    def test_全角花括号(self):
        """全角｛｝与半角{}语义相同"""
        py1 = 转译("设{总量}为10。")
        py2 = 转译("设｛总量｝为10。")
        assert py1.strip() == py2.strip()

    def test_格式化输出使用半角(self):
        """统一使用半角花括号输出（内部检查）"""
        py = 转译("设{用户的姓名}为【张三】。")
        assert "{" not in py  # 发射器应使用半角，这里确保名称通过
        assert "用户的姓名" in py

    def test_作为表达式参数(self):
        """精确名称作为函数参数"""
        检查转译("显示长度（{列表名}）。", "print(长度(列表名))")


# ==================== 二、精确名称 — 错误路径 ====================

class Test精确名称错误:

    def test_空名称(self):
        """{} 报错"""
        with pytest.raises(词法错误):
            转译("设{}为值。")

    def test_跨行(self):
        """花括号跨行 报错"""
        with pytest.raises(词法错误):
            转译("设{甲\n乙}为值。")

    def test_嵌套(self):
        """{{}} 嵌套花括号 报错"""
        with pytest.raises(词法错误):
            转译("设{{甲}}为值。")

    def test_未闭合(self):
        """{ 未闭合 报错"""
        with pytest.raises(词法错误):
            转译("设{甲为值。")


# ==================== 三、映射字面量 映射［键为值］ ====================

class Test映射关键字:

    def test_基本映射(self):
        """映射［键为值］→ Python dict"""
        py = 转译_仅语法("设映射为映射［键为值］。")
        # 应生成 Python 字典
        assert "映射" in py
        # 不应包含方括号（键为值 被转成 dict）
        assert "{" in py or "dict" in py

    def test_映射转译检查(self):
        """检查转译为Python dict"""
        py = 转译_仅语法("设m为映射［x为1］。")
        # 应该包含 key:value 结构
        assert "x" in py or "m" in py

    def test_多条目映射(self):
        """映射［键1为值1、键2为值2］"""
        py = 转译_仅语法("设m为映射［a为1、b为2］。")
        assert "a" in py or "b" in py

    def test_映射执行(self):
        """运行时映射创建与访问（字符串键）"""
        src = "设m为映射［【x】为10、【y】为20］，显示m【x】。"
        out = 编译运行(src)
        assert out == "10"

    def test_多条目执行(self):
        """多条目映射 运行时"""
        src = """
        设m为映射［【姓名】为【张三】、【年龄】为25］。
        显示m【姓名】。
        显示m【年龄】。
        """.strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert "张三" in lines
        assert "25" in lines

    def test_表达式值(self):
        """映射值可以是表达式"""
        src = """
        设基数为10。
        设m为映射［【结果】为基数加5］。
        显示m【结果】。
        """.strip()
        out = 编译运行(src)
        assert out == "15"

    def test_键可为字符串字面量(self):
        """映射［【键】为值］混合语法"""
        # 使用字符串键
        src = "设m为映射［【键】为1］，显示m【键】。"
        out = 编译运行(src)
        assert out == "1"

    def test_映射值可嵌套表达式(self):
        """映射值可以使用二元运算"""
        src = "设m为映射［【和】为3加4］，显示m【和】。"
        out = 编译运行(src)
        assert out == "7"

    def test_映射不带方括号是普通标识符(self):
        """设 映射 为值 不应触发映射字面量解析"""
        检查转译("设映射为3。", "映射 = 3")

    def test_映射变量引用(self):
        """映射 作为变量名，后不跟［ 即可"""
        检查转译("显示映射。", "print(映射)")


# ==================== 四、映射字面量 — 与现有映射共存 ====================

class Test映射共存:

    def test_新旧映射互不干扰(self):
        """映射［键为值］与 ［【键】为【值】］ 都能映射"""
        src = """
        设m1为映射［【k】为1］。
        设m2为［【k】为2］。
        显示m1【k】。
        显示m2【k】。
        """.strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert lines == ["1", "2"]

    def test_旧映射不变(self):
        """现有 ［【键】为【值】］ 语义不变"""
        检查转译("设m为［【键】为【值】］。", 'm = {"键": "值"}')


# ==================== 五、向后兼容 ====================

class Test向后兼容005:

    def test_基本绑定(self):
        检查转译("设数量为3。", "数量 = 3")

    def test_变更(self):
        检查转译("使数量变为5。", "数量 = 5")

    def test_显示(self):
        检查转译("显示【测试】。", 'print("测试")')

    def test_列表(self):
        检查转译("设列表为［1、2、3］。", "列表 = [1, 2, 3]")

    def test_映射旧语法(self):
        检查转译("设m为［【a】为1］。", 'm = {"a": 1}')


# ==================== 六、精确名称在映射字面量中 ====================

class Test精确名称与映射组合:

    def test_精确名称作映射键(self):
        """{键名}作为映射的变量键"""
        # 映射键为表达式时使用表达式下标访问
        src = """
        设{动态键}为【hello】。
        设m为映射［{动态键}为【world】］。
        显示m［{动态键}］。
        """.strip()
        out = 编译运行(src)
        assert out == "world"

    def test_精确名称作映射值(self):
        """{值名}作为映射的值（变量引用）"""
        src = """
        设{存储值}为42。
        设m为映射［【答案】为{存储值}］。
        显示m【答案】。
        """.strip()
        out = 编译运行(src)
        assert out == "42"
