import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "deploy_shared_group", ROOT / "09.sandbox_gke_deployer/deploy_shared_group.py",
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class SharedGroupDeployTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / "11.tests/fixtures/group.example.json").read_bytes()
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.env = {"SHARED_URL_MAP_NAME": "urlmap-test", "SHARED_BUILD_ID": "build-test"}
        self.group = "sandbox-group-01"
        self.bucket = Mock()
        self.lock = Mock(generation=12)
        self.approved = Mock(name="approved")
        self.approved.name = f"approved-groups/{self.group}/group.json"
        self.approved.generation = 34
        current = Mock()
        current.download_as_bytes.return_value = self.raw
        self.bucket.blob.side_effect = [self.lock, current]
        self.bucket.get_blob.return_value = self.approved
        self.apply = Mock()

    def test_applies_approved_generation_and_releases_own_lock(self):
        runner.deploy(self.group, 34, self.digest, self.env, self.bucket, apply=self.apply)
        self.lock.upload_from_string.assert_called_once_with("build-test", if_generation_match=0)
        self.bucket.get_blob.assert_called_once_with(self.approved.name)
        self.apply.assert_called_once()
        self.assertEqual(self.apply.call_args.args[0]["group"], self.group)
        self.lock.delete.assert_called_once_with(if_generation_match=12)

    def test_rejects_superseded_or_changed_approval(self):
        for generation, digest in [(33, self.digest), (34, "0" * 64)]:
            with self.subTest(generation=generation, digest=digest):
                self.setUp()
                with self.assertRaises(ValueError):
                    runner.deploy(self.group, generation, digest, self.env, self.bucket, apply=self.apply)
                self.apply.assert_not_called()
                self.lock.delete.assert_called_once_with(if_generation_match=12)

    def test_workflow_uses_private_pool_runner(self):
        path = ROOT / "07.sandbox_request_api/shared-group-workflow.yaml"
        deploy = yaml.safe_load(path.read_text())["main"]["steps"][1]["deploy"]
        body = deploy["args"]["body"]
        self.assertIn("SBX_WORKER_POOL", body["options"]["pool"]["name"])
        self.assertEqual(body["steps"][0]["args"][0], "/opt/sandbox/deploy_shared_group.py")
        self.assertEqual(body["steps"][0]["env"][-1], "SHARED_BUILD_ID=$BUILD_ID")


if __name__ == "__main__":
    unittest.main()
