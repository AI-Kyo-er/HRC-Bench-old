import copy
import os
import re
import types
import unittest
from unittest.mock import patch

from experiments.interface_anchor_v4.run import variants
from experiments.model_scale_v4.backend import ConfigurableLocalModel
from experiments.model_scale_v4.run import build_records, classify, gpu_preflight
from experiments.physical.protocol import SYSTEM


class FrozenInterfaceDiagnostics(unittest.TestCase):
    def test_exact_old_inputs_and_multiple_acceptable_actions(self):
        rows, hashes = build_records()
        self.assertEqual(len(rows), 40)
        self.assertEqual(len(hashes), 2)
        for view, expected in [('single', 15), ('full_history', 4), ('public_progress_aid', 6)]:
            self.assertEqual(sum(r['reference_3b_acceptable'] for r in rows if r['view'] == view), expected)
        for row in rows:
            self.assertEqual(row['messages'][0]['content'], SYSTEM)
            for choice in row['allowed']:
                self.assertEqual(classify(row, choice, None), [])
        multi = next(r for r in rows if r['suite'] == 'multi' and r['completed_item'] == 'green')
        errors = classify(multi, 'careful_green_left', None)
        self.assertIn('already_completed_item', errors)

    def test_anchor_changes_exactly_the_example_line(self):
        modes = variants()
        self.assertEqual(len(modes), 7)
        self.assertEqual(next(v['system'] for v in modes if v['id'] == 'example_green_right'), SYSTEM)
        pattern = r'(?:示例：[^\n]+|输出格式：[^\n]+)\n'
        original_core = re.sub(pattern, '', SYSTEM)
        for variant in modes:
            self.assertEqual(re.sub(pattern, '', variant['system']), original_core)

    def test_gpu_estimate_prevents_insufficient_single_card_launch(self):
        spec = {'total_weights_bytes': 29540134000}
        with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '2'}):
            with patch('subprocess.check_output', return_value='2, GPU, 49140, 16211, 32298\n'):
                result = gpu_preflight(spec)
                self.assertEqual(result['physical_gpu'], 2)
                self.assertLess(result['required_free_mib'], result['memory_free_mib'])
            with patch('subprocess.check_output', return_value='2, GPU, 49140, 30000, 19000\n'):
                with self.assertRaisesRegex(RuntimeError, '显存不足'):
                    gpu_preflight(spec)

    def test_metadata_reports_actual_model_and_physical_gpu(self):
        # 不加载权重或CUDA，防止旧适配器visible_device=3污染新模型结果。
        model = ConfigurableLocalModel.__new__(ConfigurableLocalModel)
        model.model_id = 'Qwen/Qwen2.5-14B-Instruct'
        model.revision = 'f' * 40
        model.model_path = '/data1/example'
        model.max_new_tokens = 96
        model.model = types.SimpleNamespace(num_parameters=lambda: 14700000000, dtype='bfloat16')
        model.torch = types.SimpleNamespace(version=types.SimpleNamespace(cuda='12.4'),
            cuda=types.SimpleNamespace(get_device_name=lambda device: 'GPU2', max_memory_allocated=lambda: 30))
        with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '2'}):
            result = model.metadata()
        self.assertEqual(result['visible_device'], 2)
        self.assertEqual(result['parameter_count'], 14700000000)
        self.assertEqual(result['model_id'], model.model_id)
        self.assertFalse(result['offload'])


if __name__ == '__main__':
    unittest.main()
