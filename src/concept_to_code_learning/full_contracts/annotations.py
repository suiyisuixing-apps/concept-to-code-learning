"""Additive, local reading annotations; existing note and context contracts stay intact."""

from typing import Annotated

from pydantic import AfterValidator, Field, model_validator

from .models import (
    ID,
    ContextRequest,
    Hash,
    Positive,
    Record,
    SelectionLocator,
    SourceLocator,
    SourceType,
    UTCDate,
    Value,
    digest,
)


def nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Annotation comment cannot be blank")
    return value


Comment = Annotated[str, Field(min_length=1, max_length=20000), AfterValidator(nonblank)]


class AnnotationAnchor(Value):
    document_id: ID
    document_revision: Positive
    original_sha256: Hash
    file_name: str
    source_type: SourceType
    unit_id: ID
    unit_locator: SourceLocator
    selected_text: Annotated[str, Field(min_length=1, max_length=10000)]
    selected_text_hash: Hash
    selection_locator: SelectionLocator

    @model_validator(mode="after")
    def exact_quote(self):
        if digest(self.selected_text) != self.selected_text_hash:
            raise ValueError("Annotation quote hash mismatch")
        return self


class CreateAnnotationRequest(ContextRequest):
    annotation_id: ID
    comment: Comment


class EditAnnotationRequest(Value):
    expected_revision: Positive
    comment: Comment


class Annotation(Record):
    annotation_id: ID
    anchor: AnnotationAnchor
    comment: Comment
    created_at: UTCDate
    updated_at: UTCDate


class AnnotationList(Record):
    document_id: ID
    annotations: list[Annotation]
    total: Annotated[int, Field(ge=0)]
    offset: Annotated[int, Field(ge=0)] = 0
