import importlib
import os
import unittest
from unittest.mock import patch

import backend.config as config_module


class SpeechToTextConfigTests(unittest.TestCase):
    def test_default_stt_engine_is_mock_when_env_is_unset(self):
        with patch.dict(os.environ, {'RENDER': 'true'}, clear=False):
            os.environ.pop('STT_ENGINE', None)
            reloaded = importlib.reload(config_module)
            self.assertEqual(reloaded.Config.STT_ENGINE, 'mock')


if __name__ == '__main__':
    unittest.main()
