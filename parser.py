from ast import MethodCallNode, StructFieldAccessNode, StringLiteralNode, IdentifierNode, CharLiteralNode, \
    FloatLiteralNode, IntLiteralNode, NullLiteralNode, UnaryOpNode, BinaryOpNode, SpawnTaskNode, VarAssignNode, \
    EnumDefNode, StructDefNode, TypeCastNode, ForLoopNode, WhileLoopNode, IfStatementNode, ReturnNode, FunctionCallNode, \
    FunctionDefNode, FreeMemoryNode, AllocMemoryNode, BlockNode, ProgramNode, ImportNode, TryNode, \
    ArrayLiteralNode, ArrayIndexNode
from lexing import TokenType, DATA_TYPES


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0

    def peek(self, offset=0):
        index = self.current_token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return None

    def consume(self, token_type):
        token = self.current_token()
        if token.type == token_type:
            self.current_token_index += 1
            return token
        raise Exception(f"Expected token type {token_type}, but got {token.type} at {token.line}:{token.column}")

    def consume_data_type(self):
        token = self.current_token()
        if token.type in [
            *DATA_TYPES.values(),
            TokenType.IDENTIFIER # Also allow generic IDENTIFIER for custom types
        ]:
            self.consume(token.type)
            return token
        raise Exception(f"Expected data type, but got {token.type} at {token.line}:{token.column}")

    def current_token(self):
        if self.current_token_index < len(self.tokens):
            return self.tokens[self.current_token_index]
        return self.tokens[-1] # EOF token

    def parse_program(self):
        statements = []
        while self.current_token().type != TokenType.EOF:
            statements.append(self.parse_statement())
        return ProgramNode(statements)

    def parse_block(self):
        self.consume(TokenType.LBRACE)
        statements = []
        while self.current_token().type != TokenType.RBRACE:
            statements.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        return BlockNode(statements)

    def parse_import(self):
        self.consume(TokenType.IMPORT)
        module_name = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        return ImportNode(module_name.value)

    def parse_statement(self):
        token = self.current_token()

        if token.type == TokenType.ALLOC:
            return self.parse_variable_declaration()
        elif token.type == TokenType.FREE:
            return self.parse_memory_free()
        elif token.type == TokenType.DEF:
            return self.parse_function_definition()
        elif token.type == TokenType.STRUCT:
            return self.parse_struct_definition()
        elif token.type == TokenType.ENUM:
            return self.parse_enum_definition()
        elif token.type == TokenType.IF:
            return self.parse_if_statement()
        elif token.type == TokenType.WHILE:
            return self.parse_while_loop()
        elif token.type == TokenType.FOR:
            return self.parse_for_loop()
        elif token.type == TokenType.RETURN:
            return self.parse_return_statement()
        elif token.type == TokenType.IDENTIFIER and self.peek(1) and self.peek(1).type == TokenType.ASSIGN:
            return self.parse_variable_assignment()
        elif token.type == TokenType.IDENTIFIER and self.peek(1) and self.peek(1).type == TokenType.LPAREN:
            return self.parse_function_call_statement()  # Function call as a statement
        elif token.type == TokenType.IDENTIFIER and self.peek(1) and self.peek(1).type == TokenType.DOT:
            return self.parse_struct_field_assignment_or_access()  # For struct field assignment like vec.x = 10;
        elif token.type == TokenType.SPAWN:
            return self.parse_spawn_task()
        elif token.type == TokenType.IMPORT:
            return self.parse_import()
        elif token.type == TokenType.TRY:
            return self.parse_try_statement()

        # Default to an expression statement (like a function call, method call, or assignment)
        expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return expr

    def parse_try_statement(self):
        self.consume(TokenType.TRY)
        try_block = self.parse_block()
        catch_block = None
        if self.current_token().type == TokenType.CATCH:
            self.consume(TokenType.CATCH)
            catch_block = self.parse_block()
        return TryNode(try_block, catch_block)

    def parse_variable_declaration(self):
        self.consume(TokenType.ALLOC)
        var_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.COLON)
        data_type_token = self.consume_data_type()
        value_expr = None
        if self.current_token().type == TokenType.ASSIGN:
            self.consume(TokenType.ASSIGN)
            value_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return AllocMemoryNode(var_name_token.value, data_type_token.value, value_expr)

    def parse_memory_free(self):
        self.consume(TokenType.FREE)
        var_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        return FreeMemoryNode(var_name_token.value)

    def parse_variable_assignment(self):
        var_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.ASSIGN)
        value_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return VarAssignNode(var_name_token.value, value_expr)

    def parse_function_definition(self):
        self.consume(TokenType.DEF)
        func_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LPAREN)
        params = []
        if self.current_token().type != TokenType.RPAREN:
            param_name_token = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            param_type_token = self.consume_data_type()
            params.append((param_name_token.value, param_type_token.value))
            while self.current_token().type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                param_name_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                param_type_token = self.consume_data_type()
                params.append((param_name_token.value, param_type_token.value))
        self.consume(TokenType.RPAREN)
        self.consume(TokenType.ARROW)
        return_type_token = self.consume_data_type()
        body = self.parse_block()
        return FunctionDefNode(func_name_token.value, params, return_type_token.value, body)

    def parse_function_call_statement(self):  # Function call used as statement (e.g., function());
        func_call = self.parse_postfix_expression()  # This will handle the function call
        self.consume(TokenType.SEMICOLON)
        return func_call

    def parse_return_statement(self):
        self.consume(TokenType.RETURN)
        return_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return ReturnNode(return_expr)

    def parse_if_statement(self):
        self.consume(TokenType.IF)
        self.consume(TokenType.LPAREN)
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN)
        then_block = self.parse_block()
        elif_blocks = []
        else_block = None
        while self.current_token().type == TokenType.ELIF:
            self.consume(TokenType.ELIF)
            self.consume(TokenType.LPAREN)
            elif_condition = self.parse_expression()
            self.consume(TokenType.RPAREN)
            elif_block = self.parse_block()
            elif_blocks.append((elif_condition, elif_block))
        if self.current_token().type == TokenType.ELSE:
            self.consume(TokenType.ELSE)
            else_block = self.parse_block()
        return IfStatementNode(condition, then_block, else_block, elif_blocks)

    def parse_while_loop(self):
        self.consume(TokenType.WHILE)
        self.consume(TokenType.LPAREN)
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN)
        loop_block = self.parse_block()
        return WhileLoopNode(condition, loop_block)

    def parse_for_loop(self):
        self.consume(TokenType.FOR)
        self.consume(TokenType.LPAREN)
        init_stmt = self.parse_statement()
        condition_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        increment_stmt = self.parse_statement()
        self.consume(TokenType.RPAREN)
        loop_block = self.parse_block()
        return ForLoopNode(init_stmt, condition_expr, increment_stmt, loop_block)

    def parse_type_cast(self):
        self.consume(TokenType.LESS_THAN)
        target_type_token = self.consume_data_type()
        self.consume(TokenType.GREATER_THAN)
        expression = self.parse_atom()
        return TypeCastNode(target_type_token.value, expression)

    def parse_struct_definition(self):
        self.consume(TokenType.STRUCT)
        struct_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LBRACE)
        fields = []
        functions = []
        while self.current_token().type != TokenType.RBRACE:
            if self.peek().type == TokenType.DEF:
                functions.append(self.parse_function_definition())
            else:
                field_name_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                field_type_token = self.consume_data_type()
                self.consume(TokenType.SEMICOLON)
                fields.append((field_name_token.value, field_type_token.value))
        self.consume(TokenType.RBRACE)
        return StructDefNode(struct_name_token.value, fields, functions)

    def parse_enum_definition(self):
        self.consume(TokenType.ENUM)
        enum_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LBRACE)
        members = []
        while self.current_token().type != TokenType.RBRACE:
            member_name_token = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COMMA)
            members.append(member_name_token.value)
        self.consume(TokenType.RBRACE)
        return EnumDefNode(enum_name_token.value, members)

    # def parse_struct_field_assignment_or_access(self):
    #     struct_var_name_token = self.consume(TokenType.IDENTIFIER)
    #     self.consume(TokenType.DOT)
    #     field_name_token = self.consume(TokenType.IDENTIFIER)
    #     if self.current_token().type == TokenType.ASSIGN:
    #         self.consume(TokenType.ASSIGN)
    #         value_expr = self.parse_expression()
    #         self.consume(TokenType.SEMICOLON)
    #         return VarAssignNode(f"{struct_var_name_token.value}.{field_name_token.value}", value_expr)  # Using dot notation in name for struct fields
    #     else:
    #         return StructFieldAccessNode(struct_var_name_token.value, field_name_token.value)

    def parse_spawn_task(self):
        self.consume(TokenType.SPAWN)
        self.consume(TokenType.IDENTIFIER) # consume 'task' keyword
        task_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LPAREN)
        params = []
        if self.current_token().type != TokenType.RPAREN:
            param_name_token = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            param_type_token = self.consume(TokenType.IDENTIFIER)
            params.append((param_name_token.value, param_type_token.value))
            while self.current_token().type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                param_name_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                param_type_token = self.consume(TokenType.IDENTIFIER)
                params.append((param_name_token.value, param_type_token.value))
        self.consume(TokenType.RPAREN)
        body = self.parse_block()
        return SpawnTaskNode(task_name_token.value, params, body)

    # --- Expression Parsing (Precedence Climbing) ---
    def parse_expression(self):
        return self.parse_bitwise_or()

    def parse_bitwise_or(self):
        left_expr = self.parse_bitwise_xor()
        while self.current_token().type == TokenType.OR:
            op_token = self.consume(TokenType.OR)
            right_expr = self.parse_bitwise_xor()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_bitwise_xor(self):
        left_expr = self.parse_bitwise_and()
        while self.current_token().type == TokenType.XOR:
            op_token = self.consume(TokenType.XOR)
            right_expr = self.parse_bitwise_and()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_bitwise_and(self):
        left_expr = self.parse_equality()
        while self.current_token().type == TokenType.AND:
            op_token = self.consume(TokenType.AND)
            right_expr = self.parse_equality()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_equality(self):
        left_expr = self.parse_comparison()
        while self.current_token().type in (TokenType.EQUAL, TokenType.NOT_EQUAL):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_comparison()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_comparison(self):
        left_expr = self.parse_shift()
        while self.current_token().type in (TokenType.GREATER_THAN, TokenType.LESS_THAN, TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_shift()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_shift(self):
        left_expr = self.parse_term()
        while self.current_token().type in (TokenType.LSHIFT, TokenType.RSHIFT):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_term()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_term(self):
        left_expr = self.parse_factor()
        while self.current_token().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_factor()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_factor(self):
        left_expr = self.parse_unary()
        while self.current_token().type in (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_unary()
            left_expr = BinaryOpNode(op_token.type, left_expr, right_expr)
        return left_expr

    def parse_unary(self):
        if self.current_token().type in (TokenType.MINUS, TokenType.BIT_NOT, TokenType.POINTER_DEREF, TokenType.POINTER_REF):
            op_token = self.consume(self.current_token().type)
            expr = self.parse_unary() # Apply unary to the result of another unary
            return UnaryOpNode(op_token.type, expr)
        return self.parse_postfix_expression()

    def parse_struct_field_assignment_or_access(self):
        # Use postfix expression parsing to handle method calls and field access
        expr = self.parse_postfix_expression()

        # Check if this is an assignment (for field assignments like struct.field = value)
        if isinstance(expr, StructFieldAccessNode) and self.current_token().type == TokenType.ASSIGN:
            self.consume(TokenType.ASSIGN)
            value_expr = self.parse_expression()
            self.consume(TokenType.SEMICOLON)
            return VarAssignNode(f"{expr.struct_var_name}.{expr.field_name}", value_expr)
        else:
            # This is either a method call or field access - consume semicolon and return
            self.consume(TokenType.SEMICOLON)
            return expr

    def parse_postfix_expression(self):
        # First, parse the primary part of the expression (the "atom").
        node = self.parse_atom()

        # Then, loop to parse any postfix operators like (), [], or .
        while True:
            if self.current_token().type == TokenType.LPAREN:
                # Function call, e.g. ( ... )
                self.consume(TokenType.LPAREN)
                args = []
                if self.current_token().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token().type == TokenType.COMMA:
                        self.consume(TokenType.COMMA)
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN)
                # 'node' becomes the callee of the function call
                node = FunctionCallNode(node, args)
            elif self.current_token().type == TokenType.LBRACKET:
                # Array index, e.g. [ ... ]
                self.consume(TokenType.LBRACKET)
                index_expr = self.parse_expression()
                self.consume(TokenType.RBRACKET)
                node = ArrayIndexNode(node, index_expr)
            elif self.current_token().type == TokenType.DOT:
                # Member access for structs, e.g., .member or .method()
                self.consume(TokenType.DOT)
                if self.peek().type == TokenType.INT_LITERAL:
                    member_name_token = self.consume(TokenType.INT_LITERAL)
                else:
                    member_name_token = self.consume(TokenType.IDENTIFIER)
                if self.current_token().type == TokenType.LPAREN:
                    # Method call
                    self.consume(TokenType.LPAREN)
                    args = []
                    if self.current_token().type != TokenType.RPAREN:
                        args.append(self.parse_expression())
                        while self.current_token().type == TokenType.COMMA:
                            self.consume(TokenType.COMMA)
                            args.append(self.parse_expression())
                    self.consume(TokenType.RPAREN)
                    node = MethodCallNode(node, member_name_token.value, args)
                else:
                    # Field access
                    if isinstance(node, IdentifierNode):
                        # Simple case: structVar.field
                        node = StructFieldAccessNode(node.name, member_name_token.value)
                    else:
                        # Complex case: expression.field
                        node = StructFieldAccessNode(node, member_name_token.value)
            else:
                break # No more postfix operators
        return node

    def parse_atom(self):
        token = self.current_token()

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr
        elif token.type == TokenType.INT_LITERAL:
            return IntLiteralNode(self.consume(TokenType.INT_LITERAL).value)
        elif token.type == TokenType.FLOAT_LITERAL:
            return FloatLiteralNode(self.consume(TokenType.FLOAT_LITERAL).value)
        elif token.type == TokenType.CHAR_LITERAL:
            return CharLiteralNode(self.consume(TokenType.CHAR_LITERAL).value)
        elif token.type == TokenType.STRING_LITERAL:
            return StringLiteralNode(self.consume(TokenType.STRING_LITERAL).value)
        elif token.type == TokenType.NULL:
            self.consume(TokenType.NULL)
            return NullLiteralNode()
        elif token.type == TokenType.IDENTIFIER:
            return IdentifierNode(self.consume(TokenType.IDENTIFIER).value)
        elif token.type == TokenType.LESS_THAN and self.peek(1).type in DATA_TYPES.values():
            return self.parse_type_cast()
        elif token.type == TokenType.LBRACKET:
            return self.parse_array_literal()
        else:
            raise Exception(f"Unexpected token {token.type} in expression at {token.line}:{token.column}")

    def parse_array_literal(self):
        self.consume(TokenType.LBRACKET)
        elements = []
        if self.current_token().type != TokenType.RBRACKET:
            elements.append(self.parse_expression())
            while self.current_token().type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                elements.append(self.parse_expression())
        self.consume(TokenType.RBRACKET)
        return ArrayLiteralNode(elements)