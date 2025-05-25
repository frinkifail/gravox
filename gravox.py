from interpreter import Interpreter
from lexing import tokenize
from parser import Parser

# --- 2. Parser (Simplified - Expression parsing and basic statements) ---
# [MOVED]

# --- 3. Interpreter ---
# [MOVED]

# --- 4. Example Execution ---
def run_gravox_code(code, debug = False):
    try:
        tokens = tokenize(code)
        if debug:
            print("\nTokens:")
            for token in tokens:
                print(token)

        parser = Parser(tokens)
        ast_tree = parser.parse_program()
        if debug:
            print("\nAST Tree:")
            print(ast_tree)

        interpreter = Interpreter()
        interpreter.interpret(ast_tree)
        # if debug:
        #     print("\nInterpretation Result:", result)
        # return result

    except Exception as e:
        if debug:
            raise e
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    from sys import argv
    with open(argv[1]) as f:
        run_gravox_code(f.read(), "-d" in argv)
