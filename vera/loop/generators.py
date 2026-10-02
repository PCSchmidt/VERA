"""Different generator models for different stages (docs/04 T9, the generator comparison).

The loop's nodes call one `deps.generator.generate(system, prompt, component="p3.<stage>")`. `ByStage` is that object
when the stages use different models: it dispatches on the stage in the component name, so "GLM for ideas and code,
Sonnet for the write-up" is a configuration, not a code change. Every generator behind it writes to the same run
ledger and charges the same `Budget`.
"""

from __future__ import annotations

from collections.abc import Mapping

from vera.loop.stages import Generator


class ByStage:
    def __init__(self, by_stage: Mapping[str, Generator], default: Generator | None = None) -> None:
        self.by_stage, self.default = dict(by_stage), default

    def generate(self, system: str, prompt: str, *, component: str) -> str:
        stage = component.split(".", 1)[-1]
        generator = self.by_stage.get(stage, self.default)
        if generator is None:
            raise KeyError(f"no generator configured for stage {stage!r}")
        return generator.generate(system, prompt, component=component)
