from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

from modal_app.workers.s3_results import upload_generation_result


class PrivateS3ResultTests(unittest.TestCase):
    def test_upload_uses_private_defaults_and_server_side_encryption(self) -> None:
        calls: list[dict[str, object]] = []

        class FakeClient:
            def put_object(self, **kwargs):
                calls.append(kwargs)
                return {"ETag": '"etag"'}

        fake_boto3 = types.SimpleNamespace(
            client=lambda service, region_name=None: FakeClient()
        )
        with (
            patch.dict(
                os.environ,
                {"AWS_S3_BUCKET": "private-bucket", "AWS_REGION": "eu-west-1"},
                clear=False,
            ),
            patch.dict(sys.modules, {"boto3": fake_boto3}),
        ):
            result = upload_generation_result("job-1", b"glb")

        self.assertEqual(result["resultKey"], "jobs/job-1/output.glb")
        self.assertEqual(calls[0]["ServerSideEncryption"], "AES256")
        self.assertNotIn("ACL", calls[0])


if __name__ == "__main__":
    unittest.main()
