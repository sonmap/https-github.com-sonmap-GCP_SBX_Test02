import subprocess
import tempfile
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ReleaseBootstrapTests(unittest.TestCase):
    def test_customer_validation_runs_without_python_command(self):
        config = yaml.safe_load((ROOT/'03.cloudbuild/platform-release.yaml').read_text())
        step = config['steps'][0]
        self.assertEqual(step['entrypoint'], 'bash')
        script = step['args'][-1].replace('$$', '$')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'02.sandbox_setup_01_gcloud/configs/provisioner-env.yaml'
            path.parent.mkdir(parents=True)
            for value, expected in [('C03rw3vtp', 0), ('__SET_CUSTOMER_ID__', 1), ('', 1)]:
                path.write_text('CLOUD_IDENTITY_CUSTOMER_ID: '+value+'\n')
                result = subprocess.run(['bash', '-ceu', script], cwd=tmp, capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_publish_step_uses_built_runner_with_python(self):
        config = yaml.safe_load((ROOT/'03.cloudbuild/platform-release.yaml').read_text())
        steps = config['steps']
        publish = next(s for s in steps if s['id']=='publish-sandbox-source')
        self.assertEqual(publish['name'], '${_AUTOMATION_IMAGE_REPO}:${_RELEASE_ID}')
        self.assertLess(next(i for i,s in enumerate(steps) if s['id']=='push-automation-runner-release'), steps.index(publish))
        self.assertIn('set -o pipefail', publish['args'][-1])
        self.assertIn('$${archive_uri}', publish['args'][-1])
