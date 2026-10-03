"""旧动力学每tick原样推进；贡献采样记录在独立同tick日志。"""
import gzip
import json
from experiments.structure_foundation_v20.world_v1 import FoundationWorld


class StructureWorld(FoundationWorld):
    def __init__(self, seed=120, trace_path=None, service_trace_path=None):
        self.step_callback = None
        self.service_trace = None
        super().__init__(seed=seed, trace_path=trace_path)
        if service_trace_path is not None:
            self.service_trace = gzip.open(service_trace_path, 'wt')

    def public_inspection_sample(self):
        physical = self.state()
        contacts = [c for c in physical['contacts']
                    if {c['body_a'], c['body_b']} == {self.robot, self.objects['blue']}]
        return dict(tick=self.tick, inspection=physical['inspection_facts'],
                    presence=physical['presence'],
                    presence_moving=physical['presence_motion'] is not None,
                    robot_blue_contact=bool(contacts), robot_blue_contacts=contacts)

    def simulate(self, ticks):
        for _ in range(ticks):
            # 基类先写完整实际物理记录，随后贡献层使用同tick事实采样。
            super().simulate(1)
            if self.step_callback is not None:
                facts = self.public_inspection_sample()
                result = self.step_callback(facts)
                if self.service_trace is not None:
                    self.service_trace.write(json.dumps(dict(facts=facts, **result)) + '\n')

    def close(self):
        try:
            if self.service_trace is not None:
                self.service_trace.close()
        finally:
            super().close()
