#!/usr/bin/env python3
"""CPU重建已保存的真实初态，核对新功能区；不改变活跃实验或冒充运动资格。"""
from hashlib import sha256
import json
from pathlib import Path

from robosuite.utils.binding_utils import MjSim

from build_joint_progress_report import RUNS
from hrc_pilot.activity_workspace import make_table_workspace
from hrc_pilot.geometry_frame_replay import replay_recorded_geometry


def main():
    names=['contract_drink_request_symbolic_20261008','agenda_snack_detour_symbolic_20261008',
           'agenda_drawer_leave_return_symbolic_20261008']
    roots=[Path('results/continuous_v2')/name for name in names]
    for name,_,kind in RUNS:
        root=Path('results/continuous_v2')/name;path=root/'provenance.json'
        if kind!='reference' or not path.exists():continue
        provenance=json.loads(path.read_text())
        if provenance.get('init_state_id') in [2,4,5] and provenance.get('human_source')=='reference':roots.append(root)
    records=[]
    for root in roots:
        ep=root/'episode';xml=ep/'scene.xml'
        with (ep/'trace.jsonl').open() as source:line=source.readline()
        row=json.loads(line);sim=MjSim.from_xml_file(str(xml.resolve()))
        frame=replay_recorded_geometry(sim.model._model,sim.data._data,row)
        movable=[name for name in row['objects'] if name in
                 ['akita_black_bowl_1','cream_cheese_1','wine_bottle_1','plate_1']]
        fixtures=[name for name in row['objects'] if name not in movable]
        record={'run':root.name,'geometry_frame':frame,
            'source_xml_sha256':sha256(xml.read_bytes()).hexdigest(),
            'first_trace_record_sha256':sha256(line.rstrip('\n').encode()).hexdigest()}
        try:record.update(status='qualified_initial_layout_geometry',
                          layout=make_table_workspace(sim.model,sim.data,movable,fixtures))
        except ValueError as error:record.update(status='rejected_initial_layout_geometry',reason=str(error))
        records.append(record)
    output=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/task_layout_review_20261008/workspace_qualification.json')
    output.parent.mkdir(exist_ok=True)
    sources=[Path(__file__),Path('src/hrc_pilot/activity_workspace.py'),
             Path('src/hrc_pilot/geometry_frame_replay.py'),Path('src/hrc_pilot/human_relation_targets.py')]
    result={'role':'initial_geometry_qualification_not_runtime_or_robot_action_test',
        'source_sha256':{str(path):sha256(path.read_bytes()).hexdigest() for path in sources},'records':records}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'roots':len(records),'qualified':sum(row['status']=='qualified_initial_layout_geometry' for row in records),
        'rejected':[{'run':row['run'],'reason':row.get('reason')} for row in records if row['status']!='qualified_initial_layout_geometry'],
        'output':str(output)},ensure_ascii=False))


if __name__=='__main__':main()
