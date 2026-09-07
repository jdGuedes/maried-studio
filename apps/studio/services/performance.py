import logging
import time
from contextlib import contextmanager

from django.utils import timezone


logger = logging.getLogger(__name__)


class GenerationPerformanceTracker:
    def __init__(
        self,
        *,
        clock=None,
        queued_at=None,
        claimed_at=None,
    ):
        self.clock = clock or time.perf_counter
        self.started_at = self.clock()
        self.queued_at = queued_at
        self.claimed_at = claimed_at
        self.stage_durations = {}
        self.failure_stage = ""

    @contextmanager
    def measure(self, stage):
        start = self.clock()

        try:
            yield

        except Exception:
            if not self.failure_stage:
                self.failure_stage = stage

            raise

        finally:
            elapsed_ms = self._elapsed_ms(start)
            self.stage_durations[stage] = (
                self.stage_durations.get(stage, 0.0)
                + elapsed_ms
            )

    def start_stage(self):
        return self.clock()

    def stop_stage(self, stage, start):
        elapsed_ms = self._elapsed_ms(start)
        self.stage_durations[stage] = (
            self.stage_durations.get(stage, 0.0)
            + elapsed_ms
        )

    def mark_failure(self, stage):
        if not self.failure_stage:
            self.failure_stage = stage

    def mark_claimed_at(self, claimed_at):
        self.claimed_at = claimed_at

    def metrics(
        self,
        *,
        generation,
        success,
        provider,
        model,
        input_metadata=None,
        output_metadata=None,
    ):
        input_metadata = input_metadata or {}
        output_metadata = output_metadata or {}
        total_ms = self._elapsed_ms(self.started_at)
        queue_wait_ms = self._queue_wait_ms()
        provider_ms = self.stage_durations.get(
            "provider",
            0.0,
        )
        internal_ms = max(
            total_ms - provider_ms,
            0.0,
        )

        data = {
            "generation_id": str(generation.pk),
            "organization_id": str(generation.organization_id),
            "generation_type": generation.mode,
            "provider": provider,
            "model": model,
            "success": success,
            "total_duration_ms": self._round(total_ms),
            "processing_total_duration_ms": self._round(total_ms),
            "queue_wait_duration_ms": self._round(queue_wait_ms),
            "provider_duration_ms": self._round(provider_ms),
            "internal_duration_ms": self._round(internal_ms),
            "provider_percentage": self._round(
                (provider_ms / total_ms * 100)
                if total_ms
                else 0.0
            ),
            "validation_duration_ms": self._stage("validation"),
            "credit_duration_ms": self._stage("credit"),
            "asset_preparation_duration_ms": self._stage(
                "asset_preparation"
            ),
            "prompt_duration_ms": self._stage("prompt"),
            "result_processing_duration_ms": self._stage(
                "result_processing"
            ),
            "storage_duration_ms": self._stage("storage"),
            "db_finalize_duration_ms": self._stage("db_finalize"),
            "failure_stage": self.failure_stage,
            **input_metadata,
            **output_metadata,
        }

        return data

    def log(
        self,
        *,
        generation,
        success,
        provider,
        model,
        input_metadata=None,
        output_metadata=None,
    ):
        data = self.metrics(
            generation=generation,
            success=success,
            provider=provider,
            model=model,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
        )

        if success:
            logger.info(
                self._message(data),
                extra=data,
            )
        else:
            logger.warning(
                self._message(data),
                extra=data,
            )

        return data

    def _message(self, data):
        fields = [
            ("generation_id", "generation_id"),
            ("generation_type", "generation_type"),
            ("provider", "provider"),
            ("success", "success"),
            ("queue_wait_ms", "queue_wait_duration_ms"),
            (
                "processing_total_ms",
                "processing_total_duration_ms",
            ),
            ("total_ms", "total_duration_ms"),
            ("provider_ms", "provider_duration_ms"),
            ("internal_ms", "internal_duration_ms"),
            ("storage_ms", "storage_duration_ms"),
            ("validation_ms", "validation_duration_ms"),
            ("credit_ms", "credit_duration_ms"),
            (
                "asset_preparation_ms",
                "asset_preparation_duration_ms",
            ),
            ("prompt_ms", "prompt_duration_ms"),
            (
                "result_processing_ms",
                "result_processing_duration_ms",
            ),
            ("db_finalize_ms", "db_finalize_duration_ms"),
            ("input_size_bytes", "input_file_size_bytes"),
            ("output_size_bytes", "output_size_bytes"),
            ("failure_stage", "failure_stage"),
        ]
        parts = ["generation_performance"]

        for label, key in fields:
            value = data.get(key)

            if value in (None, ""):
                continue

            if isinstance(value, bool):
                value = str(value).lower()

            parts.append(
                f"{label}={value}"
            )

        return " ".join(parts)

    def _queue_wait_ms(self):
        if (
            not self.queued_at
            or not self.claimed_at
        ):
            return 0.0

        return (
            self.claimed_at - self.queued_at
        ).total_seconds() * 1000

    def _stage(self, stage):
        return self._round(
            self.stage_durations.get(
                stage,
                0.0,
            )
        )

    def _elapsed_ms(self, start):
        return (
            self.clock() - start
        ) * 1000

    @staticmethod
    def _round(value):
        return round(
            value,
            3,
        )
