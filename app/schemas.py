# -*- coding: utf-8 -*-
"""Pydantic schemas for the Cars CRUD app (unit-test target)."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# A text field that is stripped of surrounding whitespace and cannot be blank.
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CarInput(BaseModel):
    make: NonBlank
    model: NonBlank
    year: int = Field(ge=1886, description="Model year; must be a plausible automobile year.")
    color: NonBlank


class Car(CarInput):
    id: int
