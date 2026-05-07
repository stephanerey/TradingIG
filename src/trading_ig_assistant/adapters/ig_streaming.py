"""IG Streaming adapter placeholder.

P00 intentionally does not implement Lightstreamer connectivity. The module exists to preserve
the package boundary defined in the PRD.
"""


class IGStreamingAdapter:
    def start(self) -> None:
        raise NotImplementedError("Streaming is outside P00 bootstrap scope.")
