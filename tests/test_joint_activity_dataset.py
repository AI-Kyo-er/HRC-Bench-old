import json

import numpy as np
from PIL import Image

from hrc_pilot.joint_activity_dataset import JointActivityDataset


def test_labels_include_only_executed_prefix_after_public_message_interrupt(tmp_path):
    ep=tmp_path/'episode';ep.mkdir()
    actions=np.arange(21,dtype=float).reshape(3,7)
    Image.fromarray(np.zeros((4,4,3),dtype=np.uint8)).save(ep/'observation_000000.png')
    Image.fromarray(np.zeros((4,4,3),dtype=np.uint8)).save(ep/'observation_000000_wrist.png')
    np.save(ep/'observation_000000_state.npy',np.zeros(8))
    np.save(ep/'observation_000000_actions.npy',actions)
    call={'step':0,'call_id':0,'executed_action_count':3,'prompt':'public request','action_source':'actual_vla_public_dialogue'}
    (ep/'model_calls.jsonl').write_text(json.dumps(call))
    (ep/'robot_control.jsonl').write_text('\n'.join(json.dumps({'model_call_id':0,'action':a.tolist()}) for a in actions[:2]))
    (ep/'human_policy_io.jsonl').write_text('{"private_intention":"do not leak"}')
    source,target,metadata=JointActivityDataset(tmp_path)[0]
    assert set(source)=={'image','wrist_image','state','prompt'}
    np.testing.assert_array_equal(target,actions[:2])
    assert metadata['truncated_by_reobservation'] and metadata['executed_block_steps']==2


def test_symlink_collection_has_distinct_sample_ids_without_pair_manifest(tmp_path):
    test_labels_include_only_executed_prefix_after_public_message_interrupt(tmp_path)
    collection=tmp_path/'collection';collection.mkdir()
    for name in ['run_a','run_b']:
        run=collection/name;run.mkdir();(run/'episode').symlink_to(tmp_path/'episode',target_is_directory=True)
    dataset=JointActivityDataset(collection)
    assert len(dataset)==2
    assert {dataset[i][2]['sample_id'] for i in range(2)}=={
        'run_a/episode/observation_000000','run_b/episode/observation_000000'}
    assert not list(collection.rglob('manifest.json'))
