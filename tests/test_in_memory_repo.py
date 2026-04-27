import asyncio

from darml.domain.enums import BuildStatus
from darml.domain.models import BuildResult
from darml.infrastructure.persistence.in_memory_build_repo import InMemoryBuildRepository


def test_save_and_get_roundtrip():
    repo = InMemoryBuildRepository()
    build = BuildResult.new(target_id="esp32-s3")

    async def run():
        await repo.save(build)
        return await repo.get(build.build_id)

    got = asyncio.run(run())
    assert got is not None
    assert got.build_id == build.build_id
    assert got.status == BuildStatus.PENDING


def test_get_missing_returns_none():
    repo = InMemoryBuildRepository()

    async def run():
        return await repo.get("does-not-exist")

    assert asyncio.run(run()) is None


def test_list_returns_most_recent_first():
    repo = InMemoryBuildRepository()

    async def run():
        a = BuildResult.new(target_id="esp32-s3")
        b = BuildResult.new(target_id="stm32f4")
        await repo.save(a)
        await asyncio.sleep(0.001)
        await repo.save(b)
        return await repo.list()

    listed = asyncio.run(run())
    assert len(listed) == 2
    assert listed[0].target_id == "stm32f4"
