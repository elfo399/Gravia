from contextlib import aclosing


class CalibratedBoard:
    """Apply Gravia correction once, after hardware mapping and before sessions."""

    def __init__(self, hardware, calibration):
        self.hardware = hardware
        self.calibration = calibration

    async def start(self, publish_status):
        await self.hardware.start(publish_status)

    def get_status(self):
        return self.hardware.get_status().model_copy(
            update={"calibration_active": self.calibration.is_active}
        )

    async def shutdown(self):
        await self.hardware.shutdown()

    async def samples(self):
        async with aclosing(self.hardware.samples()) as stream:
            async for sample in stream:
                yield self.calibration.apply(sample)
