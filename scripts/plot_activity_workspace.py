#!/usr/bin/env python3
"""由已核对的真实初态绘制新功能区几何图；这是设计图，不是Sim运行结果。"""
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
import numpy as np
from robosuite.utils.binding_utils import MjSim

from hrc_pilot.activity_workspace import object_collision_bounds
from hrc_pilot.geometry_frame_replay import replay_recorded_geometry


def main():
    root=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/task_layout_review_20261008')
    source=root/'workspace_qualification.json';qualification=json.loads(source.read_text())
    example=next(row for row in qualification['records'] if row['status']=='qualified_initial_layout_geometry')
    ep=Path('results/continuous_v2')/example['run']/'episode'
    sim=MjSim.from_xml_file(str((ep/'scene.xml').resolve()))
    with (ep/'trace.jsonl').open() as reader:state=json.loads(reader.readline())
    replay_recorded_geometry(sim.model._model,sim.data._data,state)
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    fig,ax=plt.subplots(figsize=(8,9));ax.set_aspect('equal')
    table=sim.model.geom_name2id('table_collision');center=sim.data.geom_xpos[table];half=sim.model.geom_size[table]
    ax.add_patch(Rectangle(center[:2]-half[:2],2*half[0],2*half[1],facecolor='#f3ede2',edgecolor='#9a8c78',lw=2))
    fixtures={'wooden_cabinet_1':'柜体','flat_stove_1':'炉面','wine_rack_1':'酒架'}
    for name,label in fixtures.items():
        lower,upper=object_collision_bounds(sim.model,sim.data,name)
        ax.add_patch(Rectangle(lower[:2],*(upper-lower)[:2],facecolor='#ccd1d7',edgecolor='#7c8793'))
        ax.text(*(lower[:2]+upper[:2])/2,label,ha='center',va='center',fontproperties=font)
    labels={'serving_ready':'操作准备','snack_delivery':'交付取用','drink_staging':'饮品暂放',
        'akita_black_bowl_1_personal':'碗个人区','wine_bottle_1_personal':'酒瓶个人区',
        'plate_1_personal':'盘个人区','cream_cheese_1_personal':'食品个人区'}
    layout=example['layout'];extent=np.max([shape['xy_half_extent_m'] for shape in layout['object_shapes'].values()],axis=0)
    for name,xyz in layout['zone_surface_positions'].items():
        point=np.asarray(xyz)[:2];personal=name.endswith('_personal')
        color='#8798ad' if personal else '#277ab8' if name=='serving_ready' else '#328468'
        ax.add_patch(Rectangle(point-extent,2*extent[0],2*extent[1],facecolor=color,alpha=.17,edgecolor=color))
        ax.scatter(*point,color=color,s=45,zorder=3)
        ax.annotate(labels[name],point,xytext=(0,12),textcoords='offset points',ha='center',fontproperties=font,color=color)
    ax.text(.25,.64,'人侧',ha='center',fontproperties=font)
    ax.text(0,-.68,'机器人侧',ha='center',fontproperties=font)
    ax.set(xlim=(-.58,.58),ylim=(-.73,.71),xlabel='x (m)',ylabel='y (m)')
    ax.set_title('新功能区布局：静态几何检查',fontproperties=font,pad=16)
    ax.grid(alpha=.18)
    fig.text(.5,.025,'色块是当前最大物品的碰撞包围盒；不是已执行轨迹。\n尚未验证运动路径、移动物品占用及机器人操作。',ha='center',fontproperties=font,fontsize=10)
    fig.tight_layout(rect=(0,.065,1,1))
    for suffix in ['svg','png']:fig.savefig(root/('workspace_geometry.'+suffix),dpi=180)
    plt.close(fig)
    (root/'workspace_geometry_provenance.json').write_text(json.dumps({
        'source_run':example['run'],'qualification_sha256':sha256(source.read_bytes()).hexdigest(),
        'source_xml_sha256':example['source_xml_sha256'],
        'generator_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'role':'design_geometry_figure_not_sim_execution'},ensure_ascii=False,indent=2))
    print(str(root/'workspace_geometry.svg'))


if __name__=='__main__':main()
