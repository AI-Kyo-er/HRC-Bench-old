"""保留初态的区域容纳几何资格；不执行策略或Robot、不当运动／任务成功。"""
import csv
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from robosuite.utils.binding_utils import MjSim

from hrc_pilot.geometry_frame_replay import replay_recorded_geometry
from hrc_pilot.placement_areas import table_placement_areas, area_placement


def main():
    records=[]
    for condition in csv.DictReader(Path('experiments/workspace_dynamic_20261008/conditions.csv').open()):
        root=Path('results/continuous_v2')/condition['run'];ep=root/'episode'
        sim=MjSim.from_xml_file(str((ep/'scene.xml').resolve()))
        line=(ep/'trace.jsonl').read_text().splitlines()[0];record=json.loads(line)
        frame=replay_recorded_geometry(sim.model._model,sim.data._data,record)
        layout=json.loads((root/'workspace_layout.json').read_text())
        area=table_placement_areas(layout)['snack_delivery'];plans=[]
        for obj in ['akita_black_bowl_1','plate_1','wine_bottle_1']:
            before=sim.data.qpos.copy()
            plan=area_placement(sim.model,sim.data,obj,area,list(record['objects']),
                                preferred_xy=layout['zone_surface_positions']['snack_delivery'][:2])
            np.testing.assert_array_equal(sim.data.qpos,before)
            body=sim.model.body_name2id(obj+'_main');joint=int(sim.model.body_jntadr[body])
            index=int(sim.model.jnt_qposadr[joint]);sim.data.qpos[index:index+3]=plan['body_target_xyz']
            sim.forward();mask=np.ones(len(before),dtype=bool);mask[index:index+3]=False
            np.testing.assert_array_equal(sim.data.qpos[mask],before[mask])
            plans.append(plan)
        records.append({'run':root.name,'initial_frame_replay':frame,'plans':plans,
            'scene_xml_sha256':sha256((ep/'scene.xml').read_bytes()).hexdigest(),
            'first_trace_record_sha256':sha256(line.encode()).hexdigest()})
    sources=[Path(__file__),Path('src/hrc_pilot/placement_areas.py'),
             Path('src/hrc_pilot/activity_workspace.py'),Path('src/hrc_pilot/geometry_frame_replay.py')]
    output=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/area_geometry_qualification_20261009.json')
    output.write_text(json.dumps({'scope':'CPU copied initial frames with sequential object pose probes; no policy, robot control, trajectory or success qualification',
        'source_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in sources},'records':records},ensure_ascii=False,indent=2))
    print(json.dumps({'qualified_initial_frames':len(records),'output':str(output)}))


if __name__=='__main__':main()
