import builtins
import importlib
import textwrap
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar

from invoke import Context, task
from pyclibrary.c_parser import Struct  # type: ignore[import-untyped]
from pyclibrary.c_parser import Type as CType

from tasks.dev import format_and_lint


def indent(line: str, *, n: int = 1) -> str:
    return textwrap.indent(line, "    " * n)


T = TypeVar("T")


def only_public(items: dict[str, T]) -> Iterator[tuple[str, T]]:
    for name, value in items.items():
        if name.startswith("_"):
            continue
        yield name, value


def value_annotations(values: dict[str, CType]) -> Iterator[str]:
    for name, value in only_public(values):
        if value is None:
            yield f"{name}: None"
        elif isinstance(value, (str, float, int)):
            yield f"{name}: {type(value).__name__}"
        else:
            error = f"unknown value type: {name}={value}"
            raise ValueError(error)


def function_annotations(funcs: dict[str, CType]) -> Iterator[str]:
    def param_annotations(params: CType) -> Iterator[str]:
        for declarator in params:
            if (name := declarator[0]) is None:
                continue

            safe_name = f"{name}_" if name in ["in", *dir(builtins)] else name
            yield f"{safe_name}: Any = None"

    def return_type_annotation(return_ctype: CType) -> str:
        return_type = return_ctype.type_spec
        if "*" in return_ctype.declarators:
            if return_type == "char":
                return "bytes"
            return "int"

        return {"void": "None", "int": "int"}.get(return_type, "None")

    for name, func in only_public(funcs):
        ret = return_type_annotation(func.type_spec)
        params = param_annotations(func.declarators[0])
        yield "@staticmethod"
        yield f"def {name}({','.join(params)}) -> CallResult[{ret}]: ..."


def struct_annotations(structs: dict[str, Struct]) -> Iterator[str]:
    for name, struct in only_public(structs):
        yield f"class type_{name}(Protocol):"
        if not struct.members:
            yield indent("pass")
        for member in struct.members:
            if member[0] == "def":
                continue
            yield indent(f"{member[0]}: {type_annotation(member[1])}")
        yield f"{name}: type_{name}"


def type_annotation(typ: CType) -> str:
    if typ.type_spec == "char":
        return "bytes"
    if typ.type_spec == "int":
        return "int"
    return "Any"


def type_annotations(types: dict[str, CType]) -> Iterator[str]:
    for name, typ in only_public(types):
        if len(typ.declarators) == 0:
            yield f"{name}: None"


def enum_annotations(enums: dict[str, dict[str, int]]) -> Iterator[str]:
    for name, enum in only_public(enums):
        if len(enum) > 0:
            yield f"class type_{name}(IntEnum):"
            for field, value in enum.items():
                yield indent(f"{field} = {value}")


@task
def gen(ctx: Context, clib: str) -> None:
    module_name, var_name = clib.split(":")
    module = importlib.import_module(module_name)
    lib = getattr(module, var_name)
    definitions = lib._headers_.defs

    stub_path = Path(module.__file__ or "stub.py").with_suffix(".pyi")
    with stub_path.open(mode="w") as stub:
        stub.write(
            textwrap.dedent(
                """
                from enum import IntEnum
                from typing import Any, Protocol, Generic, TypeVar
                _T = TypeVar("_T")
                class Pointer(Protocol[_T]):
                    contents: _T
                _R = TypeVar("_R")
                class CallResult(Generic[_R]):
                    rval: _R
                    def __getitem__(self, item: str) -> Any: ...
                """
            )
        )
        stub.write(
            "\n".join(
                (
                    f"class {var_name}:",
                    *map(indent, value_annotations(definitions["values"])),
                    *map(indent, type_annotations(definitions["types"])),
                    *map(indent, enum_annotations(definitions["enums"])),
                    *map(indent, struct_annotations(definitions["structs"])),
                    *map(indent, function_annotations(definitions["functions"])),
                )
            )
        )

    format_and_lint(ctx, single_file=str(stub_path))


@task
def bindings(ctx: Context) -> None:
    gen(ctx, "sigrok.bindings:lib")
