#!/usr/bin/env python3
"""Set the approved request's source from a reviewed release.json (local file).

Obtain release.json with gcloud storage cp, then review it before use. This does
not submit a request or claim approval; the final JSON must be approved again.
"""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('request_json'); p.add_argument('release_json'); p.add_argument('output_json')
    a=p.parse_args()
    request=json.loads(Path(a.request_json).read_text())
    release=json.loads(Path(a.release_json).read_text())
    request['source']={key:release[key] for key in ['release_id','archive_uri','generation','sha256']}
    if not request['source']['archive_uri'].startswith('gs://gcp-sbx-edp-gke01-sbxtest01-bundles/platform-releases/'):
        raise ValueError('release archive must belong to GCP_SBX_Test01 bundle bucket')
    Path(a.output_json).write_text(json.dumps(request,indent=2)+'\n')
    print('Source updated. Review and approve the output JSON before submitting it.')


if __name__=='__main__': main()
