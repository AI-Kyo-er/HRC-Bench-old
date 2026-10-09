import torch
import pytest

from hrc_pilot.seeded_policy_inference import SeededPolicyInference, call_seed


class RandomPolicy:
    metadata = {'model': 'fake_random_policy_for_cpu_rng_test'}

    def infer(self, value):
        assert set(value) == {'public_instruction'}
        return {'actions': torch.randn(7).tolist(),
                'language_input_evidence': {'actual_prompt': value['public_instruction']}}


def test_same_episode_and_call_reproduce_noise_without_modifying_input_or_host_rng():
    payload = {'public_instruction': 'open the drawer'}
    first = SeededPolicyInference(RandomPolicy(), 113, cuda_devices=())
    second = SeededPolicyInference(RandomPolicy(), 113, cuda_devices=())
    torch.manual_seed(392)
    before = torch.random.get_rng_state().clone()
    a = first.infer(payload)
    torch.randn(49)  # 其他宿主随机调用不改变独立模型流。
    b = second.infer(payload)
    assert a == b
    assert a['language_input_evidence']['actual_prompt'] == payload['public_instruction']
    assert set(payload) == {'public_instruction'}
    torch.random.set_rng_state(before)
    first.infer(payload)
    assert torch.equal(torch.random.get_rng_state(), before)


def test_call_index_and_episode_have_distinct_noise_and_are_recorded():
    a = SeededPolicyInference(RandomPolicy(), 113, cuda_devices=())
    b = SeededPolicyInference(RandomPolicy(), 114, cuda_devices=())
    first = a.infer({'public_instruction': 'same'})
    later = a.infer({'public_instruction': 'same'})
    other = b.infer({'public_instruction': 'same'})
    assert len({tuple(x['actions']) for x in [first, later, other]}) == 3
    assert first['language_input_evidence']['sampler_randomness']['call_index'] == 0
    assert later['language_input_evidence']['sampler_randomness']['call_index'] == 1
    assert other['language_input_evidence']['sampler_randomness']['episode_seed'] == 114


def test_failed_model_call_restores_host_state_and_preserves_attempt_index():
    class Broken(RandomPolicy):
        def infer(self, value):
            torch.randn(4)
            raise RuntimeError('model failure')
    wrapper = SeededPolicyInference(Broken(), 113, cuda_devices=())
    state = torch.random.get_rng_state().clone()
    with pytest.raises(RuntimeError, match='model failure'):
        wrapper.infer({'public_instruction': 'same'})
    assert torch.equal(torch.random.get_rng_state(), state)
    assert wrapper.call_index == 1  # 不自动重试或悄悄重复一个成功索引。


def test_reject_boolean_and_negative_index():
    with pytest.raises(ValueError):
        call_seed(True, 0)
    with pytest.raises(ValueError):
        call_seed(1, -1)
