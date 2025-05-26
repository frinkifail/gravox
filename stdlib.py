import json
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from gravox import Interpreter

class Stdlib:
    def __init__(self, interpreter: "Interpreter"):
        self.interpreter = interpreter

    @staticmethod
    def print(args: list[Any]): # TODO: pretty
        print(*args)

    @staticmethod
    def debug_print(args: list[Any]):
        print(args)

    @staticmethod
    def input(args: tuple[str]):
        return input(args[0])

    def gravox_heapusage(self, _):
        return self.interpreter.next_memory_address

    def gravox_heapsize(self, _):
        return self.interpreter.heap_size

    @staticmethod
    def _array_push(args: list[Any]):
        array = args[0]
        value = args[1]
        array.append(value)
        return array

    @staticmethod
    def _file_exec(args: tuple[str, str, str | None]): # (file, mode, arg)
        data = None
        with open(args[0], args[1]) as f:
            match args[1]:
                case "w+":
                    f.write(args[2])
                    data = True
                case "r":
                    data = f.read()
                case _:
                    raise Exception("No such mode for file execution.")
        return data

    @staticmethod
    def _json_exec(args: tuple[str, dict | str | None]): # (op, contents)
        match args[0]:
            case "dump":
                return json.dumps(args[1])
            case "load":
                return json.loads(args[1])
            case _:
                raise Exception("Unknown operation")

    def __getitem__(self, item) -> Callable | None:
        try:
            clsitem = self.__getattribute__(item)
        except AttributeError:
            clsitem = None
        if clsitem and callable(clsitem):
            return clsitem
        else:
            return None