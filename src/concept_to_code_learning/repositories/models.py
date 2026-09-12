"""Additive repository workspace contracts; no browser-supplied evidence."""

from typing import Annotated, Literal

from pydantic import Field

from concept_to_code_learning.full_contracts import models as m


class AddRepository(m.Value):
    repository: Annotated[str, Field(min_length=1, max_length=300)]
    ref: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class Repository(m.Record):
    repository_id: m.ID
    repository: m.Repo
    description: str = ""
    ref: str
    commit_sha: m.Commit
    tree_sha: m.Commit
    complete_tree: bool
    created_at: m.UTCDate


class TreeEntry(m.Value):
    path: Annotated[str, Field(min_length=1, max_length=1000)]
    sha: m.Commit
    kind: Literal["folder", "file", "symlink", "submodule"]
    size: int = Field(default=0, ge=0)


class TreePage(m.Value):
    entries: list[TreeEntry]
    directory: str
    total: int
    offset: int
    complete_tree: bool


class OpenFile(m.Value):
    document: m.DocumentRecord
    units: list[m.DocumentUnit]
