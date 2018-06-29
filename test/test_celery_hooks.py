from tor.celeryconfig import Config

import unittest


class CeleryConfigHooksTest(unittest.TestCase):
    def setUp(self):
        self.c = Config()

    def test_stuff(self):
        assert hasattr(self.c, "timezone")
        assert self.c.timezone == "UTC", "always use UTC for timezone"
        assert hasattr(self.c, "enable_utc")
        assert self.c.enable_utc is True, "always use UTC for timezone"

        assert hasattr(
            self.c, "task_default_queue"
        ), "Default queue should be defined so we can make sure all packages agree on it. This is purely a safety check."

        assert hasattr(self.c, "beat_schedule")
        assert isinstance(self.c.beat_schedule, dict)

        assert hasattr(self.c, "task_routes")
        assert isinstance(self.c.task_routes, tuple)
