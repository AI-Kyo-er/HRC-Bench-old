import copy
import json
import unittest

from experiments.interface_anchor_v4.run import variants
from experiments.neutral_vl_v4.run import BASELINE, neutral_records


class NeutralVLProtocol(unittest.TestCase):
    def test_only_fixed_format_only_system_line_changes(self):
        original = json.loads(BASELINE.read_text())['records']
        neutral = neutral_records()
        expected = next(v['system'] for v in variants() if v['id'] == 'format_only')
        self.assertEqual(len(neutral), 40)
        for old, new in zip(original, neutral):
            self.assertEqual(new['messages'][0]['content'], expected)
            restored = copy.deepcopy(new)
            restored['messages'][0]['content'] = old['messages'][0]['content']
            self.assertEqual(old, restored)


if __name__ == '__main__':
    unittest.main()
