"""
Data layour structures with Pydantic
defining the fields, data params, return shapes for all
function calling pipelines.
"""


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


class PromptInput(BaseModel):
    """single query prompt from the test suite"""
    prompt: str
