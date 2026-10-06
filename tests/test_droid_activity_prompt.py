from dataclasses import replace

import numpy as np

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS, ContinuousWorld
from hrc_pilot.openpi_adapter import DroidVLAAdapter
from hrc_pilot.protocol import Message


def test_activity_announcement_invalidates_old_chunk_and_scopes_public_dialogue():
    world = ContinuousWorld(CONTINUOUS_SCENARIOS['relay'])
    world.say(Message('human', 'policy_message', '旧活动：把蓝色送到旧区域。'))
    requests = []
    def infer(request):
        requests.append(request)
        return {'actions': np.zeros((15, 8))}
    adapter = DroidVLAAdapter(infer, instruction='Current instruction.', execution_horizon=4)
    def observation(time_s):
        return replace(world.observe(), time_s=time_s, robot_qpos=tuple([0.] * 7 + [.04, .04]),
                       rgb=np.zeros((4, 4, 3), np.uint8), wrist_rgb=np.ones((4, 4, 3), np.uint8))
    adapter.act(observation(0))
    world.say(Message('environment', 'activity_change', '现在改为绿色留用。'))
    world.say(Message('human', 'policy_message', '新活动：我处理绿色。'))
    adapter.act(observation(1/15))
    assert len(requests) == 2
    assert '现在改为绿色留用' in requests[-1]['prompt']
    assert '新活动：我处理绿色' in requests[-1]['prompt']
    assert '旧活动' not in requests[-1]['prompt']
    assert adapter.calls == 2
