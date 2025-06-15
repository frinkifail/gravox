from typing import TYPE_CHECKING
from grvast import ASTNode, AllocMemoryNode, ArrayIndexNode, ArrayLiteralNode, BlockNode, CharLiteralNode, EnumMemberNode, FloatLiteralNode, FunctionCallNode, IdentifierNode, IntLiteralNode, MethodCallNode, NullLiteralNode, ProgramNode, StringLiteralNode, StructFieldAccessNode, TypeCastNode, UnaryOpNode
from lsp.newlsp.coredata import RuntimeContext
# from lsp.newlsp.coredata import AnySymbolData
if TYPE_CHECKING:
    from lsp.newlsp.lsp import NewLSP

class StaticAnalyser:
    def __init__(self, lsp: "NewLSP", filename: str, program: ProgramNode) -> None:
        self.program = program
        self.ls = lsp
        self.filename = filename

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
            # return [self.eval_expression(i) for i in node.elements]
        elif isinstance(node, IdentifierNode):
            # print("ident", node)
            raise NotImplementedError("TBA") # TODO
            # var_name = node.name
            # if var_name in self.symbol_table:
            #     x = self.symbol_table[var_name]
            #     # print(self.resolving_context, type(x["value"]))
            #     if isinstance(x["value"], dict) and self.resolving_context == "pretty":
            #         self.resolving_context = "normal"
            #         x = f"{x.get('data_type') or '*unknown*'} {{ {", ".join([f'{k}: {v if v is not None else 'null'}' for k, v in x['value'].items()])} }}"
            #         # print("pretty", x)
            #         return x
            #     return x["value"]
            # elif var_name in self.enum_definitions: # Check if identifier is an enum
            #     return var_name # Return enum name itself for now
            # else:
            #     raise Exception(f"Variable '{var_name}' not declared")
        elif isinstance(node, UnaryOpNode):
            raise NotImplementedError("TBA")
            # value = self.eval_expression(node.expr)
            # op_type = node.op
            # if op_type == TokenType.MINUS: return -value
            # elif op_type == TokenType.BIT_NOT: return ~value # Bitwise NOT
            # elif op_type == TokenType.POINTER_DEREF: # *ptr
            #     if isinstance(value, int): # Address should be an integer address
            #         if value in self.memory:
            #             return self.memory[value] # Dereference memory address
            #         else:
            #             raise Exception(f"Invalid memory access at address {value}")
            #     else:
            #         raise Exception("Pointer dereference expects a memory address (integer)")
            # elif op_type == TokenType.POINTER_REF: # &var
            #     if isinstance(node.expr, IdentifierNode):
            #         var_name = node.expr.name
            #         # print("pointer")
            #         if var_name in self.symbol_table:
            #             # print(var_name, self.symbol_table[var_name])
            #             return self.symbol_table[var_name]["address"] # Return memory address of variable
            #         else:
            #             raise Exception(f"Variable '{var_name}' not declared")
            #     else:
            #         raise Exception("Pointer reference '&' can only be applied to variables")

        elif isinstance(node, FunctionCallNode):
            # TODO
            return self.eval_function_call(node)
        elif isinstance(node, TypeCastNode):
            expression_value = self.eval_expression(node.expression)
            return self.check_valid_cast(expression_value, node.target_type)
        elif isinstance(node, StructFieldAccessNode):
            raise NotImplementedError("TBA")
            # struct_var_name = str(node.struct_var_name)
            # field_name = node.field_name
            # if struct_var_name in self.symbol_table:
            #     if (sv := self.symbol_table[struct_var_name])["type"] in self.struct_definitions:
            #         struct_instance = self.symbol_table[struct_var_name]["value"]
            #         if field_name in struct_instance:
            #             # print(struct_instance)
            #             try:
            #                 return struct_instance[field_name]
            #             except Exception as e:
            #                 print(self.symbol_table[struct_var_name], struct_instance, e)
            #         else:
            #             raise Exception(f"Struct '{self.symbol_table[struct_var_name]['type']}' does not have field '{field_name}'")
            #     else:
            #         if sv["type"] == "array":
            #             return sv["value"][int(field_name)]
            #         if sv["type"] == "any":
            #             try:
            #                 return sv["value"][field_name]
            #             except KeyError as e:
            #                 raise KeyError(f"Key not found: {e}")
            #         raise Exception(f"'{struct_var_name}' is not a struct variable")
            # else:
            #     if enum_item := self.enum_definitions.get(struct_var_name):
            #         return next(filter(lambda y: y == field_name, enum_item.members))
            #         # return None
            #     raise Exception(f"Struct variable '{struct_var_name}' not declared")
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
            raise NotImplementedError("TBA") # TODO
            # instance_type = self._get_expression_type(node.instance_expr)
            # instance_value = self.eval_expression(node.instance_expr)

            # method_key = f"{instance_type}::{node.method_name}"
            # if method_key not in self.function_table:
            #     # print(self.function_table)
            #     raise Exception(f"Method '{node.method_name}' not found for type '{instance_type}'")

            # method_def = self.function_table[method_key]
            # args = [self.eval_expression(arg) for arg in node.args]

            # self_context = {"type": instance_type, "value": instance_value, "address": -1} # address is tricky here
            # return self._execute_callable(method_def, args, self_instance=self_context)

        return "unknown"
    
    def eval_statement(self, node: ASTNode):
        if isinstance(node, ProgramNode) or isinstance(node, BlockNode):
            for i in node.statements:
                self.eval_statement(i)
        elif isinstance(node, AllocMemoryNode):
            et = self.eval_variable(node)
            self.ls.data_table[self.filename].symbols[node.var_name] = RuntimeContext.Symbol(node.var_name, RuntimeContext.Symbol.SymbolKind.VARIABLE, RuntimeContext.VariableSymbolData(f"{et} [defined as: {node.data_type}]"))
            # self.ls.show_message("i commit war crimes")
        else:
            self.eval_expression(node)
    
    def eval_variable(self, node: AllocMemoryNode):
        return "unknown"

    def eval_function_call(self, node: FunctionCallNode):
        return "unknown"

    def check_valid_cast(self, type1: str, type2: str) -> str:
        return "invalid"
