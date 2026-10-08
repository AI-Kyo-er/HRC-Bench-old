from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys

import pytest

from hrc_pilot.joint_world import observable_world
from test_carried_world_observation import record, regions


@pytest.mark.parametrize('enabled',[False,True])
def test_contract_routes_explicit_version_and_records_it_without_changing_legacy(monkeypatch,tmp_path,enabled):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]/'scripts'))
    contract=importlib.import_module('run_contract_joint_activity')
    monkeypatch.setattr(contract.runtime,'observable_world',observable_world)
    argv=['run_contract_joint_activity.py','--interaction-contract','--human-complete-observation',
          '--human-relational-targets','--robot-skill-bank','--workspace-method','--output-dir',str(tmp_path)]
    if enabled:argv.append('--human-carried-observation')
    monkeypatch.setattr(sys,'argv',argv)
    current=record();before=deepcopy(current);observed=[]
    def run():
        observed.append(contract.runtime.observable_world(current,regions(),measurement_version=3))
        for filename in ['provenance.json','observation_adapter_provenance.json']:
            (tmp_path/filename).write_text(json.dumps({'source_sha256':{},'source_files_changed_during_run':[]}))
    monkeypatch.setattr(contract.agenda_runtime,'main',run)
    contract.main()
    expected_version=5 if enabled else 4
    assert observed[0]['measurement_version']==expected_version
    assert observed[0]['released_object_support_contacts']['food']==([] if enabled else ['bowl'])
    assert current==before
    for filename in ['provenance.json','observation_adapter_provenance.json']:
        provenance=json.loads((tmp_path/filename).read_text())
        assert provenance['world_measurement_version']==expected_version
        assert not provenance['source_files_changed_during_run']
        assert ('src/hrc_pilot/carried_world_observation.py' in provenance['source_sha256'])==enabled
