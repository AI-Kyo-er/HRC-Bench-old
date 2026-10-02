"""独立VL文本基线保持既有输入/评分，元数据不能冒充视觉评测。"""
import json
import os
import types
import unittest
from unittest.mock import patch

from experiments.local_vl_v4.backend import LocalTextVL
from experiments.local_vl_v4.run import FREEZE, OLD_FREEZE, frozen_records


class LocalVLIsolation(unittest.TestCase):
    def test_same_frozen_messages_candidates_labels_and_generation(self):
        old = json.loads(OLD_FREEZE.read_text())
        new = json.loads(FREEZE.read_text())
        self.assertEqual(new['records'], old['records'])
        self.assertEqual(new['generation'], old['generation'])
        self.assertEqual(new['gate'], old['gate'])
        copy = frozen_records()
        copy[0]['messages'][0]['content'] = 'mutation'
        self.assertEqual(frozen_records(), old['records'])
        self.assertIsNone(new['model_spec']['revision'])

    def test_metadata_keeps_unknown_revision_and_text_only_identity(self):
        model = LocalTextVL.__new__(LocalTextVL)
        model.model_id = 'Qwen/Qwen2.5-VL-7B-Instruct'
        model.revision = None
        model.model_path = '/data1/local'
        model.max_new_tokens = 96
        model.model = types.SimpleNamespace(num_parameters=lambda: 8290000000, dtype='bfloat16')
        model.torch = types.SimpleNamespace(version=types.SimpleNamespace(cuda='12.4'),
            cuda=types.SimpleNamespace(get_device_name=lambda device: 'GPU2', max_memory_allocated=lambda: 1))
        with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '2'}):
            metadata = model.metadata()
        self.assertEqual(metadata['model_id'], model.model_id)
        self.assertEqual(metadata['visible_device'], 2)
        self.assertIsNone(metadata['revision'])
        self.assertFalse(metadata['image_inputs'])
        self.assertFalse(metadata['visual_capability_evaluated'])


if __name__ == '__main__':
    unittest.main()
