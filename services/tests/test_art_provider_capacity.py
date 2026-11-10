"""Per-provider art capacity: local and muse slots are independent."""

from __future__ import annotations

import asyncio

from airunner_services.utils.job_tracker import JobTracker


def _fresh_tracker() -> JobTracker:
    JobTracker._instance = None
    JobTracker._lock = asyncio.Lock()
    return JobTracker()


def test_muse_job_does_not_block_local_and_vice_versa() -> None:
    async def scenario() -> None:
        tracker = _fresh_tracker()
        muse = await tracker.create_art_job(
            metadata={"provider": "muse"}, capacity=1)
        assert muse is not None
        # Same provider is full; the other provider still admits.
        assert await tracker.create_art_job(
            metadata={"provider": "muse"}, capacity=1) is None
        local = await tracker.create_art_job(
            metadata={"provider": "local"}, capacity=1)
        assert local is not None
        assert await tracker.create_art_job(capacity=1) is None
        # Finishing the muse job frees only the muse slot.
        await tracker.finish_art_job(muse)
        again = await tracker.create_art_job(
            metadata={"provider": "muse"}, capacity=1)
        assert again is not None
        await tracker.finish_art_job(again)
        await tracker.finish_art_job(local)

    asyncio.run(scenario())


def test_legacy_caller_without_provider_counts_as_local() -> None:
    async def scenario() -> None:
        tracker = _fresh_tracker()
        first = await tracker.create_art_job(capacity=1)
        assert first is not None
        assert await tracker.create_art_job(
            metadata={"provider": "local"}, capacity=1) is None
        cloud = await tracker.create_art_job(
            metadata={"provider": "muse"}, capacity=1)
        assert cloud is not None
        await tracker.finish_art_job(first)
        await tracker.finish_art_job(cloud)

    asyncio.run(scenario())


def test_provider_kwarg_without_metadata_is_counted() -> None:
    async def scenario() -> None:
        tracker = _fresh_tracker()
        first = await tracker.create_art_job(
            metadata={}, capacity=1, provider="muse")
        assert first is not None
        assert await tracker.create_art_job(
            metadata={}, capacity=1, provider="muse") is None
        local = await tracker.create_art_job(
            metadata={}, capacity=1, provider="local")
        assert local is not None
        job = await tracker.get_status(first)
        assert job is not None and job.metadata["provider"] == "muse"
        await tracker.finish_art_job(first)
        await tracker.finish_art_job(local)

    asyncio.run(scenario())
