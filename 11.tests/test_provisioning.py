import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('provisioner',ROOT/'07.sandbox_request_api/main.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
ENV={'SBX_GKE_PROJECT':'gcp-sbx-edp-gke01','GCP_REGION':'asia-northeast3',
     'BUNDLE_BUCKET':'gcp-sbx-edp-gke01-sbxtest01-bundles',
     'REQUEST_BUCKET':'gcp-sbx-edp-gke01-sbxtest01-requests',
     'WORKER_POOL':'projects/gcp-sbx-edp-gke01/locations/asia-northeast3/workerPools/pool-sbxtest01',
     'CLOUD_IDENTITY_CUSTOMER_ID':'C123test',
     'JUPYTER_CHART_URI':'oci://example/jupyterhub','JUPYTER_CHART_VERSION':'4.2.0'}


def payload():
    data=json.loads((ROOT/'05.sandbox_json/sbx01-approved-request.json').read_text())
    data['source']['sha256']='a'*64
    data['source']['release_id']='git-test123'
    data['network'].update(required=True,shared_vpc_join=False,subnet_name='subnet-sbx01-an3',subnet_cidr='172.31.110.0/24')
    return data


class ProvisioningTests(unittest.TestCase):
    @mock.patch.dict(os.environ,ENV)
    def test_bundles_use_shared_gsa_and_import_only_dataset_bucket(self):
        written={}
        bucket=mock.Mock();bucket.name=ENV['BUNDLE_BUCKET'];bucket.blob.side_effect=lambda name:name
        def download(source,destination):
            shutil.copytree(ROOT/'08.sandbox_setup_02_terraform',destination/'08.sandbox_setup_02_terraform')
            return destination
        with mock.patch.object(p.storage,'Client') as client, mock.patch.object(p,'download_source_archive',side_effect=download),mock.patch.object(p,'upload_immutable',side_effect=lambda name,data,ctype:written.setdefault(name,data)):
            client.return_value.bucket.return_value=bucket
            prefix,manifest=p.assemble_bundles(payload(),b'{}')
        self.assertEqual(set(manifest['bundles']),{'05-group','10-project','20-network','30-project-iam','40-data'})
        group_zip=next(v for k,v in written.items() if k.endswith('/group.zip'))
        with zipfile.ZipFile(io.BytesIO(group_zip)) as archive:
            group_vars=json.loads(archive.read('terraform.auto.tfvars.json'))
            self.assertEqual(group_vars['customer_id'],ENV['CLOUD_IDENTITY_CUSTOMER_ID'])
            self.assertEqual(group_vars['members'],payload()['identity']['members'])
            self.assertIn('google_cloud_identity_group',archive.read('main.tf').decode())
        data_zip=next(v for k,v in written.items() if k.endswith('/data.zip'))
        with zipfile.ZipFile(io.BytesIO(data_zip)) as archive:
            variables=json.loads(archive.read('terraform.auto.tfvars.json'))
            self.assertEqual(variables['jupyter_gsa_email'],'sbx-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com')
            imports=archive.read('imports.tf').decode()
            self.assertIn('google_bigquery_dataset.sandbox',imports)
            self.assertIn('google_storage_bucket.sandbox',imports)
            self.assertNotIn('google_service_account',imports)
            self.assertFalse(variables['create_jupyter_gsa'])

    @mock.patch.dict(os.environ,ENV)
    def test_new_project_dedicated_gsa_and_parent_validation(self):
        data=json.loads((ROOT/'05.sandbox_json/sbx03-request.template.json').read_text())
        # The checked-in template must never be accepted as an approved request.
        self.assertTrue(list(p.VALIDATOR.iter_errors(data)))
        data['approval']={'status':'APPROVED','approval_id':'test-approval','approved_at':'2026-11-07T00:00:00Z'}
        data['source']['sha256']='b'*64
        p.VALIDATOR.validate(data)
        p.validate_semantics(data)
        variables=p.stage_variables(data)
        self.assertEqual(variables['10-project']['org_id'],'51654893849')
        self.assertIsNone(variables['10-project']['folder_id'])
        self.assertTrue(variables['40-data']['create_jupyter_gsa'])
        self.assertEqual(variables['40-data']['identity_project_id'],'gcp-sbx-edp-sbx03')
        self.assertEqual(variables['40-data']['jupyter_gsa_email'],'gsa-jupyter-sbx03@gcp-sbx-edp-sbx03.iam.gserviceaccount.com')
        self.assertEqual(variables['40-data']['gke_project_id'],'gcp-sbx-edp-gke01')
        self.assertEqual(variables['40-data']['datalake_datasets'],[{'project_id':'pjt-c-admin','dataset_id':'dlk_sample'}])
        data['project']['folder_id']='123'
        self.assertTrue(list(p.VALIDATOR.iter_errors(data)))
        del data['project']['folder_id'];del data['project']['org_id']
        self.assertTrue(list(p.VALIDATOR.iter_errors(data)))
        data['identity']['create_jupyter_gsa']=False
        with self.assertRaisesRegex(ValueError,'new projects require'):p.validate_semantics(data)

    @mock.patch.dict(os.environ,ENV)
    def test_old_source_cannot_silently_skip_dedicated_gsa(self):
        data=json.loads((ROOT/'05.sandbox_json/sbx03-request.template.json').read_text())
        bucket=mock.Mock();bucket.name=ENV['BUNDLE_BUCKET'];bucket.blob.side_effect=lambda name:name
        def download(source,destination):
            shutil.copytree(ROOT/'08.sandbox_setup_02_terraform',destination/'08.sandbox_setup_02_terraform')
            (destination/'08.sandbox_setup_02_terraform/deployments/40-data/main.tf').write_text('provider "google" {}')
            return destination
        with mock.patch.object(p.storage,'Client') as client, mock.patch.object(p,'download_source_archive',side_effect=download),mock.patch.object(p,'upload_immutable'):
            client.return_value.bucket.return_value=bucket
            with self.assertRaisesRegex(ValueError,'does not support dedicated'):p.assemble_bundles(data,b'{}')

    @mock.patch.dict(os.environ,ENV)
    def test_build_execution_identities_and_group_order(self):
        with mock.patch.object(p.cloudbuild_v1,'CloudBuildClient',autospec=True) as client:
            p.start_build(payload(),'gs://example/request.json','gs://example/bundle')
            self.assertEqual(client.return_value.create_build.call_args.kwargs['request'].parent, 'projects/gcp-sbx-edp-gke01/locations/asia-northeast3')
            build=client.return_value.create_build.call_args.kwargs['request'].build
        spec=json.loads(p.cloudbuild_v1.Build.to_json(build))
        self.assertEqual(spec['serviceAccount'],f"projects/{ENV['SBX_GKE_PROJECT']}/serviceAccounts/tf-manager@{ENV['SBX_GKE_PROJECT']}.iam.gserviceaccount.com")
        self.assertEqual(len(spec['steps']),2)
        self.assertNotIn('WORKSPACE_ADMIN_SUBJECT',str(spec))
        commands=spec['steps'][0]['args'][1]
        self.assertLess(commands.index('/group.zip'),commands.index('sleep 60'))
        self.assertLess(commands.index('sleep 60'),commands.index('/project.zip'))
        self.assertIn('deployments/sbxtest01-',commands)
        self.assertNotIn('sa-im-',commands)
        self.assertEqual(commands.count('tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com'),5)
        group_vars=p.stage_variables(payload())
        self.assertEqual(group_vars['10-project']['project_iam_service_account'],'tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com')
        child_config=spec['steps'][1]['args'][1]
        self.assertIn('projects/gcp-sbx-edp-gke01/serviceAccounts/tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com',child_config)
        self.assertIn('pool-sbxtest01',spec['options']['pool']['name'])

    @mock.patch.dict(os.environ,ENV)
    def test_optional_network_is_not_applied(self):
        data=json.loads((ROOT/'05.sandbox_json/sbx01-approved-request.json').read_text())
        self.assertFalse(data['network']['required'])
        self.assertFalse(data['network']['shared_vpc_join'])
        p.VALIDATOR.validate(data)
        with mock.patch.object(p.cloudbuild_v1,'CloudBuildClient',autospec=True) as client:
            p.start_build(data,'gs://example/request.json','gs://example/bundle')
        build=client.return_value.create_build.call_args.kwargs['request'].build
        text=build.steps[0].args[1]
        self.assertNotIn('/network.zip',text)
        self.assertIn('/data.zip',text)

    @mock.patch.dict(os.environ,ENV)
    def test_placeholder_release_rejected(self):
        data=payload();data['source']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'publish a new'): p.validate_semantics(data)

    def test_published_archive_matches_api_source_root_after_rename(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            (work/'bin').mkdir()
            stub=work/'bin/gcloud'
            stub.write_text('#!/bin/sh\nif [ "$1" = storage ] && [ "$2" = cp ]; then\n  cp "$3" "$SBX_TEST_ARCHIVE"\nelif [ "$1" = storage ] && [ "$2" = objects ] && [ "$3" = describe ]; then\n  printf \'1234567890123\\n\'\nelse\n  exit 2\nfi\n')
            stub.chmod(0o755)
            env=dict(os.environ,PATH=str(work/'bin')+os.pathsep+os.environ['PATH'],SBX_TEST_ARCHIVE=str(work/'source.zip'))
            subprocess.run(['bash',str(ROOT/'10.sandbox_deploy_tools/publish-sandbox-source.sh'),'test-bucket','git-test123'],
                           cwd=ROOT,env=env,check=True,capture_output=True,text=True)
            extracted=work/'extracted'
            with zipfile.ZipFile(work/'source.zip') as archive:
                paths=archive.namelist()
                self.assertTrue(paths)
                self.assertTrue(all(name.startswith('08.sandbox_setup_02_terraform/deployments/') for name in paths))
                archive.extractall(extracted)
            written={}
            bucket=mock.Mock();bucket.name=ENV['BUNDLE_BUCKET'];bucket.blob.side_effect=lambda name:name
            def source(source_config,destination):
                shutil.copytree(extracted,destination)
                return destination
            with mock.patch.dict(os.environ,ENV),mock.patch.object(p.storage,'Client') as client, mock.patch.object(p,'download_source_archive',side_effect=source),mock.patch.object(p,'upload_immutable',side_effect=lambda name,data,ctype:written.setdefault(name,data)):
                client.return_value.bucket.return_value=bucket
                _,manifest=p.assemble_bundles(payload(),b'{}')
            self.assertEqual(len(manifest['bundles']),5)

    def test_schema_reference_matches_runtime(self):
        self.assertEqual(json.loads((ROOT/'06.sandbox_json_rules/sandbox-request.schema.json').read_text()),p.SCHEMA)
        p.VALIDATOR.validate(payload())

    @mock.patch.dict(os.environ,ENV)
    def test_group_imports_are_literal_and_validate_membership_parent(self):
        data=payload()
        data['identity']['group_resource_name']='groups/group123'
        email=data['identity']['members'][0]
        data['identity']['membership_resource_names']={email:'groups/group123/memberships/member123'}
        p.VALIDATOR.validate(data)
        p.validate_semantics(data)
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            p.write_static_group_imports(work,data)
            imports=(work/'imports.tf').read_text()
            self.assertIn('to = google_cloud_identity_group.sandbox',imports)
            self.assertIn('id = "groups/group123"',imports)
            self.assertIn(f'member["{email}"]',imports)
            self.assertNotIn('var.',imports)
        data['identity']['membership_resource_names'][email]='groups/other/memberships/member123'
        with self.assertRaisesRegex(ValueError,'must belong'):p.validate_semantics(data)

    @mock.patch.dict(os.environ,ENV)
    def test_group_variables_and_reject_missing_customer_or_unapproved_import(self):
        data=payload()
        variables=p.stage_variables(data)['05-group']
        self.assertEqual(variables['customer_id'],ENV['CLOUD_IDENTITY_CUSTOMER_ID'])
        self.assertEqual(variables['members'],data['identity']['members'])
        with mock.patch.dict(os.environ,{'CLOUD_IDENTITY_CUSTOMER_ID':'__SET_CUSTOMER_ID__'}):
            with self.assertRaisesRegex(ValueError,'configure CLOUD_IDENTITY'):p.validate_semantics(data)
        data['identity']['group_resource_name']='groups/group123'
        data['identity']['membership_resource_names']={'other@sonmap.net':'groups/group123/memberships/m1'}
        with self.assertRaisesRegex(ValueError,'approved identity.members'):p.validate_semantics(data)

    def test_old_group_delegation_runner_removed(self):
        self.assertFalse((ROOT/'09.sandbox_gke_deployer/group_upsert.py').exists())
        self.assertFalse((ROOT/'10.sandbox_deploy_tools/group_upsert.py').exists())
        module=(ROOT/'08.sandbox_setup_02_terraform/deployments/05-group/main.tf').read_text()
        self.assertIn('google_cloud_identity_group_membership',module)
        self.assertIn('prevent_destroy = true',module)

    @mock.patch.dict(os.environ,ENV)
    def test_runtime_rejects_host_network_mutations(self):
        data=payload()
        data['network']['create_subnet']=False
        data['network']['shared_vpc_join']=False
        p.validate_semantics(data)
        for field in ['create_subnet','shared_vpc_join']:
            invalid=copy.deepcopy(data)
            invalid['network'][field]=True
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'managed by VPC Admin'):
                p.validate_semantics(invalid)


if __name__=='__main__': unittest.main()
