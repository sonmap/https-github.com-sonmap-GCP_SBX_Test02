import unittest
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[1]


class BuildPathTests(unittest.TestCase):
    def test_bootstrap_and_release_docker_contexts_exist(self):
        for name in ['02.sandbox_setup_01_gcloud/configs/bootstrap-build.yaml','03.cloudbuild/platform-release.yaml']:
            config=yaml.safe_load((ROOT/name).read_text())
            for step in config['steps']:
                args=step.get('args',[])
                if not args or args[0]!='build':continue
                context=ROOT/args[-1]
                self.assertTrue(context.is_dir(),(name,args[-1]))
                dockerfile=ROOT/args[args.index('-f')+1] if '-f' in args else context/'Dockerfile'
                self.assertTrue(dockerfile.is_file(),str(dockerfile))
                for line in dockerfile.read_text().splitlines():
                    if not line.startswith('COPY '):continue
                    parts=line.split()
                    for source in parts[1:-1]:
                        self.assertTrue((context/source).exists(),(str(dockerfile),source))

    def test_removed_data_access_component_has_no_build_or_doc_links(self):
        self.assertFalse((ROOT/'datalake-access-provisioner').exists())
        for path in ROOT.rglob('*'):
            if not path.is_file() or any(p in path.parts for p in ['.git','__pycache__','11.tests']):continue
            self.assertNotIn('datalake-access-provisioner',path.read_text(),str(path))


if __name__=='__main__':unittest.main()
