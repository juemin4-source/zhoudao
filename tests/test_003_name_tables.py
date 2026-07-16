"""周道 v0.0.3：NameTable / NameLattice 单元测试。

覆盖：
- NameTable 绑定和查找
- 同域重名拒绝
- 解除绑定
- NameLattice 进入/离开作用域
- 名称从当前→父→全局查找
- global/nonlocal 跨越查找
- 查找失败错误
"""

import pytest
from 周道.nametable import NameTable, 绑定信息
from 周道.name_lattice import NameLattice
from 周道.errors import 语义错误
from 周道.errors import 源码位置

P = 源码位置(行=1, 列=1, 索引=0)


class TestNameTable:
    def test_绑定和查找(self):
        tbl = NameTable(作用域类型="global")
        tbl.绑定("甲", 绑定信息("甲", "变量", P))
        assert tbl.查找("甲") is not None
        assert tbl.查找("甲").名称 == "甲"

    def test_查找不存在(self):
        tbl = NameTable(作用域类型="global")
        assert tbl.查找("不存在") is None

    def test_同域重名拒绝(self):
        tbl = NameTable(作用域类型="global")
        tbl.绑定("甲", 绑定信息("甲", "变量", P))
        with pytest.raises(语义错误, match="重复定义"):
            tbl.绑定("甲", 绑定信息("甲", "变量", P))

    def test_解除绑定(self):
        tbl = NameTable(作用域类型="global")
        tbl.绑定("甲", 绑定信息("甲", "变量", P))
        assert tbl.已绑定("甲")
        tbl.解除绑定("甲")
        assert not tbl.已绑定("甲")

    def test_解除不存在的绑定(self):
        tbl = NameTable(作用域类型="global")
        assert not tbl.解除绑定("不存在")

    def test_已绑定(self):
        tbl = NameTable(作用域类型="global")
        tbl.绑定("甲", 绑定信息("甲", "变量", P))
        assert tbl.已绑定("甲")
        assert not tbl.已绑定("乙")

    def test_所有名称(self):
        tbl = NameTable(作用域类型="global")
        tbl.绑定("甲", 绑定信息("甲", "变量", P))
        tbl.绑定("乙", 绑定信息("乙", "函数", P))
        assert tbl.所有名称 == frozenset({"甲", "乙"})

    def test_数量(self):
        tbl = NameTable(作用域类型="global")
        assert tbl.数量 == 0
        tbl.绑定("甲", 绑定信息("甲", "变量", P))
        assert tbl.数量 == 1

    def test_函数作用域(self):
        tbl = NameTable(作用域类型="function")
        tbl.绑定("x", 绑定信息("x", "参数", P))
        assert tbl.查找("x") is not None
        assert tbl.作用域类型 == "function"


class TestNameLattice:
    def test_初始状态(self):
        nl = NameLattice()
        assert nl.根表.作用域类型 == "global"
        assert nl.当前表.作用域类型 == "global"

    def test_进入和离开作用域(self):
        nl = NameLattice()
        nl.进入作用域("function")
        assert nl.当前表.作用域类型 == "function"
        nl.进入作用域("control")
        assert nl.当前表.作用域类型 == "control"
        nl.离开作用域()
        assert nl.当前表.作用域类型 == "function"
        nl.离开作用域()
        assert nl.当前表.作用域类型 == "global"

    def test_在当前域注册(self):
        nl = NameLattice()
        nl.在当前域注册("甲", 绑定信息("甲", "变量", P))
        assert nl.当前表.查找("甲") is not None

    def test_在当前域解析(self):
        nl = NameLattice()
        nl.在当前域注册("甲", 绑定信息("甲", "变量", P))
        assert nl.在当前域解析("甲") is not None
        assert nl.在当前域解析("乙") is None

    def test_检查重复_无重复(self):
        nl = NameLattice()
        assert not nl.检查重复("甲")
        nl.在当前域注册("甲", 绑定信息("甲", "变量", P))
        assert nl.检查重复("甲")

    def test_解析_当前域(self):
        nl = NameLattice()
        nl.在当前域注册("甲", 绑定信息("甲", "变量", P))
        result = nl.解析("甲")
        assert result is not None
        assert result.名称 == "甲"

    def test_解析_父作用域(self):
        nl = NameLattice()
        nl.在当前域注册("全局", 绑定信息("全局", "变量", P))
        nl.进入作用域("function")
        nl.在当前域注册("局部", 绑定信息("局部", "变量", P))
        # 从当前域可以解析到父域的"全局"
        result = nl.解析("全局")
        assert result is not None
        assert result.名称 == "全局"

    def test_解析_遮蔽(self):
        nl = NameLattice()
        nl.在当前域注册("甲", 绑定信息("甲", "变量", P))
        nl.进入作用域("function")
        nl.在当前域注册("甲", 绑定信息("甲", "变量", P))
        # 内层覆盖外层
        result = nl.解析("甲")
        assert result is not None

    def test_解析_未定义(self):
        nl = NameLattice()
        with pytest.raises(语义错误, match="未定义"):
            nl.解析("不存在")

    def test_全局跨越解析(self):
        nl = NameLattice()
        nl.在当前域注册("全局变量", 绑定信息("全局变量", "变量", P))
        nl.进入作用域("function")
        nl.注册跨越声明("全局变量", "global")
        result = nl.解析("全局变量")
        assert result is not None
        assert result.名称 == "全局变量"

    def test_跨越冲突(self):
        nl = NameLattice()
        nl.注册跨越声明("甲", "global")
        with pytest.raises(语义错误, match="跨越"):
            nl.注册跨越声明("甲", "nonlocal")

    def test_离开根作用域失败(self):
        nl = NameLattice()
        with pytest.raises(语义错误, match="根作用域"):
            nl.离开作用域()

    def test_解析_多层嵌套(self):
        nl = NameLattice()
        nl.在当前域注册("root", 绑定信息("root", "变量", P))
        nl.进入作用域("function")
        nl.进入作用域("control")
        nl.进入作用域("control")
        assert nl.解析("root") is not None
        assert nl.解析("root").名称 == "root"


if __name__ == "__main__":
    pytest.main([__file__])
