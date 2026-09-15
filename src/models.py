""""""


from typing import Literal
from pydantic import BaseModel


ParameterType = Literal["number", "string", "boolean"]


class ParameterInfo(BaseModel):
    """defining structure of an individual function param"""
    type: ParameterType


class ReturnInfo(BaseModel):
    """definin the return type structure of a function"""
    type: ParameterType


class FunctionDefinition(BaseModel):
    """schema definition for a callable function"""
    name: str
    description: str
    parameters: dict[str, ParameterInfo]
    returns: ReturnInfo


class PrompInput(BaseModel):
    """single query prompt from the test suite"""
    prompt: str
