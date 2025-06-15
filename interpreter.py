from pathlib import Path
from typing import Any, cast

from grvast import EnumMemberNode, ErrResultNode, OkResultNode, StructFieldAccessNode, TypeCastNode, FunctionCallNode, \
    IdentifierNode, UnaryOpNode, BinaryOpNode, NullLiteralNode, StringLiteralNode, CharLiteralNode, FloatLiteralNode, \
    IntLiteralNode, ReturnNode, SpawnTaskNode, VarAssignNode, StructInstantiationNode, PrintStatementNode, \
    VarDeclarationNode, EnumDefNode, StructDefNode, ForLoopNode, WhileLoopNode, IfStatementNode, FunctionDefNode, \
    FreeMemoryNode, AllocMemoryNode, BlockNode, ProgramNode, ImportNode, TryNode, ArrayLiteralNode, ArrayIndexNode, \
    MethodCallNode
from lexing import TokenType, tokenize
from parser import Parser
from stdlib import Stdlib


def get_type_size(data_type): # Placeholder - needs proper size mapping.
    if data_type in ["int8", "uint8", "char"]: return 1
    elif data_type in ["int16", "uint16"]: return 2
    elif data_type in ["int32", "uint32", "float32"]: return 4
    elif data_type in ["int64", "uint64", "float64"]: return 8
    return 4 # Default size if type not recognized


def execute_return(node):
    return node # Simply return the ReturnNode itself, function call execution will handle it.

class CappedMemoryDict[K, V](dict):
    def __init__(self, max_items: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_items = max_items
    def __setitem__(self, key, value):
        if int(key) >= self.max_items:
            raise Exception(f"segmentation fault")
        super().__setitem__(key, value)

class Interpreter:
    def __init__(self, heap_size=1024):
        self.symbol_table: dict[str, Any] = {} # {var_name: (data_type, value, memory_address)} - for variables
        self.function_table: dict[str, FunctionDefNode] = {} # {func_name: FunctionDefNode} - for functions
        self.struct_definitions: dict[str, StructDefNode] = {
            # "Result": StructDefNode("Result", [("success", "bool"), ("value", "any")], []),
        } # {struct_name: StructDefNode}
        self.enum_definitions: dict[str, EnumDefNode] = {} # {enum_name: EnumDefNode}
        self.memory: CappedMemoryDict[int, Any] = CappedMemoryDict(heap_size) # {memory_address: value} - simulate memory
        self.next_memory_address = 0
        self.resolving_context = "normal" # figure this shit out yourself
        self.heap_size = heap_size
        self.stdlib = Stdlib(self)
        self.last_updated_index = 0
        self.last_node = None

    def allocate_memory(self, data_type): # Simple memory allocation
        address = self.next_memory_address
        size = get_type_size(data_type) # Placeholder for size calculation
        self.next_memory_address += size # Increment for next allocation. In real scenario, more sophisticated approach
        return address

    def free_memory(self, address): # Simple free - for now just remove from memory dict if needed. More complex in real
        if address in self.memory:
            del self.memory[address]

    def interpret(self, program_node):
        for statement in program_node.statements:
            self.execute_statement(statement)
        return None # Or return something meaningful at the end

    def execute_statement(self, node):
        self.last_updated_index += 1
        self.last_node = node
        if isinstance(node, ProgramNode) or isinstance(node, BlockNode):
            for statement in node.statements:
                self.execute_statement(statement)
        elif isinstance(node, AllocMemoryNode):
            self.execute_alloc_memory(node)
        elif isinstance(node, FreeMemoryNode):
            self.execute_free_memory(node)
        elif isinstance(node, VarAssignNode):
            self.execute_variable_assignment(node)
        elif isinstance(node, FunctionDefNode):
            self.function_table[str(node.func_name)] = node
        elif isinstance(node, FunctionCallNode):
            return self.execute_function_call(node)
        elif isinstance(node, ReturnNode):
            return execute_return(node)
        elif isinstance(node, IfStatementNode):
            self.execute_if_statement(node)
        elif isinstance(node, WhileLoopNode):
            self.execute_while_loop(node)
        elif isinstance(node, ForLoopNode):
            self.execute_for_loop(node)
        elif isinstance(node, StructDefNode):
            self.struct_definitions[node.struct_name] = node
            for function in node.functions:
                self.function_table[node.struct_name + "::" + str(function.func_name)] = function
        elif isinstance(node, EnumDefNode):
            self.enum_definitions[node.enum_name] = node
        elif isinstance(node, VarDeclarationNode): # Deprecated - use AllocMemoryNode
            self.execute_variable_declaration(node)
        elif isinstance(node, PrintStatementNode):
            self.execute_print_statement(node)
        elif isinstance(node, StructInstantiationNode): # Not directly executable, handled by AllocMemoryNode if struct type
            pass # Handled in execute_alloc_memory when type is struct
        elif isinstance(node, VarAssignNode): # already handled above, check again
            self.execute_variable_assignment(node)
        elif isinstance(node, SpawnTaskNode):
            self.execute_spawn_task(node)
        elif isinstance(node, ImportNode):
            self.execute_import(node)
        elif isinstance(node, TryNode):
            try:
                # print("trying")
                self.execute_statement(node.try_block)
            except Exception as e:
                # print("caught")
                self.symbol_table["e"] = {"type": "any", "value": e, "address": self.next_memory_address}
                self.execute_statement(node.catch_block)
        else:
            self.evaluate_expression(node) # For expression statements (e.g., function call returning value and ignoring it for now)

    def execute_import(self, node: ImportNode):
        if node.module_name.endswith('_py'):
            raise Exception("Native modules are a work-in-progress.")

        path = Path(node.module_name + ".grv")
        if not path.exists():
            raise Exception(f"Module '{node.module_name}' not found")
        with open(path, 'r') as f:
            source_code = f.read()
        parser = Parser(tokenize(source_code))
        program_node = parser.parse_program()
        # print("Imported AST Tree (Debug):")
        # print(program_node)
        interpreter = Interpreter(self.heap_size)
        interpreter.next_memory_address = self.next_memory_address
        interpreter.interpret(program_node)
        self.function_table.update(interpreter.function_table)
        self.symbol_table.update(interpreter.symbol_table)
        self.struct_definitions.update(interpreter.struct_definitions)
        self.enum_definitions.update(interpreter.enum_definitions)
        self.memory.update(interpreter.memory)
        self.next_memory_address = interpreter.next_memory_address

    def _execute_callable(self, func_def: FunctionDefNode, args, self_instance=None):
        if len(args) != len(func_def.params):
            raise Exception(f"Incorrect number of arguments for function '{func_def.func_name}'. Expected {len(func_def.params)}, got {len(args)}")

        # Create a new scope for the function/method call
        prev_symbol_table = self.symbol_table
        self.symbol_table = self.symbol_table.copy()

        # If it's a method call, inject 'self' into the scope
        if self_instance:
            self.symbol_table['self'] = self_instance

        # Bind arguments to parameters in the new scope
        for i, param in enumerate(func_def.params):
            param_name, param_type = param
            typed_arg_value = self.cast_value_to_type(args[i], param_type)
            self.symbol_table[param_name] = {"type": param_type, "value": typed_arg_value, "address": self.allocate_memory(param_type)}

        # Execute the body
        return_value = None
        for statement in func_def.body.statements:
            result = self.execute_statement(statement)
            if isinstance(result, ReturnNode):
                return_value = self.evaluate_expression(result.return_expr)
                break

        # Restore the previous scope
        self.symbol_table = prev_symbol_table

        return self.cast_value_to_type(return_value, func_def.return_type) if return_value is not None else None

    def execute_function_call(self, node: FunctionCallNode):
        func_name = node.func_name.name # Assuming func_name is now an IdentifierNode
        # if isinstance(node.func_name, IdentifierNode):
        #     func_name = cast(IdentifierNode, node.func_name).name
        args = [self.evaluate_expression(arg) for arg in node.args]

        # print(f"fnc: {func_name}({args})")

        if func_name not in self.function_table:
            
            builtin = self.stdlib[func_name]
            if builtin:
                return builtin(args)
            raise Exception(f"Function '{func_name}' not defined")

        func_def = self.function_table[func_name]
        return self._execute_callable(func_def, args)

    def execute_alloc_memory(self, node):
        var_name = node.var_name
        data_type = node.data_type
        memory_address = self.allocate_memory(data_type)

        if data_type in self.struct_definitions: # Struct allocation
            struct_def = self.struct_definitions[data_type]
            struct_instance = {}
            for field_name, field_type in struct_def.fields:
                struct_instance[field_name] = self.get_default_value_for_type(field_type) # Initialize fields to None or default value
            initial_value = struct_instance
        elif node.value_expr:
            initial_value = self.evaluate_expression(node.value_expr)
            initial_value = self.cast_value_to_type(initial_value, data_type) # Type casting on initialization
        else:
            initial_value = self.get_default_value_for_type(data_type) # Default if no initializer

        self.symbol_table[var_name] = {"type": data_type, "address": memory_address, "value": initial_value, "data_type": data_type}
        self.memory[memory_address] = initial_value # Store in memory

    def execute_free_memory(self, node):
        var_name = node.var_name
        if var_name in self.symbol_table:
            memory_address = self.symbol_table[var_name]["address"]
            self.free_memory(memory_address)
            del self.symbol_table[var_name]
        else:
            raise Exception(f"Cannot free undeclared variable '{var_name}'")

    def execute_variable_declaration(self, node):
        var_name = node.var_name
        data_type = node.data_type
        initial_value = self.evaluate_expression(node.value_expr) if node.value_expr else self.get_default_value_for_type(data_type)

        # Create symbol table entry with memory allocation
        self.symbol_table[var_name] = {"type": data_type, "value": initial_value, "address": self.next_memory_address}
        self.allocate_memory(data_type)

        # If there's an initial value, use the same assignment logic as regular assignments
        if node.value_expr:
            self._handle_variable_assignment(var_name, initial_value)

    def _get_expression_type(self, node):
        """Helper to find the data type of an expression result."""
        if isinstance(node, IdentifierNode):
            if node.name in self.symbol_table:
                x = self.symbol_table[node.name]
                return x.get("type") or x.get("data_type") or "*unknown*"
        elif isinstance(node, FunctionCallNode):
            if node.func_name in self.function_table:
                return self.function_table[str(node.func_name)].return_type
        elif isinstance(node, MethodCallNode):
            instance_type = self._get_expression_type(node.instance_expr)
            method_key = f"{instance_type}::{node.method_name}"
            if method_key in self.function_table:
                return self.function_table[method_key].return_type
        # Add more cases for other node types if necessary
        return "any" # Default fallback

    def execute_variable_assignment(self, node):
        var_name = node.var_name
        new_value = self.evaluate_expression(node.value_expr)
        self._handle_variable_assignment(var_name, new_value)

    def _handle_variable_assignment(self, var_name, new_value):
        if '.' in var_name:  # Struct field assignment e.g., vec.x = 10;
            struct_var_name, field_name = var_name.split('.', 1)
            if struct_var_name in self.symbol_table:
                if self.symbol_table[struct_var_name]["type"] in self.struct_definitions:
                    if field_name in self.symbol_table[struct_var_name]["value"]:  # Check if field exists in struct instance
                        field_type = next(filter(lambda x: x[0] == field_name, self.struct_definitions[self.symbol_table[struct_var_name]["type"]].fields), 'null')[1]
                        typed_value = self.cast_value_to_type(new_value, field_type)
                        current_struct_value = self.symbol_table[struct_var_name]["value"]
                        current_struct_value[field_name] = typed_value  # Assign new value to struct field
                        self.symbol_table[struct_var_name]["value"] = current_struct_value  # Update symbol table with modified struct
                        memory_address = self.symbol_table[struct_var_name]["address"]
                        self.memory[memory_address] = current_struct_value  # Update memory as well
                        return
                    else:
                        raise Exception(f"Struct '{self.symbol_table[struct_var_name]['type']}' does not have field '{field_name}'")
                else:
                    raise Exception(f"'{struct_var_name}' is not a struct variable")
            else:
                raise Exception(f"Struct variable '{struct_var_name}' not declared")

        if var_name in self.symbol_table:
            declared_type = self.symbol_table[var_name]["type"]
            typed_value = self.cast_value_to_type(new_value, declared_type)  # Type casting on assignment
            self.symbol_table[var_name]["value"] = typed_value  # Update symbol table
            memory_address = self.symbol_table[var_name]["address"]
            self.memory[memory_address] = typed_value  # Update memory
        else:
            raise Exception(f"Variable '{var_name}' not declared")

    # def execute_function_call(self, node):
    #     func_name = node.func_name
    #     args = [self.evaluate_expression(arg) for arg in node.args]
    #
    #     # print(f"fnc: {func_name}({args})")
    #
    #     if func_name not in self.function_table:
    #         # if func_name == 'print': # Special case for print
    #         #     self.resolving_context = "pretty"
    #         #     values = [self.evaluate_expression(expr) for expr in node.args]
    #         #     # print(values)
    #         #     print(*values)
    #         #     # print(*(args)) # Python print function
    #         #     return None
    #         builtin = self.stdlib[func_name]
    #         if builtin:
    #             x = builtin(args)
    #             if self.resolving_context == "expr":
    #                 self.resolving_context = "normal"
    #                 return self.evaluate_expression(x)
    #             return x
    #         raise Exception(f"Function '{func_name}' not defined")
    #
    #     func_def = self.function_table[func_name]
    #     if len(args) != len(func_def.params):
    #         raise Exception(f"Incorrect number of arguments for function '{func_name}'. Expected {len(func_def.params)}, got {len(args)}")
    #
    #     # Prepare function scope (for variables declared inside function) - for now, simple approach
    #     prev_symbol_table = self.symbol_table.copy() # Simple scope management - not perfect for nested scopes
    #
    #     # Bind arguments to parameters in function scope
    #     for i, param in enumerate(func_def.params):
    #         param_name, param_type = param
    #         typed_arg_value = self.cast_value_to_type(args[i], param_type) # Type check/cast arguments against parameters
    #         self.symbol_table[param_name] = {"type": param_type, "value": typed_arg_value, "address": self.next_memory_address}
    #         self.allocate_memory(param_type)
    #
    #     # Execute function body
    #     return_value = None
    #     # try:
    #     for statement in func_def.body.statements:
    #         result = self.execute_statement(statement) # Execute statement and capture return value
    #         if isinstance(result, ReturnNode): # If a 'return' statement is executed
    #             return_value = self.evaluate_expression(result.return_expr) # Evaluate return expression
    #             break # Exit function execution on return
    #     # except ReturnException as e: # In case we want to use exceptions for return (cleaner return flow). Not used in current example.
    #     # return_value = e.value
    #
    #     # Restore previous scope - simple scope management
    #     self.symbol_table = prev_symbol_table
    #     return self.cast_value_to_type(return_value, func_def.return_type) if return_value is not None else None # Cast return value to expected type

    def execute_if_statement(self, node):
        condition_value = self.evaluate_expression(node.condition)
        if condition_value:
            self.execute_statement(node.then_block)
        else:
            for elif_condition, elif_block in node.elif_blocks:
                if self.evaluate_expression(elif_condition):
                    self.execute_statement(elif_block)
                    return # Exit after executing elif
            if node.else_block:
                self.execute_statement(node.else_block)

    def execute_while_loop(self, node):
        while self.evaluate_expression(node.condition):
            self.execute_statement(node.loop_block)

    def execute_for_loop(self, node):
        # self.symbol_table["i"] = {"type": "int32", "value": 0, "address": self.next_memory_address}
        # self.allocate_memory("int32")
        self.execute_statement(node.init_stmt) # Initialization statement
        # print("st", self.symbol_table)
        while self.evaluate_expression(node.condition_expr): # Condition
            self.execute_statement(node.loop_block) # Loop body
            self.execute_statement(node.increment_stmt) # Increment statement
        # self.free_memory(self.symbol_table["i"]["address"])

    def execute_print_statement(self, node):
        values = [self.evaluate_expression(expr) for expr in node.expressions]
        print(*values)

    def execute_spawn_task(self, node): # Simple concurrency simulation - just prints a message.
        # task_name = node.task_name
        # print(f"Spawning task: {task_name}...")
        # In a real implementation, would create a new thread/process and execute task body.
        self.execute_statement(node.body) # For simulation, execute in current thread directly.

    def evaluate_expression(self, node):
        if isinstance(node, IntLiteralNode):
            return node.value
        elif isinstance(node, FloatLiteralNode):
            return node.value
        elif isinstance(node, CharLiteralNode):
            return node.value
        elif isinstance(node, StringLiteralNode):
            return node.value
        elif isinstance(node, NullLiteralNode):
            return None
        elif isinstance(node, ArrayLiteralNode):
            return [self.evaluate_expression(i) for i in node.elements]
        elif isinstance(node, IdentifierNode):
            # print("ident", node)
            var_name = node.name
            if var_name in self.symbol_table:
                x = self.symbol_table[var_name]
                # print(self.resolving_context, type(x["value"]))
                if isinstance(x["value"], dict) and self.resolving_context == "pretty":
                    self.resolving_context = "normal"
                    x = f"{x.get('data_type') or '*unknown*'} {{ {", ".join([f'{k}: {v if v is not None else 'null'}' for k, v in x['value'].items()])} }}"
                    # print("pretty", x)
                    return x
                return x["value"]
            elif var_name in self.enum_definitions: # Check if identifier is an enum
                return var_name # Return enum name itself for now
            else:
                raise Exception(f"Variable '{var_name}' not declared")
        elif isinstance(node, BinaryOpNode):
            left_value = self.evaluate_expression(node.left_expr)
            right_value = self.evaluate_expression(node.right_expr)
            op_type = node.op

            if op_type == TokenType.PLUS: return left_value + right_value
            elif op_type == TokenType.MINUS: return left_value - right_value
            elif op_type == TokenType.MULTIPLY: return left_value * right_value
            elif op_type == TokenType.DIVIDE:
                if right_value == 0: raise Exception("Division by zero")
                return left_value / right_value
            elif op_type == TokenType.MODULO:
                if right_value == 0: raise Exception("Modulo by zero")
                return left_value % right_value
            elif op_type == TokenType.EQUAL: return left_value == right_value
            elif op_type == TokenType.NOT_EQUAL: return left_value != right_value
            elif op_type == TokenType.GREATER_THAN: return left_value > right_value
            elif op_type == TokenType.LESS_THAN: return left_value < right_value
            elif op_type == TokenType.GREATER_EQUAL: return left_value >= right_value
            elif op_type == TokenType.LESS_EQUAL: return left_value <= right_value
            elif op_type == TokenType.AND: return left_value & right_value # Bitwise AND
            elif op_type == TokenType.OR: return left_value | right_value  # Bitwise OR
            elif op_type == TokenType.XOR: return left_value ^ right_value # Bitwise XOR
            elif op_type == TokenType.LSHIFT: return left_value << right_value # Left Shift
            elif op_type == TokenType.RSHIFT: return left_value >> right_value # Right Shift

        elif isinstance(node, UnaryOpNode):
            value = self.evaluate_expression(node.expr)
            op_type = node.op
            if op_type == TokenType.MINUS: return -value
            elif op_type == TokenType.BIT_NOT: return ~value # Bitwise NOT
            elif op_type == TokenType.POINTER_DEREF: # *ptr
                if isinstance(value, int): # Address should be an integer address
                    if value in self.memory:
                        return self.memory[value] # Dereference memory address
                    else:
                        raise Exception(f"Invalid memory access at address {value}")
                else:
                    raise Exception("Pointer dereference expects a memory address (integer)")
            elif op_type == TokenType.POINTER_REF: # &var
                if isinstance(node.expr, IdentifierNode):
                    var_name = node.expr.name
                    # print("pointer")
                    if var_name in self.symbol_table:
                        # print(var_name, self.symbol_table[var_name])
                        return self.symbol_table[var_name]["address"] # Return memory address of variable
                    else:
                        raise Exception(f"Variable '{var_name}' not declared")
                else:
                    raise Exception("Pointer reference '&' can only be applied to variables")

        elif isinstance(node, FunctionCallNode):
            return self.execute_function_call(node)
        elif isinstance(node, TypeCastNode):
            expression_value = self.evaluate_expression(node.expression)
            return self.cast_value_to_type(expression_value, node.target_type)
        elif isinstance(node, StructFieldAccessNode):
            struct_var_name = str(node.struct_var_name)
            field_name = node.field_name
            if struct_var_name in self.symbol_table:
                if (sv := self.symbol_table[struct_var_name])["type"] in self.struct_definitions:
                    struct_instance = self.symbol_table[struct_var_name]["value"]
                    if field_name in struct_instance:
                        # print(struct_instance)
                        try:
                            return struct_instance[field_name]
                        except Exception as e:
                            print(self.symbol_table[struct_var_name], struct_instance, e)
                    else:
                        raise Exception(f"Struct '{self.symbol_table[struct_var_name]['type']}' does not have field '{field_name}'")
                else:
                    if sv["type"] == "array":
                        return sv["value"][int(field_name)]
                    if sv["type"] == "any":
                        try:
                            return sv["value"][field_name]
                        except KeyError as e:
                            raise KeyError(f"Key not found: {e}")
                    raise Exception(f"'{struct_var_name}' is not a struct variable")
            else:
                if enum_item := self.enum_definitions.get(struct_var_name):
                    return next(filter(lambda y: y == field_name, enum_item.members))
                    # return None
                raise Exception(f"Struct variable '{struct_var_name}' not declared")
        elif isinstance(node, ArrayIndexNode):
            array_name = str(node.array_name)
            index = self.evaluate_expression(node.index_expr)
            if array_name in self.symbol_table:
                array_value = self.symbol_table[array_name]["value"]
                try:
                    index = int(index)
                    if isinstance(array_value, list) and 0 <= index < len(array_value):
                        return array_value[index]
                    else:
                        raise Exception(f"Array '{array_name}' index out of range")
                except ValueError:
                    raise Exception("Array index expression must be an integer literal")
            else:
                raise Exception(f"Array '{array_name}' not declared")
        elif isinstance(node, OkResultNode):
            return {"type": "Ok", "value": self.evaluate_expression(node.value_expr)}
        elif isinstance(node, ErrResultNode):
            error_value = self.evaluate_expression(node.error_expr) # Could be enum member etc.
            return {"type": "Err", "error": error_value}
        elif isinstance(node, EnumMemberNode): # Referencing enum member value - for now return string name itself.
            return node.member_name # Could be improved to store enum values if needed
        elif isinstance(node, MethodCallNode):
            instance_type = self._get_expression_type(node.instance_expr)
            instance_value = self.evaluate_expression(node.instance_expr)

            method_key = f"{instance_type}::{node.method_name}"
            if method_key not in self.function_table:
                # print(self.function_table)
                raise Exception(f"Method '{node.method_name}' not found for type '{instance_type}'")

            method_def = self.function_table[method_key]
            args = [self.evaluate_expression(arg) for arg in node.args]

            self_context = {"type": instance_type, "value": instance_value, "address": -1} # address is tricky here
            return self._execute_callable(method_def, args, self_instance=self_context)


        return None # Default return if not handled.

    def cast_value_to_type(self, value, target_type): # Simple type casting. Needs more robust logic.
        try:
            if target_type in ["int8", "int16", "int32", "int64"]:
                return int(value)
            elif target_type in ["uint8", "uint16", "uint32", "uint64"]:
                return int(value) # Unsigned is treated same as signed for now in casting, needs proper uint handling
            elif target_type in ["float32", "float64"]:
                return float(value)
            elif target_type == "char":
                return str(value)[0] if str(value) else '\0' # Get first char or null char if empty
            elif target_type in self.struct_definitions: # Casting to struct type? Not directly supported in Gravox spec example, may need to handle struct instantiation instead.
                return value # Return original value if type is struct (no direct cast, might need constructor)
            elif target_type in self.enum_definitions:
                return value
            elif target_type == "Result": # Result type is more of a return type specifier, not really a type to cast to in value context.
                raise DeprecationWarning("Use try/catch instead.")
                # return value # Return original value if type is Result
            elif target_type == "string":
                return str(value)
            elif target_type == "any":
                return value
            elif target_type == "array":
                return list(value)
            else:
                raise Exception(f"Cannot cast value of type '{type(value)}' to type '{target_type}'")
        except ValueError:
            raise Exception(f"Cannot cast value '{value}' to type '{target_type}'")
        except TypeError:
            raise Exception(f"Cannot cast value '{value}' to type '{target_type}'")

    def get_default_value_for_type(self, data_type):
        if data_type in ["int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"]:
            return 0
        elif data_type in ["float32", "float64"]:
            return 0.0
        elif data_type == "char":
            return '\0'
        elif data_type in self.struct_definitions: # Default struct instance? For now, initialize all fields to default of their types in struct_def
            struct_def = self.struct_definitions[data_type]
            struct_instance = {}
            print("sd", struct_def)
            for field_name, field_type in struct_def.fields:
                struct_instance[field_name] = self.get_default_value_for_type(field_type) # Recursive default for nested structs?
            return struct_instance
        return None