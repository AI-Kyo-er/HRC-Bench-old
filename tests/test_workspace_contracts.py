from hrc_pilot.interaction_contracts import CONTRACTS
from hrc_pilot.workspace_contracts import PRIVATE_NEEDS,WORKSPACE_CONTRACTS


def test_task_results_and_private_use_are_defined_without_rewriting_original_contracts():
    assert set(WORKSPACE_CONTRACTS)==set(CONTRACTS)
    for key,contract in WORKSPACE_CONTRACTS.items():
        assert contract.activity.scene_case==CONTRACTS[key].activity.scene_case
        assert contract.activity.dependencies
        assert contract.activity.private_background==PRIVATE_NEEDS[key]
        assert contract.activity.private_background!=CONTRACTS[key].activity.private_background
        public=contract.public()
        assert 'private_background' not in public['activity']
        assert 'external_context' not in public['activity']
        assert not {'next_action','stage','schedule','score'}.intersection(public)
