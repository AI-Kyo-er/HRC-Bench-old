from dataclasses import replace
import json

from hrc_pilot.activity_stream import run_activity_stream
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS, ContinuousWorld
from hrc_pilot.llm_human import QwenHumanPolicy
from hrc_pilot.protocol import Action


def test_stream_keeps_world_clock_and_model_history_across_public_task_changes(tmp_path):
    scenes = [replace(CONTINUOUS_SCENARIOS[name], max_steps=2) for name in ['relay','concurrent_overlay']]
    world = ContinuousWorld(scenes[0])
    world.workspace = world
    for name in ['contact_grasps','human_contact_grasps']:
        setattr(world,name,set())
    for name in ['stable_placements','last_placement','last_grasp_role']:
        setattr(world,name,{})
    resets=[]
    original=world.reset
    world.reset=lambda seed: (resets.append(seed),original(seed))[-1]
    world.bind_output=lambda _: None
    world.finish_episode=lambda: None
    world.close=lambda: None
    world.last_observation_path=None
    world.last_wrist_observation_path=None
    class Policy:
        calls=0
        resets=0
        def reset(self):self.resets+=1
        def act(self,_):self.calls+=1;return Action('wait')
        def audit_record(self):return {'call':self.calls}
    policy=Policy()
    partner=QwenHumanPolicy(scenes[0],model_path='/tmp/unused',decision_interval_steps=1,
                           generator=lambda _:'{"intent":"observe","current_goal":"保留当前观察目标","memory_note":"记录本次观察"}')
    result=run_activity_stream(scenes,policy,partner,output=tmp_path,backend_factory=lambda _:world,
                               instructions=['first public task','second public task'])
    assert resets == [0]
    assert policy.resets == 1 and policy.calls == 4
    assert result['activities'][1]['start_time_s'] == result['activities'][0]['end_time_s']
    transitions=[json.loads(line) for line in (tmp_path/'activity_transitions.jsonl').read_text().splitlines()]
    assert all(row['physical_state_preserved'] for row in transitions)
    assert transitions[1]['goal_before'] == '保留当前观察目标'
    assert len(partner.experience_memory) == 4
