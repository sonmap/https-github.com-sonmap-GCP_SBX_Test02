import importlib.util
import json
import runpy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "12.sandbox_shared"
EXAMPLE = Path(__file__).resolve().with_name("fixtures") / "group.example.json"
spec = importlib.util.spec_from_file_location("shared_sandbox", FEATURE / "shared_sandbox.py")
sandbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sandbox)


class SharedSandboxTests(unittest.TestCase):
    def setUp(self):
        self.group = sandbox.load_group(EXAMPLE)
        self.task = "sbx01"

    def resources(self):
        return sandbox.task_resources(self.group, self.task)["items"]

    def test_task_has_one_pod_and_one_shared_home_with_five_distinct_member_sessions(self):
        deployment, = [item for item in self.resources() if item["kind"] == "Deployment"]
        pod = deployment["spec"]["template"]["spec"]
        self.assertNotIn("replicas", deployment["spec"])
        self.assertEqual(pod["serviceAccountName"], "ksa-jupyter-sbx01")
        self.assertEqual(pod["volumes"][0]["persistentVolumeClaim"]["claimName"], "notebook-home")
        containers = pod["containers"]
        self.assertEqual(len(containers), 5)
        self.assertEqual(sum(int(c["resources"]["requests"]["cpu"][:-1]) for c in containers), 8000)
        self.assertEqual(sum(int(c["resources"]["requests"]["memory"][:-2]) for c in containers), 65536)
        for container, member in zip(containers, self.group["tasks"][self.task]["members"]):
            self.assertEqual(container["env"][0]["value"], f"/home/jupyter/{member}")
            self.assertEqual(container["volumeMounts"][0]["subPath"], self.task)
        secrets = [v["secret"]["secretName"] for v in pod["volumes"] if "secret" in v]
        self.assertEqual(len(set(secrets)), 5)
        role, = [item for item in self.resources() if item["kind"] == "Role"]
        self.assertEqual(role["rules"][0]["resourceNames"], secrets)
        self.assertEqual(role["rules"][0]["verbs"], ["patch"])

    def test_existing_member_home_can_keep_its_vm_directory_name(self):
        task = self.group["tasks"][self.task]
        task["home_dirs"] = {task["members"][0]: "legacy-user"}
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "group.json"
            config.write_text(json.dumps(self.group))
            self.group = sandbox.load_group(config)
            deployment, = [item for item in self.resources() if item["kind"] == "Deployment"]
            containers = deployment["spec"]["template"]["spec"]["containers"]
            self.assertEqual(containers[0]["env"][0]["value"], "/home/jupyter/legacy-user")
            task = self.group["tasks"][self.task]
            task["home_dirs"][task["members"][0]] = "../other-task"
            config.write_text(json.dumps(self.group))
            with self.assertRaisesRegex(ValueError, "relative directory"):
                sandbox.load_group(config)

    def test_existing_claim_is_not_recreated_and_dynamic_claim_is_created_once(self):
        self.assertFalse(any(item["kind"] == "PersistentVolumeClaim" for item in self.resources()))
        self.group["tasks"][self.task]["storage"]["storage_class"] = "filestore-retain"
        claim, = [item for item in self.resources() if item["kind"] == "PersistentVolumeClaim"]
        self.assertEqual(claim["spec"]["resources"]["requests"]["storage"], "100Gi")
        self.assertEqual(claim["spec"]["accessModes"], ["ReadWriteMany"])

    def test_group_uses_local_test_accounts_and_group_proxy(self):
        values = sandbox.group_values(self.group)
        configs = values["hub"]["extraConfig"]
        for name, source in configs.items():
            compile(source, name, "exec")
        config = configs["50-shared-sandbox"]
        self.assertIn("SharedTestAuthenticator", config)
        self.assertIn(self.group["tasks"][self.task]["members"][0], config)
        self.assertNotIn("GenericOAuthenticator", config)
        self.assertNotIn("oauth_callback_url", config)
        volume, = values["hub"]["extraVolumes"]
        self.assertEqual(volume["secret"]["secretName"], "shared-test-accounts")
        self.assertEqual(volume["secret"]["items"][0]["key"], "accounts.json")
        self.assertIn("cloud.google.com/neg", values["proxy"]["service"]["annotations"])

    def test_password_hashes_are_salted_and_reject_wrong_passwords(self):
        passwords = runpy.run_path(str(FEATURE / "test_passwords.py"))
        password = "test-only-example-password"
        first = passwords["hash_password"](password)
        second = passwords["hash_password"](password)
        self.assertNotEqual(first, second)
        self.assertNotIn(password, first)
        self.assertTrue(passwords["verify_password"](password, first))
        self.assertFalse(passwords["verify_password"]("incorrect", first))
        self.assertFalse(passwords["verify_password"](password, "malformed"))

    def test_stop_changes_replicas_and_clears_sessions_without_touching_pvc(self):
        with patch.object(sys, "argv", ["tool", str(EXAMPLE), "stop", self.task, "--context", "ctx"]):
            with patch.object(sandbox, "kubectl") as kubectl:
                sandbox.main()
        commands = [call.args for call in kubectl.call_args_list]
        self.assertEqual(commands[0], ("ctx", self.task, "scale", "deployment/notebook", "--replicas=0"))
        self.assertEqual(len(commands), 6)
        self.assertTrue(all(command[2:4] == ("patch", "secret") for command in commands[1:]))

    def test_rejects_duplicate_members_and_unpinned_images(self):
        task = self.group["tasks"][self.task]
        original = task["members"][:]
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "group.json"
            task["members"][0] = task["members"][1]
            config.write_text(json.dumps(self.group))
            with self.assertRaisesRegex(ValueError, "five unique"):
                sandbox.load_group(config)
            task["members"] = original
            task["image"] = task["image"].split("@")[0] + ":latest"
            config.write_text(json.dumps(self.group))
            with self.assertRaisesRegex(ValueError, "image digest"):
                sandbox.load_group(config)
