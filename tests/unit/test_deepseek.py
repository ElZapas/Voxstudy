from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

from voxstudy.adapters.deepseek import request_guide


class DeepSeekRequestTests(unittest.TestCase):
    def test_sends_transcript_and_bounded_note_metadata_and_parses_json(self) -> None:
        payload = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps({"title": "Guía", "summary": "Resumen."})},
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        response = Mock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("voxstudy.adapters.deepseek.urllib.request.urlopen", return_value=response) as urlopen:
                guide, usage = request_guide(
                    "La transcripción de prueba.",
                    related_notes=[{
                        "path": "Conceptos/Nota.md",
                        "title": "Nota existente",
                        "summary": "Resumen disponible para buscar conexiones.",
                    }],
                )

        request = urlopen.call_args.args[0]
        sent = json.loads(request.data)
        user_message = sent["messages"][1]["content"]
        self.assertIn("<transcripcion>\nLa transcripción de prueba.", user_message)
        self.assertIn('"path": "Conceptos/Nota.md"', user_message)
        self.assertEqual(guide["title"], "Guía")
        self.assertEqual(usage["total_tokens"], 15)


if __name__ == "__main__":
    unittest.main()
