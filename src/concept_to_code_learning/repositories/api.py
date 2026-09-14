"""Explicit repository imports and paged, lazy tree navigation."""

import asyncio

from fastapi import APIRouter, Query

from concept_to_code_learning.full_contracts import models as m

from .models import AddRepository, OpenFile, Repository, TreePage


def repository_router(library):
    router = APIRouter(prefix="/repositories", tags=["Repository workspace"])

    @router.get("", response_model=list[Repository])
    def repositories():
        return library.list()

    @router.get("/search")
    async def search(q: str = Query(min_length=1, max_length=100)):
        names = await library.client.search_repositories([q], 6)
        values = await asyncio.gather(*(library.client.repository(*name.split("/")) for name in names),
                                      return_exceptions=True)
        if values and all(isinstance(value, Exception) for value in values):
            raise values[0]
        return [{"repository": value["full_name"], "description": str(value.get("description") or "")[:500],
                 "language": value.get("language")} for value in values if isinstance(value, dict)]

    @router.post("", response_model=Repository, status_code=201)
    async def add(body: AddRepository):
        return await library.add(body)

    @router.get("/{repository_id}", response_model=Repository)
    def repository(repository_id: m.ID):
        return library.get(repository_id)

    @router.get("/{repository_id}/tree", response_model=TreePage)
    async def tree(repository_id: m.ID, directory: str = Query(default="", max_length=1000),
                   q: str = Query(default="", max_length=100), offset: int = Query(default=0, ge=0),
                   limit: int = Query(default=300, ge=1, le=500)):
        return await library.tree(repository_id, directory, q, offset, limit)

    @router.post("/{repository_id}/files", response_model=OpenFile)
    async def open_file(repository_id: m.ID, path: str = Query(min_length=1, max_length=1000)):
        return await library.open_file(repository_id, path)

    return router
