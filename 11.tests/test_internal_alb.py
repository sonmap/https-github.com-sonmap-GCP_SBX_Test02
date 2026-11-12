import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reconcile", ROOT / "09.sandbox_gke_deployer/reconcile_postdeploy.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PROJECT = "gcp-sbx-edp-gke01"
REGION = "asia-northeast3"
ENV = {"GCP_REGION": REGION, "SHARED_NETWORK_URI": "projects/gcp-prod-edp-hub-vpchost/global/networks/vpc-prod-edp-hub"}


class InternalAlbTests(unittest.TestCase):
    @mock.patch.dict(os.environ,{'SBX_GKE_PROJECT':PROJECT})
    def test_dedicated_cross_project_ksa_annotation_is_verified(self):
        request={'task':{'name':'sbx03'},'gke':{'namespace':'sbx03'},'project':{'project_id':'gcp-sbx-edp-sbx03'},'identity':{'create_jupyter_gsa':True}}
        email='gsa-jupyter-sbx03@gcp-sbx-edp-sbx03.iam.gserviceaccount.com'
        with mock.patch.object(module,'run',return_value=email):
            module.verify_workload_identity(request,ENV)
        with mock.patch.object(module,'run',return_value='sbx-manager@'+PROJECT+'.iam.gserviceaccount.com'):
            with self.assertRaisesRegex(RuntimeError,'KSA/GSA mismatch'):module.verify_workload_identity(request,ENV)

    def test_health_and_backend_are_regional_and_internal(self):
        neg = {"name": "neg-sbx01", "zone": REGION + "-a", "self_link": f"projects/{PROJECT}/zones/{REGION}-a/networkEndpointGroups/neg-sbx01"}
        with mock.patch.object(module, "gcloud_describe_or_none", side_effect=[None, None, {"backends": []}]) as describe, mock.patch.object(module, "gcloud", return_value="") as cloud:
            hc = module.ensure_health_check(PROJECT, "sbx01", ENV)
            module.ensure_backend_service(PROJECT, "sbx01", hc, [neg], ENV)
        for call in describe.call_args_list:
            self.assertIn("--region=" + REGION, call.args[0])
            self.assertNotIn("--global", call.args[0])
        calls = [call.args for call in cloud.call_args_list]
        for args in calls:
            self.assertIn("--region=" + REGION, args)
            self.assertNotIn("--global", args)
        backend = next(args for args in calls if args[:3] == ("compute", "backend-services", "create"))
        self.assertIn("--load-balancing-scheme=INTERNAL_MANAGED", backend)
        self.assertFalse(any(arg.startswith("--network=") for arg in backend))
        self.assertIn("--health-checks-region=" + REGION, backend)

    def test_url_map_uses_full_regional_backend_uri(self):
        uri = f"projects/{PROJECT}/regions/{REGION}/backendServices/bes-jupyter-sbx01"
        matcher = {"name": "sbx01", "defaultService": uri}
        host = {"hosts": ["jupyter-sbx01.sonmap.net"], "pathMatcher": "sbx01"}
        maps = iter([{}, {"pathMatchers": [matcher]}, {"pathMatchers": [matcher], "hostRules": [host]}])
        def response(*args, **kwargs):
            if args[:3] == ("compute", "url-maps", "describe"):
                return json.dumps(next(maps))
            return ""
        with mock.patch.object(module, "gcloud", side_effect=response) as cloud:
            module.reconcile_url_map(PROJECT, "urlmap-alb-sbxtest01-shared", "sbx01", host["hosts"][0], "bes-jupyter-sbx01", ENV)
        calls = [call.args for call in cloud.call_args_list]
        self.assertTrue(any("--default-service=" + uri in args for args in calls))
        self.assertTrue(all("--region=" + REGION in args for args in calls))
        self.assertFalse(module.expected_backend({"defaultService": f"projects/{PROJECT}/global/backendServices/bes-jupyter-sbx01"}, uri))

    def test_incompatible_existing_backend_is_rejected(self):
        for current in [{"loadBalancingScheme": "EXTERNAL"}, {"loadBalancingScheme": "INTERNAL_MANAGED", "protocol": "HTTPS"}]:
            with self.subTest(current=current), mock.patch.object(module, "gcloud_describe_or_none", return_value=current), mock.patch.object(module, "gcloud") as cloud:
                with self.assertRaises(RuntimeError):
                    module.ensure_backend_service(PROJECT, "sbx01", "hc", [], ENV)
                cloud.assert_not_called()

    def test_permission_failure_is_not_missing_resource(self):
        result = mock.Mock(returncode=1, stdout="", stderr="Could not fetch resource: Required permission missing (403)")
        with mock.patch.object(module.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError):
                module.gcloud_describe_or_none(("compute", "backend-services", "describe", "bes"))

    def test_foundation_uses_shared_vpc_internal_vip_and_proxy_subnet(self):
        network = (ROOT / "02.sandbox_setup_01_gcloud/02-network.md").read_text()
        foundation = (ROOT / "02.sandbox_setup_01_gcloud/03-foundation.md").read_text()
        self.assertIn("--purpose=REGIONAL_MANAGED_PROXY --role=ACTIVE", network)
        self.assertIn("export ILB_VIP_CIDR=172.31.96.0/27", network)
        self.assertIn("export ILB_PROXY_CIDR=172.31.111.64/26", network)
        self.assertIn("--source-ranges=\"${ILB_PROXY_CIDR}\"", network)
        for line in foundation.splitlines():
            if line.startswith("gcloud compute ") and any(resource in line for resource in ["addresses ", "backend-services ", "health-checks ", "url-maps ", "target-http-proxies ", "target-https-proxies ", "forwarding-rules ", "ssl-certificates "]):
                self.assertIn('--region="${REGION}"', line)
                self.assertNotIn("--global", line)
        self.assertNotIn("--load-balancing-scheme=EXTERNAL", foundation)
        self.assertIn("--purpose=SHARED_LOADBALANCER_VIP", foundation)
        self.assertIn('subnetworks/${ILB_VIP_SUBNET}', foundation)


if __name__ == "__main__":
    unittest.main()
