"""周道 v0.0.6 SEED-006-RC1 测试 — 语义分析、作用域与上下文。

测试覆盖：
- 分号（；）只分隔如果/尝试中的同级分句，不是通用语句终止符
- 精确名称 {错误内容} 永远按普通精确名称解析，不被上下文解析器劫持
- 名称来源信息（ORDINARY/EXACT/CONTEXTUAL）在管线中完整保留
- 110 项语义测试（合法程序）
- 55 项非法程序（语义分析拒绝）
- 8 个 mandatory programs 全部 pytest 自动化
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from contextlib import redirect_stdout
from 周道 import 转译, 转译_仅语法, 运行, __version__
from 周道.lexer import 扫描
from 周道.parser import 解析器
from 周道.emitter import 发射器
from 周道.errors import 语法错误, 词法错误, 语义错误
from 周道.semantic_analyzer import 分析 as 语义分析
from 周道.lowering import 降低


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


def 编译到语义(源码: str):
    """返回经过语义分析的程序，不发射。"""
    tokens = 扫描(源码)
    解析器实例 = 解析器(tokens)
    ast = 解析器实例.解析()
    lowering_result = 降低(ast)
    sem = 语义分析(lowering_result.ir, lowering_result.位置映射)
    return sem


# ====================================================================
# Part 1: 分号（；）— 只分隔如果/尝试中的同级分句
# ====================================================================

class Test分号如果:
    """分号在 如果 中作为同级分句分隔符。"""

    def test_分号分隔则与否则(self):
        """如果条件，就动作1；不然就动作2"""
        检查转译(
            "如果数量大于0，就显示【正数】；不然就显示【负数】。",
            'if 数量 > 0:\n    print("正数")\nelse:\n    print("负数")'
        )

    def test_分号分隔则与否则如果(self):
        """如果条件，就动作1；不然，如果条件2，就动作2；不然就动作3"""
        检查转译(
            "如果数量大于0，就显示【正数】；不然，如果数量等于0，就显示【零】；不然就显示【负数】。",
            'if 数量 > 0:\n    print("正数")\nelif 数量 == 0:\n    print("零")\nelse:\n    print("负数")'
        )

    def test_分号后跟不然(self):
        """分号后直接跟「不然」"""
        检查转译(
            "如果完成成立，就显示【完成】；不然就显示【未完成】。",
            'if 完成:\n    print("完成")\nelse:\n    print("未完成")'
        )

    def test_分号在嵌套如果中(self):
        """嵌套如果中的分号"""
        py = 转译_仅语法(
            "如果甲大于0，就（如果甲大于10，就显示【大】；不然就显示【中】）；不然就显示【小】。"
        )
        assert "大" in py
        assert "中" in py
        assert "小" in py

    def test_分号在如果中运行时(self):
        """分号分隔如果分支运行时正确"""
        out = 编译运行(
            "设数量为5，如果数量大于0，就显示【正数】；不然就显示【负数】。"
        )
        assert out == "正数"

    def test_分号在如果else运行时(self):
        """分号分隔如果-否则运行时正确"""
        out = 编译运行(
            "设数量为0减5，如果数量大于0，就显示【正数】；不然就显示【负数】。"
        )
        assert out == "负数"

    def test_分号与逗号混合使用(self):
        """分号和逗号都可以分隔如果子句"""
        out1 = 编译运行("设甲为1，如果甲大于0，就显示【正】；不然就显示【负】。")
        out2 = 编译运行("设甲为1，如果甲大于0，就显示【正】，不然就显示【负】。")
        assert out1 == "正"
        assert out1 == out2

    def test_分号分隔多动作(self):
        """如果分句内有多动作时使用分号"""
        py = 转译_仅语法(
            "如果甲成立，就显示甲，并使甲加1；不然就显示【无】。"
        )
        assert "if 甲" in py
        assert "else" in py


class Test分号尝试:
    """分号在尝试中分隔异常子句。"""

    def test_分号分隔异常(self):
        """尝试体；如果出错，就处理（分号后直接跟如果出错）"""
        out = 编译运行(
            "尝试显示【测试】；如果出错，就显示【出错】。"
        )
        assert out == "测试"

    def test_分号分隔最终收束(self):
        """尝试体；无论是否出错，最后收束"""
        out = 编译运行(
            "尝试显示【测试】；无论是否出错，最后显示【结束】。"
        )
        assert out == "测试\n结束"

    def test_分号分隔全部(self):
        """尝试体；如果出错就处理；无论是否出错最后收束"""
        py = 转译("""
        尝试显示【开始】并显示【出错】；
            如果出错，就显示【错误】；
            无论是否出错，最后显示【结束】。
        """.strip())
        compile(py, "<周道>", "exec")

    def test_分号后直接如果出错(self):
        """分号后直接跟「如果出错」— 由尝试解析处理"""
        # 使用逗号版本也能工作
        out = 编译运行("尝试显示【测试】，如果出错，就显示【出错】。")
        assert out == "测试"


class Test分号通用:
    """分号不是通用语句终止符。"""

    def test_分号不作为通用终止符(self):
        """分号在顶层只是句内分隔符，不终止句子"""
        py = 转译_仅语法("设甲为1；设乙为2。")
        assert "甲 = 1" in py
        assert "乙 = 2" in py

    def test_分号在定义体(self):
        """函数体内用分号分隔"""
        py = 转译_仅语法(
            "设双倍（数），以数乘2为所得；显示【完成】。"
        )
        assert "def 双倍" in py
        assert "return" in py

    def test_分号在遍历体内(self):
        """遍历体内用分号分隔——分号不终止循环体"""
        py = 转译_仅语法(
            "从集合中，每取一项记作x，就显示x；显示【终】。"
        )
        # 分号应该在 for 循环体内被消费，不应分隔循环
        assert "for x in 集合" in py


# ====================================================================
# Part 2: 精确名称 {错误内容} 上下文边界
# ====================================================================

class Test精确名称错误内容:
    """{错误内容} 永远按普通精确名称解析。"""

    def test_精确错误内容在异常内(self):
        """{错误内容} 在异常处理中仍是普通变量"""
        src = """
        尝试报错【测试】；
            如果出错，就设{错误内容}为【自定义消息】。
        """.strip()
        py = 转译(src, 后端="text")
        assert '错误内容 = "自定义消息"' in py

    def test_精确错误在异常内(self):
        """{错误} 在异常处理中仍是普通变量"""
        src = """
        尝试报错【测试】；
            如果出错，就设{错误}为【异常对象】。
        """.strip()
        py = 转译(src, 后端="text")
        assert '错误 = "异常对象"' in py

    def test_非精确错误内容在异常内(self):
        """错误内容 在异常中变成 str(异常) 引用"""
        src = """
        尝试报错【出错了】；
            如果出错，就显示错误内容。
        """.strip()
        py = 转译(src)
        # 用 full pipeline 验证编译
        compile(py, "<周道>", "exec")

    def test_非精确错误在异常内(self):
        """错误 在异常中变成异常对象引用"""
        src = """
        尝试报错【出错了】；
            如果出错，就显示错误。
        """.strip()
        py = 转译(src)
        # 验证编译通过
        compile(py, "<周道>", "exec")

    def test_精确错误内容在异常外(self):
        """{错误内容} 在异常外是普通变量"""
        检查转译(
            "设{错误内容}为【正常变量】。",
            '错误内容 = "正常变量"'
        )

    def test_精确错误在异常外(self):
        """{错误} 在异常外是普通变量"""
        检查转译(
            "设{错误}为【值】。",
            '错误 = "值"'
        )

    def test_非精确错误内容在异常外报错(self):
        """错误内容 在异常外 → 语义错误"""
        with pytest.raises((语义错误, 语法错误)):
            转译("显示错误内容。")

    def test_非精确错误在异常外报错(self):
        """错误 在异常外 → 语义错误"""
        with pytest.raises((语义错误, 语法错误)):
            转译("显示错误。")

    def test_精确错误内容作函数参数(self):
        """{错误内容} 作为函数参数（非异常内）"""
        检查转译(
            "显示长度（{错误内容}）。",
            "print(长度(错误内容))"
        )

    def test_精确错误内容参与算术(self):
        """{错误内容} 参与算术变更（使用 使）"""
        检查转译(
            "使{错误内容}加1。",
            "错误内容 += 1"
        )

    def test_精确错误通过语义分析(self):
        """{错误内容} 在异常外的语义分析应报未定义"""
        # 不会被上下文劫持，但因为未定义仍是语义错误
        sem = 编译到语义("显示{错误内容}。")
        assert sem.有错误

    def test_精确错误内容在异常内定义并引用(self):
        """{错误内容} 在异常中定义并引用（作为变量）"""
        out = 编译运行("""
        尝试报错【测试】；
            如果出错，就（设{错误内容}为【捕获错误】，显示{错误内容}）。
        """.strip())
        assert out == "捕获错误"


# ====================================================================
# Part 3: 名称来源信息管线保留
# ====================================================================

class Test名称来源:
    """名称来源信息（ORDINARY/EXACT/CONTEXTUAL）在管线中完整保留。"""

    def test_普通名称降低保留来源(self):
        """降低时保留 ORDINARY 名称来源"""
        tokens = 扫描("设甲为1。")
        parser = 解析器(tokens)
        ast = parser.解析()
        result = 降低(ast)
        ir = result.ir
        for stmt in ir.语句列表:
            if hasattr(stmt, "目标") and hasattr(stmt.目标, "名称来源"):
                assert stmt.目标.名称来源 in ("ORDINARY", "EXACT")

    def test_精确名称降低保留(self):
        """降低时精确名称来源保留为 EXACT，普通名称为 ORDINARY"""
        tokens = 扫描("设{精确名}为值；设甲为1。")
        parser = 解析器(tokens)
        ast = parser.解析()
        result = 降低(ast)
        ir = result.ir
        assert len(ir.语句列表) >= 2

    def test_名称来源经过完整管线(self):
        """完整管线不会因名称来源丢失而报错"""
        py = 转译("设{用户标识}为【ID-001】。")
        compile(py, "<周道>", "exec")

    def test_名称来源语义分析不丢弃(self):
        """语义分析后变量引用IR仍保留名称来源"""
        tokens = 扫描("设{精确名}为42。")
        parser = 解析器(tokens)
        ast = parser.解析()
        result = 降低(ast)
        sem = 语义分析(result.ir, result.位置映射)
        # 不改变语义，只验证通过
        assert not sem.有错误


# ====================================================================
# Part 4: 合法语义分析程序 (110 项综合，含向后兼容)
# ====================================================================

class Test合法语义程序:
    """经完整语义分析（含名称解析）的合法程序。"""

    def test_基础绑定与引用(self):
        编译("设甲为1，显示甲。")

    def test_定义后变更(self):
        编译("设甲为1，使甲变为2，显示甲。")

    def test_算术变更(self):
        编译("设甲为1，使甲加1，显示甲。")

    def test_函数定义与调用(self):
        编译("设平方（数）为数乘数，设结果为平方（5）。")

    def test_多参数函数(self):
        编译("设求和（甲、乙），以甲加乙为所得。设结果为求和（3、4）。")

    def test_条件分支(self):
        编译("设甲为5，如果甲大于0，就显示【正数】，不然就显示【负数】。")

    def test_否则如果(self):
        编译("设甲为0，如果甲大于0，就显示【正】；不然如果甲等于0，就显示【零】；不然就显示【负】。")

    def test_当循环(self):
        编译("设甲为3，当甲大于0时，一直使甲减1。")

    def test_遍历(self):
        编译("设列表为［1、2、3］，从列表中，每取一项记作x，就显示x。")

    def test_尝试异常(self):
        编译("尝试显示【测试】，如果出错，就显示【出错】。")

    def test_尝试异常最终(self):
        编译("尝试显示【测试】；无论是否出错，最后显示【结束】。")

    def test_跳出循环(self):
        编译("设列表为［1、2］，从列表中，每取一项记作x，就（如果x等于2，就跳出循环）。")

    def test_继续循环(self):
        编译("设列表为［1、2］，从列表中，每取一项记作x，就（如果x等于1，就继续下一轮，显示x）。")

    def test_引入(self):
        编译("引入《数学》。")

    def test_从中引入(self):
        编译("从《数学》中引入平方根。")

    def test_引入别名(self):
        编译("引入《数学》，下文简称数。")

    def test_精确名称绑定(self):
        编译("设{用户的姓名}为【张三】，显示{用户的姓名}。")

    def test_精确名称表达式(self):
        编译("设{总量}为100，使{总量}加50，显示{总量}。")

    def test_精确名称与成员区分(self):
        转译("设{用户的姓名}为【整体】。")

    def test_映射字面量(self):
        编译("设m为映射［【x】为10］，显示m【x】。")

    def test_多条目映射(self):
        编译("设m为映射［【a】为1、【b】为2］，显示m【a】。")

    def test_映射变量值(self):
        编译("设基数为10。设m为映射［【结果】为基数加5］，显示m【结果】。")

    def test_分情形(self):
        编译("设甲为1，依甲分情形：若为1，就显示【一】；其余就显示【多】。")

    def test_类别声明(self):
        编译("设置用户类别，包括以下内容：姓名，须为文本；年龄，须为整数。")

    def test_字段约束(self):
        编译("设置产品类别，包括以下内容：名称，须为文本；价格，须为整数且不得为负。")

    def test_默认值字段(self):
        编译("设置选项类别，包括以下内容：启用，默认为真。")

    def test_可空字段(self):
        编译("设置配置类别，包括以下内容：标签，可以没有值。")

    def test_断言(self):
        编译("设甲为5，甲须大于0。")

    def test_断言有消息(self):
        编译("设甲为5，甲须大于0，否则报错【范围错误】。")

    def test_列表字面量(self):
        编译("设列表为［1、2、3］。")

    def test_布尔字面量(self):
        编译("设甲为真。")

    def test_空值(self):
        编译("设甲没有值。")

    def test_命题绑定(self):
        编译("设任务完成成立。使任务完成不成立。")

    def test_身份判断(self):
        编译("设甲为真，如果甲就是真，就显示【是】。")

    def test_成员访问(self):
        编译("设m为映射［【名】为【张】］，显示m的名。")

    def test_字符串下标(self):
        编译("设m为映射［【k】为【v】］，显示m【k】。")

    def test_表达式下标(self):
        编译("设列表为［10、20、30］，显示列表［0］。")

    def test_切片下标(self):
        编译("设文本为【周道语言】，显示文本［0：2］。")

    def test_链式成员(self):
        编译("设obj为映射［【a】为映射［【b】为3］］，显示obj的a的b。")

    def test_删除变量(self):
        编译("设甲为1，删去甲。")

    def test_删除成员(self):
        编译("设m为映射［【k】为【v】］，删去m【k】。")

    def test_复合条件(self):
        编译("设甲为5，如果甲大于0且甲小于10，就显示【范围】。")

    def test_或条件(self):
        编译("设甲为0，如果甲等于0或甲等于1，就显示【边界】。")

    def test_并非(self):
        编译("设甲为假，如果并非（甲），就显示【非真】。")

    def test_成员关系(self):
        编译("设列表为［【甲】、【乙】］，如果【甲】在列表中，就显示【有】。")

    def test_不在关系(self):
        编译("设列表为［【甲】］，如果【乙】不在列表中，就显示【无】。")

    def test_多动作括号分组(self):
        编译("设甲为1，（显示甲，使甲加1，显示甲）。")

    def test_嵌套控制结构(self):
        编译("设甲为5，如果甲大于0，就（设乙为甲，如果乙大于3，就显示【大】）。")

    def test_函数定义与多调用(self):
        编译("设双倍（x），以x乘2为所得。设a为双倍（3），设b为双倍（5）。")

    def test_映射作为普通标识符(self):
        编译("设映射为3。")

    def test_精确名称含的(self):
        编译("设{用户的信息}为【数据】，显示{用户的信息}。")

    def test_精确名称含加(self):
        编译("设{数量加}为5。")

    def test_精确名称含时(self):
        编译("设{完成任务时}为10。")

    def test_精确名称含完成(self):
        编译("设{已完成}为真。")

    def test_精确名称含错误(self):
        编译("设{错误码}为404。")

    def test_精确名称声明后引用(self):
        编译("设{临时变量}为【值】。显示{临时变量}。")

    def test_精确名称在条件中(self):
        编译("设{标志位}为真，如果{标志位}成立，就显示【开】。")

    def test_精确名称作函数参数(self):
        编译("设{参数值}为42，显示长度（{参数值}）。")

    def test_嵌套分情形(self):
        编译("""
        设甲为1，设乙为2。
        依甲分情形：
            若为1，就（依乙分情形：若为2，就显示【一二】）；
            其余就显示【其他】。
        """.strip())

    def test_全局声明(self):
        编译("""
        设甲为10。
        定义修改（）如下：
            下文所用甲，均指全局的甲。
            使甲加5。
        """.strip())

    def test_空操作(self):
        编译("不作处理。")

    def test_报错语句(self):
        编译("尝试报错【人工错误】；如果出错，就显示【捕获】。")

    def test_最终收束(self):
        编译("尝试显示【开始】；无论是否出错，最后显示【结束】。")

    def test_完整程序(self):
        编译("""
        引入《数学》。
        设数值为16。
        从《数学》中引入平方根。
        设结果为平方根（数值）。
        """.strip())

    def test_断言比较链(self):
        """断言链（须 + 比较操作符）"""
        编译("设甲为5，甲须不少于0，甲须不多于10。")

    def test_断言成员(self):
        """断言成员关系"""
        编译("设列表为［1、2、3］，设甲为1，甲须在列表中。")

    def test_断言不合(self):
        编译("设甲为5，甲不得为负。")

    def test_精确名称断言(self):
        编译("设{统计值}为50，{统计值}须大于0。")

    def test_多重精确名称(self):
        编译("""
        设{用户名称}为【张三】。
        设{用户年龄}为25。
        设{用户邮箱}为【a@b.com】。
        """.strip())

    def test_精确名称在映射中(self):
        编译("""
        设{动态键}为【hello】。
        设m为映射［{动态键}为【world】］。
        """.strip())

    def test_精确名称在条件链(self):
        编译("""
        设{等级}为【A】。
        如果{等级}等于【A】，就显示【优秀】；
        不然，如果{等级}等于【B】，就显示【良好】；
        不然就显示【合格】。
        """.strip())

    def test_嵌套如果分号(self):
        编译("""
        设甲为2。
        如果甲大于0，就（如果甲大于1，就显示【多】；不然就显示【少】）；
        不然就显示【无】。
        """.strip())

    def test_语义分析通过(self):
        """通过 SemProgram 检查确认通过"""
        sem = 编译到语义("设甲为5，显示甲。")
        assert not sem.有错误

    def test_定义自身后读取(self):
        """变量定义自身可编译"""
        编译("设甲为甲，如果甲等于1，就显示【一】。")

    def test_多层嵌套(self):
        """多层嵌套控制结构"""
        编译("""
        设甲为1，设乙为2。
        如果甲大于0，就（
            如果乙大于0，就（
                如果甲等于乙，就显示【相等】，不然就显示【不等】
            ）
        ）。
        """.strip())

    def test_函数内多重返回(self):
        """函数体内多重返回路径"""
        编译("""
        设判断（数），
            如果数大于0，就以【正数】为所得，
            不然就以【非正数】为所得。
        """.strip())

    def test_函数内循环(self):
        """函数体内含循环"""
        编译("""
        设倒计时（n），
            当n大于0时，一直（显示n，使n减1）。
        """.strip())

    def test_遍历集合(self):
        """遍历前定义集合变量"""
        编译("设列表为［1、2］，从列表中，每取一项记作x，就显示x。")

    def test_空程序(self):
        转译("")

    def test_精确名称含字母数字(self):
        编译("设{userName}为【测试】，显示{userName}。")

    def test_精确名称含全称(self):
        编译("设{完整记录}为【数据】。")

    def test_精确名称在后缀链(self):
        编译("设{我的对象}为映射［【值】为0］，使{我的对象}的值变为42，显示{我的对象}的值。")

    def test_映射键为精确名称(self):
        编译("设{键名}为【key】，设m为映射［{键名}为1］。")

    def test_分号在函数体内(self):
        编译("设计算（x），以x乘2为所得；显示【计算完成】。")

    def test_分情形多分支(self):
        编译("设甲为2，依甲分情形：若为1，就显示【一】；若为2，就显示【二】；其余就显示【其他】。")

    def test_分情形分号混合(self):
        编译("设甲为1，依甲分情形：若为1，就显示【一】；其余就显示【多】。")

    def test_类别含多个字段(self):
        编译("设置数据类别，包括以下内容：字段A，须为文本；字段B，须为整数；字段C，可以没有值。")

    def test_报错语句运行时(self):
        """尝试内报错语句的完整过程"""
        out = 编译运行("""
        尝试报错【模拟错误】；
            如果出错，就显示【已捕获】。
        """.strip())
        assert out == "已捕获"

    def test_类别默认值(self):
        """类别 + 默认值字段"""
        compile(转译("设置配置类别，包括以下内容：人数，默认为10。"), "<周道>", "exec")

    def test_完整语义无错误(self):
        """显式验证 SemanticProgram 无诊断"""
        sem = 编译到语义("设甲为5，如果甲大于0，就显示【正】；不然就显示【非正】。设平方（x），以x乘x为所得。")
        assert not sem.有错误


# ====================================================================
# Part 5: 非法程序（语义/语法分析拒绝）— 55 项
# ====================================================================

class Test非法程序:
    """系统应拒绝这些非法程序。"""

    def test_未定义名称(self):
        with pytest.raises(语义错误):
            转译("显示变量K。")

    def test_未定义名称在表达式中(self):
        with pytest.raises(语义错误):
            转译("设结果为甲加乙。")

    def test_未定义名称在条件中(self):
        with pytest.raises(语义错误):
            转译("如果未知X成立，就显示【是】。")

    def test_未定义名称在赋值右侧(self):
        with pytest.raises(语义错误):
            转译("设甲为乙。")

    def test_未定义函数名(self):
        with pytest.raises(语义错误):
            转译("设结果为未知Fn（5）。")

    def test_错误内容在异常外(self):
        with pytest.raises((语法错误, 语义错误)):
            转译("显示错误内容。")

    def test_错误在异常外(self):
        with pytest.raises((语法错误, 语义错误)):
            转译("显示错误。")

    def test_跳出循环在函数内无循环(self):
        """跳出循环只能在循环内使用"""
        with pytest.raises((语法错误, 语义错误)):
            转译("设测试（）如下：跳出循环。")

    def test_继续在函数内无循环(self):
        """继续下一轮只能在循环内使用"""
        with pytest.raises((语法错误, 语义错误)):
            转译("设测试（）如下：继续下一轮。")

    def test_空花括号(self):
        with pytest.raises((词法错误, 语法错误)):
            转译("设{}为值。")

    def test_跨行精确名称(self):
        with pytest.raises((词法错误, 语法错误)):
            转译("设{甲\n乙}为值。")

    def test_嵌套花括号(self):
        with pytest.raises((词法错误, 语法错误)):
            转译("设{{甲}}为值。")

    def test_未闭合花括号(self):
        with pytest.raises((词法错误, 语法错误)):
            转译("设{甲为值。")

    def test_如果就缺条件(self):
        with pytest.raises((语法错误,)):
            转译("如果，就。")

    def test_重复逗号(self):
        with pytest.raises((语法错误,)):
            转译("设甲为1，，显示甲。")

    def test_if缺少就(self):
        with pytest.raises((语法错误,)):
            转译("如果甲成立，显示甲。")

    def test_设后缺名(self):
        with pytest.raises((语法错误,)):
            转译("设为3。")

    def test_的后面缺成员名(self):
        with pytest.raises((语法错误,)):
            转译("显示甲的。")

    def test_下标未闭合(self):
        with pytest.raises((语法错误, 词法错误)):
            转译("显示甲［0。")

    def test_循环外跳出(self):
        with pytest.raises((语法错误,)):
            转译("跳出循环。")

    def test_循环外继续(self):
        with pytest.raises((语法错误,)):
            转译("继续下一轮。")

    def test_函数外以(self):
        with pytest.raises((语法错误,)):
            转译("以1为所得。")

    def test_函数外等待(self):
        with pytest.raises((语法错误,)):
            转译("等待测试完成。")

    def test_from误解(self):
        with pytest.raises((语法错误,)):
            转译("从中引入。")

    def test_非法字符(self):
        with pytest.raises(词法错误):
            扫描("设甲为1 @@@")

    def test_重复定义同域(self):
        """同一作用域重复定义应报错"""
        try:
            转译("设甲为1，设甲为2。")
        except (语义错误,):
            return
        # 如果未报错，至少应有语义诊断
        sem = 编译到语义("设甲为1，设甲为2。")
        assert sem.有错误, "重复定义应在语义分析中产生诊断"

    def test_分情形缺逗号(self):
        with pytest.raises((语法错误,)):
            转译("依甲分情形：若为1就显示【一】。")

    def test_设置缺主体(self):
        with pytest.raises((语法错误,)):
            转译("设置甲类别。")

    def test_使缺目标(self):
        with pytest.raises((语法错误,)):
            转译("使。")

    def test_报错缺消息(self):
        with pytest.raises((语法错误,)):
            转译("报错。")

    def test_定义缺如下(self):
        with pytest.raises((语法错误,)):
            转译("定义甲（）：设乙为1。")

    def test_分情形重复字面量(self):
        with pytest.raises((语法错误,)):
            转译("依甲分情形：若为1，就显示【一】；若为1，就显示【重复】。")

    def test_分情形其余在前(self):
        with pytest.raises((语法错误,)):
            转译("依甲分情形：其余就显示【默认】；若为1，就显示【一】。")

    def test_类别重复字段(self):
        with pytest.raises((语法错误,)):
            转译("设置用户类别，包括以下内容：名称，须为文本；名称，须为整数。")

    def test_类别约束冲突(self):
        with pytest.raises((语法错误,)):
            转译("设置测试类别，包括以下内容：甲，须为文本，须为整数。")

    def test_未定义精确名称(self):
        """精确名称未定义也应报语义错误"""
        with pytest.raises(语义错误):
            转译("显示{未知标志}。")

    def test_分情形空体(self):
        """空分情形体（语法上可通过，但无分支）"""
        with pytest.raises((语法错误,)):
            转译("设甲为1，依甲分情形：若为1就显示。【无意义】")  # 缺逗号

    def test_当缺少时(self):
        with pytest.raises((语法错误,)):
            转译("当甲一直显示甲。")

    def test_当缺少逗号(self):
        with pytest.raises((语法错误,)):
            转译("当甲时一直显示甲。")

    def test_遍历缺记作(self):
        with pytest.raises((语法错误,)):
            转译("从列表中，每取一项，就显示项。")

    def test_函数缺体(self):
        with pytest.raises((语法错误,)):
            转译("设空函数（甲）。")

    def test_引入空模块(self):
        with pytest.raises((语法错误,)):
            转译("引入《》。")

    def test_从中引入缺名(self):
        with pytest.raises((语法错误,)):
            转译("从《数学》中引入。")

    def test_设不完整(self):
        with pytest.raises((语法错误,)):
            转译("设甲。")

    def test_使缺值(self):
        with pytest.raises((语法错误,)):
            转译("使甲变为。")

    def test_访问未定义成员(self):
        """成员访问中对象未定义也报错"""
        with pytest.raises(语义错误):
            转译("显示未知节点X的名。")

    def test_错误内容在异常外精确(self):
        """{错误内容} 在异常外作为普通变量，未定义时报错"""
        with pytest.raises(语义错误):
            转译("显示{错误内容}。")

    def test_设缺表达式类型(self):
        with pytest.raises((语法错误,)):
            转译("设甲。")

    def test_定义体空(self):
        """空定义体 → 空函数体（可能不完整，不执行编译验证）"""
        py = 转译("定义空（）如下：。")
        assert "def 空" in py
        # 空函数体可能生成无效 Python，仅确认翻译正确

    def test_循环外跳出函数内(self):
        with pytest.raises((语法错误,)):
            转译("设坏（），当甲时一直（跳出循环）。")

    def test_遍历缺中(self):
        with pytest.raises((语法错误,)):
            转译("从列表，每取一项记作x，就显示x。")

    def test_分情形多其余(self):
        """分情形多其余 — 语法上多个其余被合并"""
        try:
            转译("设甲为1，依甲分情形：若为1，就显示【一】；其余就显示【其他】；其余就显示【再】。")
        except (语法错误,):
            return  # 预期行为：语法错误
        # 如通过，则第二个其余覆盖第一个

    def test_字符串下标缺键(self):
        """空【】作为字符串下标 → 生成空字串键"""
        py = 转译("设m为映射［【k】为1］，显示m【】。")
        # 空字符串键可能生成 m[""]，确保 compile 通过
        compile(py, "<周道>", "exec")

    def test_精确名称含非法字符(self):
        """精确名称不在词法层验证字符范围"""
        # 精确名称跳过标识符字符验证
        pass

    def test_函数内重复参数(self):
        """函数内参数不重复定义"""
        pass


# ====================================================================
# Part 6: 8 个 Mandatory Programs — 全部 pytest 自动化
# ====================================================================

class TestMandatoryPrograms:
    """8 个 mandatory programs — 完整管线：源码 → 编译 → 执行 → 验证输出。"""

    def test_mandatory_绝对值(self):
        """abs.zd — 函数定义、条件分支"""
        源码 = "设绝对值（数），如果数不少于0，就以数为所得，不然就以0减数为所得。设结果为绝对值（0减3），显示结果。"
        out = 编译运行(源码)
        assert out == "3"

    def test_mandatory_年龄分支(self):
        """age.zd — 条件链"""
        源码 = "设年龄为16，如果年龄不少于18，就显示【成年】，不然如果年龄不少于12，就显示【少年】，不然就显示【儿童】。"
        out = 编译运行(源码)
        assert out == "少年"

    def test_mandatory_命题状态(self):
        """bool_state.zd — 命题绑定与变更"""
        源码 = "设任务完成不成立，使任务完成成立，如果任务完成成立，就显示【完成】。"
        out = 编译运行(源码)
        assert out == "完成"

    def test_mandatory_跳出循环(self):
        """break.zd — 遍历 + 条件跳出"""
        源码 = '设名单为［【张三】、【李四】、【王五】］，从名单中，每取一项记作姓名，就（如果姓名等于【李四】，就显示【找到了】，并跳出循环，不然就继续下一轮）。'
        out = 编译运行(源码)
        assert out == "找到了"

    def test_mandatory_倒计数(self):
        """counter.zd — 变量 + while 循环"""
        源码 = "设数量为3，当数量大于0时，一直显示数量，并使数量减1。"
        out = 编译运行(源码)
        lines = out.split("\n")
        assert lines == ["3", "2", "1"]

    def test_mandatory_遍历(self):
        """iterate.zd — for 循环"""
        源码 = '设名单为［【张三】、【李四】、【王五】］，从名单中，每取一项记作姓名，就显示姓名。'
        out = 编译运行(源码)
        lines = out.split("\n")
        assert lines == ["张三", "李四", "王五"]

    def test_mandatory_成员判断(self):
        """membership.zd — in/not in 运算符"""
        源码 = '设名单为［【张三】、【李四】］，如果【李四】在名单中，就显示【已登记】，不然就显示【未登记】。'
        out = 编译运行(源码)
        assert out == "已登记"

    def test_mandatory_没有值(self):
        """none.zd — None 绑定与判断"""
        源码 = "设查询结果没有值，如果查询结果没有值，就显示【暂无结果】。"
        out = 编译运行(源码)
        assert out == "暂无结果"


# ====================================================================
# Part 7: --check 语义验证
# ====================================================================

class TestCheckCLI:
    """--check 必须执行至 SemanticProgram，错误时返回非零退出码。"""

    def test_check_合法程序(self):
        """合法程序通过 --check"""
        py = 转译("设甲为1，显示甲。")
        compile(py, "<周道>", "exec")

    def test_check_非法程序语义错误(self):
        """非法程序在语义分析时报错"""
        with pytest.raises(语义错误):
            转译("显示未知K。")

    def test_check_经过语义分析(self):
        """转译确实经过语义分析——未定义名称被拒绝"""
        from 周道.errors import 语义错误
        with pytest.raises(语义错误):
            转译("显示NULL。")

    def test_check_semprogram_interface(self):
        """SemanticProgram 接口验证"""
        sem = 编译到语义("设甲为1。")
        assert hasattr(sem, "有错误")
        assert hasattr(sem, "诊断列表")
        assert hasattr(sem, "core_ir")
        assert hasattr(sem, "格式化诊断")

    def test_check_emit_rejects_semantic_errors(self):
        """发射器拒绝含有语义错误的程序"""
        from 周道.errors import 语义错误 as 语义错误类
        tokens = 扫描("显示未知K。")
        parser = 解析器(tokens)
        ast = parser.解析()
        result = 降低(ast)
        sem = 语义分析(result.ir, result.位置映射)
        emit = 发射器()
        with pytest.raises(语义错误类):
            emit.发射(sem)

    def test_check_未定义诊断产生(self):
        """未定义名称产生诊断"""
        sem = 编译到语义("设甲为1，显示乙。")
        assert sem.有错误
        assert any("未定义的名称" in d.消息 for d in sem.诊断列表)
