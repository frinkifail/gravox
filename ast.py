class ASTNode:
    pass

class ProgramNode(ASTNode):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f'<ProgramNode statements={self.statements}>'

class BlockNode(ASTNode):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f'<BlockNode statements={self.statements}>'

class VarDeclarationNode(ASTNode):
    def __init__(self, var_name, data_type, value_expr=None):
        self.var_name = var_name
        self.data_type = data_type
        self.value_expr = value_expr

    def __repr__(self):
        return f'<VarDeclarationNode name={self.var_name}, type={self.data_type}, value={self.value_expr}>'

class VarAssignNode(ASTNode):
    def __init__(self, var_name, value_expr):
        self.var_name = var_name
        self.value_expr = value_expr

    def __repr__(self):
        return f'<VarAssignNode name={self.var_name}, value={self.value_expr}>'

class IdentifierNode(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<IdentifierNode name={self.name}>'

class IntLiteralNode(ASTNode):
    def __init__(self, value):
        self.value = int(value)

    def __repr__(self):
        return f'<IntLiteralNode value={self.value}>'

class FloatLiteralNode(ASTNode):
    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return f'<FloatLiteralNode value={self.value}>'

class CharLiteralNode(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'<CharLiteralNode value={self.value}>'

class StringLiteralNode(ASTNode):
    def __init__(self, value) -> None:
        self.value = str(value)

    def __repr__(self) -> str:
        return f"<StringLiteralNode value={self.value}>"

class ArrayLiteralNode(ASTNode):
    def __init__(self, elements):
        self.elements = elements

    def __repr__(self):
        return f"<ArrayLiteralNode elements={self.elements}>"

class ArrayIndexNode(ASTNode):
    def __init__(self, array_name, index_expr):
        self.array_name = array_name
        self.index_expr = index_expr

    def __repr__(self):
        return f"<ArrayIndexNode array={self.array_name}, index={self.index_expr}>"

class NullLiteralNode(ASTNode):
    def __init__(self):
        pass
    def __repr__(self):
        return "<NullLiteralNode>"

class BinaryOpNode(ASTNode):
    def __init__(self, op, left_expr, right_expr):
        self.op = op
        self.left_expr = left_expr
        self.right_expr = right_expr

    def __repr__(self):
        return f'<BinaryOpNode op={self.op}, left={self.left_expr}, right={self.right_expr}>'

class UnaryOpNode(ASTNode): # For bitwise NOT, pointer dereference etc.
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __repr__(self):
        return f'<UnaryOpNode op={self.op}, expr={self.expr}>'

class FunctionDefNode(ASTNode):
    def __init__(self, func_name, params, return_type, body):
        self.func_name = func_name
        self.params = params # list of (param_name, param_type) tuples
        self.return_type = return_type
        self.body = body

    def __repr__(self):
        return f'<FunctionDefNode name={self.func_name}, params={self.params}, return_type={self.return_type}, body={self.body}>'

class FunctionCallNode(ASTNode):
    def __init__(self, func_name, args):
        self.func_name = func_name
        self.args = args

    def __repr__(self):
        return f'<FunctionCallNode name={self.func_name}, args={self.args}>'

class MethodCallNode(ASTNode):
    """
    Represents a method call on an instance, e.g., `my_vector.push(10)`.
    """
    def __init__(self, instance_expr, method_name, args):
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

    def __repr__(self):
        """
        Provides a developer-friendly string representation of the node.
        """
        return f'<MethodCallNode instance={self.instance_expr} method="{self.method_name}" args={self.args}>'

class ReturnNode(ASTNode):
    def __init__(self, return_expr):
        self.return_expr = return_expr

    def __repr__(self):
        return f'<ReturnNode expr={self.return_expr}>'

class IfStatementNode(ASTNode):
    def __init__(self, condition, then_block, else_block=None, elif_blocks=None):
        self.condition = condition
        self.then_block = then_block
        self.elif_blocks = elif_blocks if elif_blocks else [] # list of (condition, block)
        self.else_block = else_block

    def __repr__(self):
        return f'<IfStatementNode condition={self.condition}, then={self.then_block}, elifs={self.elif_blocks}, else={self.else_block}>'

class WhileLoopNode(ASTNode):
    def __init__(self, condition, loop_block):
        self.condition = condition
        self.loop_block = loop_block

    def __repr__(self):
        return f'<WhileLoopNode condition={self.condition}, body={self.loop_block}>'

class ForLoopNode(ASTNode): # Simple for i = 0; i < 10; i++ style
    def __init__(self, init_stmt, condition_expr, increment_stmt, loop_block):
        self.init_stmt = init_stmt
        self.condition_expr = condition_expr
        self.increment_stmt = increment_stmt
        self.loop_block = loop_block

    def __repr__(self):
        return f'<ForLoopNode init={self.init_stmt}, condition={self.condition_expr}, increment={self.increment_stmt}, body={self.loop_block}>'

class TypeCastNode(ASTNode):
    def __init__(self, target_type, expression):
        self.target_type = target_type
        self.expression = expression

    def __repr__(self):
        return f'<TypeCastNode type={self.target_type}, expr={self.expression}>'

class StructDefNode(ASTNode):
    def __init__(self, struct_name, fields, functions):
        self.struct_name = struct_name
        self.fields = fields # list of (field_name, field_type) tuples
        self.functions = functions

    def __repr__(self):
        return f'<StructDefNode name={self.struct_name}, fields={self.fields} functions={self.functions}>'

class StructInstantiationNode(ASTNode): # alloc struct_var : StructName;
    def __init__(self, var_name, struct_type):
        self.var_name = var_name
        self.struct_type = struct_type

    def __repr__(self):
        return f'<StructInstantiationNode name={self.var_name}, type={self.struct_type}>'

class StructFieldAccessNode(ASTNode): # struct_var.field
    def __init__(self, struct_var_name, field_name):
        self.struct_var_name = struct_var_name
        self.field_name = field_name

    def __repr__(self):
        return f'<StructFieldAccessNode struct={self.struct_var_name}, field={self.field_name}>'

class EnumDefNode(ASTNode):
    def __init__(self, enum_name, members):
        self.enum_name = enum_name
        self.members: list[str] = members # list of enum member names

    def __repr__(self):
        return f'<EnumDefNode name={self.enum_name}, members={self.members}>'

class EnumMemberNode(ASTNode): # For referencing enum members like ErrorCode.DivisionByZero
    def __init__(self, enum_name, member_name):
        self.enum_name = enum_name
        self.member_name = member_name

    def __repr__(self):
        return f'<EnumMemberNode enum={self.enum_name}, member={self.member_name}>'

class ResultTypeNode(ASTNode): # Result<int32, ErrorCode> - represent the type
    def __init__(self, ok_type, err_type):
        self.ok_type = ok_type
        self.err_type = err_type

    def __repr__(self):
        return f'<ResultTypeNode ok_type={self.ok_type}, err_type={self.err_type}>'

class OkResultNode(ASTNode): # Ok(value)
    def __init__(self, value_expr):
        self.value_expr = value_expr

    def __repr__(self):
        return f'<OkResultNode value={self.value_expr}>'

class ErrResultNode(ASTNode): # Err(ErrorCode.DivisionByZero)
    def __init__(self, error_expr):
        self.error_expr = error_expr

    def __repr__(self):
        return f'<ErrResultNode error={self.error_expr}>'

class AllocMemoryNode(ASTNode): # alloc var : int32 = 128;
    def __init__(self, var_name, data_type, value_expr=None):
        self.var_name = var_name
        self.data_type = data_type
        self.value_expr = value_expr

    def __repr__(self):
        return f'<AllocMemoryNode name={self.var_name}, type={self.data_type}, value={self.value_expr}>'

class FreeMemoryNode(ASTNode): # free var;
    def __init__(self, var_name):
        self.var_name = var_name

    def __repr__(self):
        return f'<FreeMemoryNode name={self.var_name}>'

class PointerRefNode(ASTNode): # &var
    def __init__(self, var_name):
        self.var_name = var_name

    def __repr__(self):
        return f'<PointerRefNode var={self.var_name}>'

class PointerDerefNode(ASTNode): # *ptr
    def __init__(self, pointer_expr):
        self.pointer_expr = pointer_expr

    def __repr__(self):
        return f'<PointerDerefNode pointer={self.pointer_expr}>'

class PrintStatementNode(ASTNode): # print(expr1, expr2, ...)
    def __init__(self, expressions):
        self.expressions = expressions

    def __repr__(self):
        return f'<PrintStatementNode expressions={self.expressions}>'

class SpawnTaskNode(ASTNode): # spawn task fetchData(...) { ... }
    def __init__(self, task_name, params, body):
        self.task_name = task_name
        self.params = params
        self.body = body

    def __repr__(self):
        return f'<SpawnTaskNode name={self.task_name}, params={self.params}, body={self.body}>'

class ImportNode(ASTNode):
    def __init__(self, module_name):
        self.module_name = module_name

    def __repr__(self):
        return f'<ImportNode name={self.module_name}>'

class TryNode(ASTNode):
    def __init__(self, try_block, catch_block):
        self.try_block = try_block
        self.catch_block = catch_block

    def __repr__(self):
        return f'<TryNode try={self.try_block}, catch={self.catch_block}>'
