from pathlib import Path
from typing import TYPE_CHECKING, cast
from grvast import ASTNode, ForLoopNode, IfStatementNode, ImportNode, LetMemoryNode, ArrayIndexNode, ArrayLiteralNode, BlockNode, CharLiteralNode, EnumMemberNode, FloatLiteralNode, FunctionCallNode, FunctionDefNode, IdentifierNode, IntLiteralNode, MethodCallNode, NullLiteralNode, ProgramNode, StringLiteralNode, StructDefNode, StructFieldAccessNode, TryNode, TypeCastNode, UnaryOpNode, VarAssignNode, WhileLoopNode
from lexing import tokenize
from lsp.newlsp.coredata import RuntimeContext, single_range
from lsprotocol.types import Diagnostic, Position

from parser import Parser
# from lsp.newlsp.coredata import AnySymbolData
if TYPE_CHECKING:
    from lsp.newlsp.lsp import NewLSP

class StaticAnalyser:
    def __init__(self, lsp: "NewLSP", filename: str, program: ProgramNode) -> None:
        self.program = program
        self.ls = lsp
        self.filename = filename
        self.diagnostics: list[Diagnostic] = []

        if filename not in self.ls.data_table:
            self.ls.data_table[filename] = RuntimeContext()

    def eval_expression(self, node: ASTNode) -> str: # type
        if isinstance(node, IntLiteralNode):
            # return node.value
            return "int(unknown size)"
        elif isinstance(node, FloatLiteralNode):
            return "float"
        elif isinstance(node, CharLiteralNode):
            return "char"
        elif isinstance(node, StringLiteralNode):
            return "string"
        elif isinstance(node, NullLiteralNode):
            return "null"
        elif isinstance(node, ArrayLiteralNode):
            return "array<unknown>"
        elif isinstance(node, IdentifierNode):
            pass # TODO
        elif isinstance(node, UnaryOpNode):
            pass # TODO
        elif isinstance(node, ArrayIndexNode):
            raise NotImplementedError("TBA") # TODO
            # array_name = str(node.array_name)
            # index = self.eval_expression(node.index_expr)
            # if array_name in self.symbol_table:
            #     array_value = self.symbol_table[array_name]["value"]
            #     try:
            #         index = int(index)
            #         if isinstance(array_value, list) and 0 <= index < len(array_value):
            #             return array_value[index]
            #         else:
            #             raise Exception(f"Array '{array_name}' index out of range")
            #     except ValueError:
            #         raise Exception("Array index expression must be an integer literal")
            # else:
            #     raise Exception(f"Array '{array_name}' not declared")
        # elif isinstance(node, OkResultNode): # NOTE: deprecated
        #     return {"type": "Ok", "value": self.eval_expression(node.value_expr)}
        # elif isinstance(node, ErrResultNode):
        #     error_value = self.eval_expression(node.error_expr) # Could be enum member etc.
        #     return {"type": "Err", "error": error_value}
        elif isinstance(node, EnumMemberNode): # Referencing enum member value - for now return string name itself.
            return node.enum_name # Could be improved to store enum values if needed
        elif isinstance(node, MethodCallNode):
            pass # TODO

        return "unknown"

    def get_symbol_maybe(self, name: str):
        return self.ls.data_table[self.filename].symbols.get(name)

    def get_symbol(self, name: str):
        x = self.get_symbol_maybe(name)
        if not x:
            raise KeyError(f"'{name}'")
        return x

    def set_symbol(self, name: str, symbol: RuntimeContext.Symbol):
        self.ls.data_table[self.filename].symbols[name] = symbol
        return symbol
    
    def eval_statement(self, node: ASTNode):
        if isinstance(node, ProgramNode) or isinstance(node, BlockNode):
            for i in node.statements:
                self.eval_statement(i)
        elif isinstance(node, ImportNode):
            path = Path(node.module_name + ".grv")
            if not path.exists():
                raise Exception(f"Module '{node.module_name}' not found")
            with open(path, 'r') as f:
                source_code = f.read()
            parser = Parser(tokenize(source_code))
            program_node = parser.parse_program()
            self.eval_statement(program_node)
        elif isinstance(node, LetMemoryNode):
            # et = self.eval_variable(node)
            self.set_symbol(node.var_name, RuntimeContext.Symbol(node.var_name, RuntimeContext.Symbol.SymbolKind.VARIABLE, RuntimeContext.VariableSymbolData(f"{node.data_type}")))
            # self.ls.show_message_log(self.ls.data_table)
            # self.ls.show_message("i commit war crimes")
        elif isinstance(node, FunctionDefNode):
            self.set_symbol(str(node.func_name), RuntimeContext.Symbol(str(node.func_name), RuntimeContext.Symbol.SymbolKind.FUNCTION, RuntimeContext.FunctionSymbolData(dict(node.params), str(node.return_type))))
            self.eval_statement(node.body)
        elif isinstance(node, StructDefNode):
            self.set_symbol(node.struct_name, RuntimeContext.Symbol(node.struct_name, RuntimeContext.Symbol.SymbolKind.STRUCT, RuntimeContext.StructSymbolData(dict(node.fields), dict([(str(i.func_name), RuntimeContext.FunctionSymbolData(dict(i.params), str(i.return_type))) for i in node.functions]))))
        elif isinstance(node, WhileLoopNode):
            self.eval_statement(node.loop_block)
        elif isinstance(node, TryNode):
            self.eval_statement(node.try_block)
            if node.catch_block: self.eval_statement(node.catch_block)
        elif isinstance(node, IfStatementNode):
            self.eval_statement(node.then_block)
            for i in node.elif_blocks:
                if isinstance(i, tuple):
                    for j in i:
                        self.eval_statement(j)
                else:
                    self.eval_statement(i)
            if node.else_block: self.eval_statement(node.else_block)
        elif isinstance(node, ForLoopNode):
            self.eval_statement(node.init_stmt)
            self.eval_statement(node.loop_block)
        elif isinstance(node, VarAssignNode):
            valtype = self.eval_expression(node.value_expr)
            var = self.get_symbol_maybe(node.var_name)
            if not var:
                self.diagnostics.append(Diagnostic(single_range(Position(node.line, node.column)), f"undefined variable '{node.var_name}'"))
                return
            if var.kind != var.SymbolKind.VARIABLE:
                self.diagnostics.append(Diagnostic(single_range(Position(node.line, node.column)), f"assigning to a non-variable '{node.var_name}'"))
                return
            vardata = cast(RuntimeContext.VariableSymbolData, var.data)
            if valtype != vardata.type:
                self.diagnostics.append(Diagnostic(single_range(Position(node.line, node.column)), f"type {valtype} and {vardata.type} is not compatible"))
                return
        else:
            self.eval_expression(node)
    
    # def eval_variable(self, node: LetMemoryNode):
    #     return "unknown"
