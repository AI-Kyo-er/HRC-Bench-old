"""正式运行候选的逐调用随机性记录；不改变策略输入或选择动作。"""
from hashlib import sha256


def call_seed(episode_seed, call_index):
    if type(episode_seed) is not int or type(call_index) is not int or call_index < 0:
        raise ValueError('需要显式整数episode种子及非负调用索引')
    digest = sha256(f'hrc-vla-sampler-v1:{episode_seed}:{call_index}'.encode()).digest()
    return int.from_bytes(digest[:8], 'big') % (2**63 - 1)


class SeededPolicyInference:
    """包裹已加载模型；每episode独立进程，调用编号不跨episode共享。"""

    def __init__(self, policy, episode_seed, *, cuda_devices=(0,)):
        call_seed(episode_seed, 0)
        self.policy = policy
        self.episode_seed = episode_seed
        self.cuda_devices = list(cuda_devices)
        self.call_index = 0
        self.metadata = {**policy.metadata, 'sampler_protocol': 'episode_seed_and_call_index_v1',
            'episode_sampler_seed': episode_seed, 'sampler_call_index_start': 0,
            'rng_scope': 'fork_rng restores host CPU and selected CUDA random state',
            'reproducibility_scope': '记录Torch采样种子；不保证跨设备／版本逐位相同，不匹配不同闭环轨迹。'}

    def infer(self, value):
        import torch
        index = self.call_index
        seed = call_seed(self.episode_seed, index)
        self.call_index += 1
        with torch.random.fork_rng(devices=self.cuda_devices):
            # 只更新fork中已保存的CPU／指定CUDA生成器，不改其他设备。
            torch.random.default_generator.manual_seed(seed)
            for device in self.cuda_devices:
                torch.cuda.default_generators[device].manual_seed(seed)
            result = self.policy.infer(value)
        evidence = {'protocol': self.metadata['sampler_protocol'],
            'episode_seed': self.episode_seed, 'call_index': index, 'torch_seed': seed}
        # 当前journal完整保存此真实语言证据；保留原字段，不把种子放入prompt。
        return {**result, 'language_input_evidence': {
            **result.get('language_input_evidence', {}), 'sampler_randomness': evidence}}
