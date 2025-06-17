from __future__ import annotations


class ASTNode:
    line: int = 0
    column: int = 0


class ProgramNode(ASTNode):
    def __init__(self, statements: list[ASTNode]) -> None:
        self.statements = statements

    def __repr__(self) -> str:
        return f'<ProgramNode statements={self.statements}>'


class BlockNode(ASTNode):
    def __init__(self, statements: list[ASTNode]) -> None:
        self.statements = statements

    def __repr__(self) -> str:
        return f'<BlockNode statements={self.statements}>'


class VarDeclarationNode(ASTNode):
    def __init__(self, var_name: str, data_type: str, value_expr: ASTNode | None = None) -> None:
        self.var_name = var_name
        self.data_type = data_type
        self.value_expr = value_expr

    def __repr__(self) -> str:
        return f'<VarDeclarationNode name={self.var_name}, type={self.data_type}, value={self.value_expr}>'


class VarAssignNode(ASTNode):
    def __init__(self, var_name: str, value_expr: ASTNode) -> None:
        self.var_name = var_name
        self.value_expr = value_expr

    def __repr__(self) -> str:
        return f'<VarAssignNode name={self.var_name}, value={self.value_expr}>'


class IdentifierNode(ASTNode):
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f'<IdentifierNode name={self.name}>'


class IntLiteralNode(ASTNode):
    def __init__(self, value: str | int) -> None:
        self.value = int(value)

    def __repr__(self) -> str:
        return f'<IntLiteralNode value={self.value}>'


class FloatLiteralNode(ASTNode):
    def __init__(self, value: str | float) -> None:
        self.value = float(value)

    def __repr__(self) -> str:
        return f'<FloatLiteralNode value={self.value}>'


class CharLiteralNode(ASTNode):
    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f'<CharLiteralNode value={self.value}>'


class StringLiteralNode(ASTNode):
    def __init__(self, value: str) -> None:
        self.value = str(value)

    def __repr__(self) -> str:
        return f"<StringLiteralNode value={self.value}>"


class ArrayLiteralNode(ASTNode):
    def __init__(self, elements: list[ASTNode]) -> None:
        self.elements = elements

    def __repr__(self) -> str:
        return f"<ArrayLiteralNode elements={self.elements}>"


class ArrayIndexNode(ASTNode):
    def __init__(self, array_name: str | ASTNode, index_expr: ASTNode) -> None:
        self.array_name = array_name
        self.index_expr = index_expr

    def __repr__(self) -> str:
        return f"<ArrayIndexNode array={self.array_name}, index={self.index_expr}>"


class NullLiteralNode(ASTNode):
    def __init__(self) -> None:
        pass
    
    def __repr__(self) -> str:
        return "<NullLiteralNode>"


class BinaryOpNode(ASTNode):
    def __init__(self, op: str, left_expr: ASTNode, right_expr: ASTNode) -> None:
        self.op = op
        self.left_expr = left_expr
        self.right_expr = right_expr

    def __repr__(self) -> str:
        return f'<BinaryOpNode op={self.op}, left={self.left_expr}, right={self.right_expr}>'


class UnaryOpNode(ASTNode):  # For bitwise NOT, pointer dereference etc.
    def __init__(self, op: str, expr: ASTNode) -> None:
        self.op = op
        self.expr = expr

    def __repr__(self) -> str:
        return f'<UnaryOpNode op={self.op}, expr={self.expr}>'


class FunctionDefNode(ASTNode):
    def __init__(self, func_name: IdentifierNode, params: list[tuple[str, str]], return_type: str, body: BlockNode) -> None:
        self.func_name = func_name
        self.params = params  # list of (param_name, param_type) tuples
        self.return_type = return_type
        self.body = body

    def __repr__(self) -> str:
        return f'<FunctionDefNode name={self.func_name}, params={self.params}, return_type={self.return_type}, body={self.body}>'


class FunctionCallNode(ASTNode):
    def __init__(self, func_name: IdentifierNode, args: list[ASTNode]) -> None:
        self.func_name = func_name
        self.args = args

    def __repr__(self) -> str:
        return f'<FunctionCallNode name={self.func_name}, args={self.args}>'


class MethodCallNode(ASTNode):
    """
    Represents a method call on an instance, e.g., `my_vector.push(10)`.
    """
    def __init__(self, instance_expr: ASTNode, method_name: str, args: list[ASTNode]) -> None:
        """
        Initializes a MethodCallNode.

        :param instance_expr: The node representing the instance or object
                              (e.g., an IdentifierNode for 'my_vector').
        :param method_name: The string name of the method (e.g., 'push').
        :param args: A list of nodes representing the arguments passed to the method.
        """
        self.instance_expr = instance_expr
        self.method_name = method_name
        self.args = args

    def __repr__(self) -> str:
        """
        Provides a developer-friendly string representation of the node.
        """
        return f'<MethodCallNode instance={self.instance_expr} method="{self.method_name}" args={self.args}>'


class ReturnNode(ASTNode):
    def __init__(self, return_expr: ASTNode | None) -> None:
        self.return_expr = return_expr

    def __repr__(self) -> str:
        return f'<ReturnNode expr={self.return_expr}>'


class IfStatementNode(ASTNode):
    def __init__(self, condition: ASTNode, then_block: BlockNode, else_block: BlockNode | None = None, elif_blocks: list[tuple[ASTNode, BlockNode]] | None = None) -> None:
        self.condition = condition
        self.then_block = then_block
        self.elif_blocks = elif_blocks if elif_blocks else []  # list of (condition, block)
        self.else_block = else_block

    def __repr__(self) -> str:
        return f'<IfStatementNode condition={self.condition}, then={self.then_block}, elifs={self.elif_blocks}, else={self.else_block}>'


class WhileLoopNode(ASTNode):
    def __init__(self, condition: ASTNode, loop_block: BlockNode) -> None:
        self.condition = condition
        self.loop_block = loop_block

    def __repr__(self) -> str:
        return f'<WhileLoopNode condition={self.condition}, body={self.loop_block}>'


class ForLoopNode(ASTNode):  # Simple for i = 0; i < 10; i++ style
    def __init__(self, init_stmt: ASTNode, condition_expr: ASTNode, increment_stmt: ASTNode, loop_block: BlockNode) -> None:
        self.init_stmt = init_stmt
        self.condition_expr = condition_expr
        self.increment_stmt = increment_stmt
        self.loop_block = loop_block

    def __repr__(self) -> str:
        return f'<ForLoopNode init={self.init_stmt}, condition={self.condition_expr}, increment={self.increment_stmt}, body={self.loop_block}>'


class TypeCastNode(ASTNode):
    def __init__(self, target_type: str, expression: ASTNode) -> None:
        self.target_type = target_type
        self.expression = expression

    def __repr__(self) -> str:
        return f'<TypeCastNode type={self.target_type}, expr={self.expression}>'


class StructDefNode(ASTNode):
    def __init__(self, struct_name: str, fields: list[tuple[str, str]], functions: list[FunctionDefNode]) -> None:
        self.struct_name = struct_name
        self.fields = fields  # list of (field_name, field_type) tuples
        self.functions = functions

    def __repr__(self) -> str:
        return f'<StructDefNode name={self.struct_name}, fields={self.fields} functions={self.functions}>'


class StructInstantiationNode(ASTNode):  # let struct_var : StructName;
    def __init__(self, var_name: str, struct_type: str) -> None:
        self.var_name = var_name
        self.struct_type = struct_type

    def __repr__(self) -> str:
        return f'<StructInstantiationNode name={self.var_name}, type={self.struct_type}>'


class StructFieldAccessNode(ASTNode):  # struct_var.field
    def __init__(self, struct_var_name: str | ASTNode, field_name: str) -> None:
        self.struct_var_name = struct_var_name
        self.field_name = field_name

    def __repr__(self) -> str:
        return f'<StructFieldAccessNode struct={self.struct_var_name}, field={self.field_name}>'


class EnumDefNode(ASTNode):
    def __init__(self, enum_name: str, members: list[str]) -> None:
        self.enum_name = enum_name
        self.members: list[str] = members  # list of enum member names

    def __repr__(self) -> str:
        return f'<EnumDefNode name={self.enum_name}, members={self.members}>'


class EnumMemberNode(ASTNode):  # For referencing enum members like ErrorCode.DivisionByZero
    def __init__(self, enum_name: str, member_name: str) -> None:
        self.enum_name = enum_name
        self.member_name = member_name

    def __repr__(self) -> str:
        return f'<EnumMemberNode enum={self.enum_name}, member={self.member_name}>'


class ResultTypeNode(ASTNode):  # Result<int32, ErrorCode> - represent the type
    def __init__(self, ok_type: str, err_type: str) -> None:
        self.ok_type = ok_type
        self.err_type = err_type

    def __repr__(self) -> str:
        return f'<ResultTypeNode ok_type={self.ok_type}, err_type={self.err_type}>'


class OkResultNode(ASTNode):  # Ok(value)
    def __init__(self, value_expr: ASTNode) -> None:
        self.value_expr = value_expr

    def __repr__(self) -> str:
        return f'<OkResultNode value={self.value_expr}>'


class ErrResultNode(ASTNode):  # Err(ErrorCode.DivisionByZero)
    def __init__(self, error_expr: ASTNode) -> None:
        self.error_expr = error_expr

    def __repr__(self) -> str:
        return f'<ErrResultNode error={self.error_expr}>'


class LetMemoryNode(ASTNode):  # let var : int32 = 128;
    def __init__(self, var_name: str, data_type: str, value_expr: ASTNode | None = None) -> None:
        self.var_name = var_name
        self.data_type = data_type
        self.value_expr = value_expr

    def __repr__(self) -> str:
        return f'<LetMemoryNode name={self.var_name}, type={self.data_type}, value={self.value_expr}>'


class FreeMemoryNode(ASTNode):  # free var;
    def __init__(self, var_name: str) -> None:
        self.var_name = var_name

    def __repr__(self) -> str:
        return f'<FreeMemoryNode name={self.var_name}>'


class PointerRefNode(ASTNode):  # &var
    def __init__(self, var_name: str | ASTNode) -> None:
        self.var_name = var_name

    def __repr__(self) -> str:
        return f'<PointerRefNode var={self.var_name}>'


class PointerDerefNode(ASTNode):  # *ptr
    def __init__(self, pointer_expr: ASTNode) -> None:
        self.pointer_expr = pointer_expr

    def __repr__(self) -> str:
        return f'<PointerDerefNode pointer={self.pointer_expr}>'


class PrintStatementNode(ASTNode):  # print(expr1, expr2, ...)
    def __init__(self, expressions: list[ASTNode]) -> None:
        self.expressions = expressions

    def __repr__(self) -> str:
        return f'<PrintStatementNode expressions={self.expressions}>'


class SpawnTaskNode(ASTNode):  # spawn task fetchData(...) { ... }
    def __init__(self, task_name: str, params: list[tuple[str, str]], body: BlockNode) -> None:
        self.task_name = task_name
        self.params = params
        self.body = body

    def __repr__(self) -> str:
        return f'<SpawnTaskNode name={self.task_name}, params={self.params}, body={self.body}>'


class ImportNode(ASTNode):
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name

    def __repr__(self) -> str:
        return f'<ImportNode name={self.module_name}>'


class TryNode(ASTNode):
    def __init__(self, try_block: BlockNode, catch_block: BlockNode | None) -> None:
        self.try_block = try_block
        self.catch_block = catch_block

    def __repr__(self) -> str:
        return f'<TryNode try={self.try_block}, catch={self.catch_block}>'