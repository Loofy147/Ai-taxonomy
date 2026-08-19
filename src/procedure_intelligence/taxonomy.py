"""Taxonomy and classification engine for procedures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
import inspect


class ExecutionNature(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    PROBABILISTIC = "PROBABILISTIC"


class Statefulness(str, Enum):
    STATELESS = "STATELESS"
    STATEFUL = "STATEFUL"


class SideEffectLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATIVE_REVERSIBLE = "MUTATIVE_REVERSIBLE"
    NON_REVERSIBLE = "NON_REVERSIBLE"


class MetaLevel(str, Enum):
    ATOMIC = "ATOMIC"
    COMPOSITE = "COMPOSITE"
    META_OPERANT = "META_OPERANT"  # Vau-style operants manipulating sub-procedures


@dataclass
class ProcedureDimension:
    execution_nature: ExecutionNature = ExecutionNature.DETERMINISTIC
    statefulness: Statefulness = Statefulness.STATELESS
    side_effect: SideEffectLevel = SideEffectLevel.READ_ONLY
    meta_level: MetaLevel = MetaLevel.ATOMIC


@dataclass
class ProcedureMetadata:
    name: str
    description: str
    dimensions: ProcedureDimension
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


def _generate_default_input_schema(func: Callable) -> Dict[str, Any]:
    """Auto-generates JSON schema from function signature if input_schema is omitted."""
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return {"type": "object", "properties": {}, "additionalProperties": False}

    properties = {}
    required = []
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        param_type = "string"
        if param.annotation == int:
            param_type = "integer"
        elif param.annotation == float:
            param_type = "number"
        elif param.annotation == bool:
            param_type = "boolean"
        elif param.annotation in (dict, Dict):
            param_type = "object"
        elif param.annotation in (list, List):
            param_type = "array"

        properties[param_name] = {"type": param_type}
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    schema = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _generate_default_output_schema(func: Callable) -> Dict[str, Any]:
    """Auto-generates JSON output schema from return type annotation if omitted."""
    try:
        sig = inspect.signature(func)
        ret = sig.return_annotation
        if ret == str:
            return {"type": "string"}
        elif ret == int:
            return {"type": "integer"}
        elif ret == float:
            return {"type": "number"}
        elif ret == bool:
            return {"type": "boolean"}
        elif ret in (dict, Dict):
            return {"type": "object", "properties": {}}
        elif ret in (list, List):
            return {"type": "array"}
    except (ValueError, TypeError):
        pass
    return {}


def procedure(
    name: Optional[str] = None,
    description: Optional[str] = None,
    execution_nature: ExecutionNature = ExecutionNature.DETERMINISTIC,
    statefulness: Statefulness = Statefulness.STATELESS,
    side_effect: SideEffectLevel = SideEffectLevel.READ_ONLY,
    meta_level: MetaLevel = MetaLevel.ATOMIC,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    preconditions: Optional[List[str]] = None,
    postconditions: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> Callable:
    """Decorator to attach Procedure Intelligence taxonomy metadata to a callable."""

    def decorator(func: Callable) -> Callable:
        proc_name = name or func.__name__
        proc_desc = description or (func.__doc__.strip() if func.__doc__ else proc_name)

        dimensions = ProcedureDimension(
            execution_nature=execution_nature,
            statefulness=statefulness,
            side_effect=side_effect,
            meta_level=meta_level,
        )

        in_schema = input_schema or _generate_default_input_schema(func)
        out_schema = output_schema if output_schema is not None else _generate_default_output_schema(func)

        meta = ProcedureMetadata(
            name=proc_name,
            description=proc_desc,
            dimensions=dimensions,
            input_schema=in_schema,
            output_schema=out_schema,
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            tags=tags or [],
        )

        setattr(func, "__procedure_metadata__", meta)
        return func

    return decorator


def get_procedure_metadata(func: Callable) -> Optional[ProcedureMetadata]:
    """Retrieves procedure metadata attached to a callable if present."""
    return getattr(func, "__procedure_metadata__", None)
