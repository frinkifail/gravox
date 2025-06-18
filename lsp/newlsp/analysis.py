from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
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
            return "int8" # default size
        elif isinstance(node, FloatLiteralNode):
            return "float32" # default size
        elif isinstance(node, CharLiteralNode):
            return "char"
        elif isinstance(node, StringLiteralNode):
            return "string"
        elif isinstance(node, NullLiteralNode):
            return "null"
        elif isinstance(node, ArrayLiteralNode):
            return "array"
        elif isinstance(node, IdentifierNode):
            pass # TODO
        elif isinstance(node, UnaryOpNode):
            pass # TODO
        elif isinstance(node, ArrayIndexNode):
            pass # TODO
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
        elif isinstance(node, FunctionCallNode):
            try:
                func_name = str(node.func_name)
                if func_name in self.ls.data_table[self.filename].symbols:
                    sym = self.ls.data_table[self.filename].symbols[func_name]
                    if sym.kind == RuntimeContext.Symbol.SymbolKind.FUNCTION:
                        typ = cast(RuntimeContext.FunctionSymbolData, sym.data).return_type
                        if isinstance(typ, tuple):
                            return typ[0]
                        return typ
                    else:
                        raise Exception(f"'{func_name}' is not a function")
                else:
                    raise Exception(f"Function '{func_name}' not found")
            except Exception as e:
                self.diagnostics.append(Diagnostic(
                    range=single_range(Position(node.line, node.column)),
                    message=str(e)
                ))

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
            try:
                self._handle_variable_assignment(node.var_name, self.eval_expression(node.value_expr))
            except Exception as e:
                self.diagnostics.append(Diagnostic(
                    range=single_range(Position(node.line, node.column)),
                    message=str(e)
                ))
        else:
            self.eval_expression(node)
    
    def _handle_variable_assignment(self, var_name: str, new_value_type: str):
        if '.' in var_name:  # Struct field assignment e.g., vec.x = 10;
            struct_var_name, field_name = var_name.split('.', 1)
            sym = self.get_symbol_maybe(struct_var_name)
            if not sym:
                raise Exception(f"undefined variable '{struct_var_name}'")
            if sym.kind != RuntimeContext.Symbol.SymbolKind.VARIABLE:
                raise Exception(f"assigning to a non-variable '{struct_var_name}'")
            struct = self.get_symbol_maybe(cast(RuntimeContext.VariableSymbolData, sym.data).type)
            if not struct or struct.kind != RuntimeContext.Symbol.SymbolKind.STRUCT:
                raise Exception(f"'{struct_var_name}' is not a struct variable")
            sd = cast(RuntimeContext.StructSymbolData, struct.data)
            if field_name not in sd.fields:
                raise Exception(f"Struct '{struct_var_name}' does not have field '{field_name}'")
            field_type = sd.fields[field_name]
            if new_value_type != field_type:
                raise Exception(f"type {new_value_type} and {field_type} is not compatible")
        else:
            sym = self.get_symbol_maybe(var_name)
            if not sym:
                raise Exception(f"undefined variable '{var_name}'")
            if sym.kind != RuntimeContext.Symbol.SymbolKind.VARIABLE:
                raise Exception(f"assigning to a non-variable '{var_name}'")
            vardata = cast(RuntimeContext.VariableSymbolData, sym.data)
            if new_value_type != vardata.type:
                raise Exception(f"type {new_value_type} and {vardata.type} is not compatible")
    
    # def eval_variable(self, node: LetMemoryNode):
    #     return "unknown"
