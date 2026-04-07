import io
import json
import unittest
from types import SimpleNamespace

try:
    from fastapi import HTTPException
    from app.api.custom_exercises import _ensure_publish_ready, _validate_reference_video_upload
    IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific fallback
    HTTPException = Exception
    _ensure_publish_ready = None
    _validate_reference_video_upload = None
    IMPORT_ERROR = exc


@unittest.skipIf(IMPORT_ERROR is not None, f"Project API deps are unavailable: {IMPORT_ERROR}")
class CustomExercisePipelineTests(unittest.TestCase):
    def test_publish_ready_accepts_clean_high_score(self) -> None:
        payload = json.dumps(
            {
                "rep_score": 84,
                "errors": [],
                "details": {"caps_applied": []},
            }
        )

        _ensure_publish_ready(payload)

    def test_publish_ready_rejects_low_score(self) -> None:
        payload = json.dumps(
            {
                "rep_score": 64,
                "errors": [],
                "details": {"caps_applied": []},
            }
        )

        with self.assertRaises(HTTPException) as exc:
            _ensure_publish_ready(payload)

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("score не ниже", str(exc.exception.detail))

    def test_publish_ready_rejects_caps(self) -> None:
        payload = json.dumps(
            {
                "rep_score": 88,
                "errors": ["Недостаточный ракурс"],
                "details": {"caps_applied": ["bad_view"]},
            }
        )

        with self.assertRaises(HTTPException) as exc:
            _ensure_publish_ready(payload)

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("caps", str(exc.exception.detail))

    def test_validate_reference_video_upload_accepts_supported_video(self) -> None:
        upload = SimpleNamespace(
            filename="reverse-lunge.mp4",
            content_type="video/mp4",
            file=io.BytesIO(b"video"),
        )

        suffix = _validate_reference_video_upload(upload, {"size_bytes": 1024})

        self.assertEqual(suffix, ".mp4")

    def test_validate_reference_video_upload_rejects_wrong_extension(self) -> None:
        upload = SimpleNamespace(
            filename="reverse-lunge.avi",
            content_type="video/x-msvideo",
            file=io.BytesIO(b"video"),
        )

        with self.assertRaises(HTTPException) as exc:
            _validate_reference_video_upload(upload, {"size_bytes": 1024})

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("MP4", str(exc.exception.detail))


if __name__ == "__main__":
    unittest.main()
