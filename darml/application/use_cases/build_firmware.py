import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from darml.application.pipeline.context import BuildContext
from darml.application.pipeline.pipeline import BuildPipeline
from darml.application.ports.build_cache import BuildCachePort
from darml.application.ports.build_repository import BuildRepositoryPort
from darml.application.ports.file_storage import FileStoragePort
from darml.domain.enums import BuildStatus
from darml.domain.models import BuildRequest, BuildResult


@dataclass
class BuildFirmware:
    """Orchestrate the full model-to-firmware build pipeline.

    Adds two cross-cutting concerns on top of the raw pipeline:
      - Build cache: identical (model, target, options) returns a cached
        artifact in O(copy) time instead of recompiling.
      - Build timeout: hung pipelines (e.g. wedged subprocess) are killed
        after `timeout_s` and the result is marked FAILED with a clear error.

    Exposes two entry points:
      - `start`: register, schedule, and return immediately (HTTP API).
      - `execute`: run synchronously to completion (CLI, tests).
    """

    pipeline: BuildPipeline
    repo: BuildRepositoryPort
    storage: FileStoragePort
    cache: BuildCachePort | None = None
    timeout_s: int | None = None

    async def start(self, request: BuildRequest) -> BuildResult:
        result = BuildResult.new(target_id=request.target_id)
        await self.repo.save(result)
        asyncio.create_task(self._run(request, result))
        return result

    async def execute(self, request: BuildRequest) -> BuildResult:
        result = BuildResult.new(target_id=request.target_id)
        await self.repo.save(result)
        return await self._run(request, result)

    async def _run(self, request: BuildRequest, result: BuildResult) -> BuildResult:
        workspace = self.storage.workspace(result.build_id)
        workspace.mkdir(parents=True, exist_ok=True)

        # Cache lookup before any compute.
        cache_key: str | None = None
        if self.cache is not None:
            try:
                cache_key = self.cache.key_for(request)
                cached = self.cache.get(cache_key, workspace, result.build_id)
            except Exception:
                cached = None
            if cached is not None:
                await self.repo.save(cached)
                return cached

        ctx = BuildContext(
            request=request,
            result=result,
            workspace=workspace,
            current_model_path=request.model_path,
        )
        try:
            if self.timeout_s and self.timeout_s > 0:
                await asyncio.wait_for(self.pipeline.run(ctx), timeout=self.timeout_s)
            else:
                await self.pipeline.run(ctx)
        except asyncio.TimeoutError:
            ctx.result.status = BuildStatus.FAILED
            ctx.result.error = (
                f"Build exceeded DARML_BUILD_TIMEOUT={self.timeout_s}s and was killed. "
                "Increase the timeout for first-time toolchain fetches, or check "
                "for a wedged subprocess."
            )
            ctx.result.completed_at = datetime.now(timezone.utc)
        except Exception:
            # BuildPipeline already sets status=FAILED + error on ctx.result.
            pass
        finally:
            await self.repo.save(ctx.result)

        if (
            self.cache is not None
            and cache_key is not None
            and ctx.result.status == BuildStatus.COMPLETED
        ):
            try:
                self.cache.put(cache_key, ctx.result)
            except Exception:
                pass

        return ctx.result
