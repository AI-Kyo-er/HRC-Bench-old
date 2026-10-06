#!/usr/bin/env python3
"""从已有VICO GLB和动作资产导出MuJoCo蒙皮；不下载、不生成替代人物。"""
import argparse
from hashlib import sha256
import json
import io
from pathlib import Path
import pickle
import struct

import numpy as np
from pygltflib import GLTF2
from scipy.spatial.transform import Rotation
from PIL import Image


def accessor(gltf, index, blob):
    item=gltf.accessors[index];view=gltf.bufferViews[item.bufferView]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[item.type]
    dtype={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[item.componentType]
    size=np.dtype(dtype).itemsize
    return np.ndarray((item.count,width),dtype=dtype,buffer=blob,
                      offset=(view.byteOffset or 0)+(item.byteOffset or 0),
                      strides=(view.byteStride or width*size,size)).copy()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/assets/virtual-community/avatars'))
    parser.add_argument('--output',type=Path,default=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/assets/native_avatar'))
    args=parser.parse_args()
    glb=args.source/'models/mixamo_Alex_Jefferson.glb';motions=args.source/'motions/motion.pkl'
    gltf=GLTF2().load(glb);blob=gltf.binary_blob();skin=gltf.skins[0];primitive=gltf.meshes[0].primitives[0]
    vertices=accessor(gltf,primitive.attributes.POSITION,blob)
    uv=accessor(gltf,primitive.attributes.TEXCOORD_0,blob)
    faces=accessor(gltf,primitive.indices,blob).reshape(-1,3).astype('<i4')
    joints=accessor(gltf,primitive.attributes.JOINTS_0,blob)
    weights=accessor(gltf,primitive.attributes.WEIGHTS_0,blob)
    if np.any(weights.sum(1)<=0):raise ValueError('人物存在无骨骼影响的顶点')
    weights=weights/weights.sum(1,keepdims=True)
    inverse=accessor(gltf,skin.inverseBindMatrices,blob).reshape(-1,4,4).transpose(0,2,1)
    bind=np.linalg.inv(inverse).astype(np.float64)
    bind_rot=bind[:,:3,:3]/np.linalg.norm(bind[:,:3,:3],axis=1)[:,None,:]
    bind_quat=Rotation.from_matrix(bind_rot).as_quat()[:,[3,0,1,2]]
    parents=np.full(len(gltf.nodes),-1,dtype=np.int32)
    for index,node in enumerate(gltf.nodes):
        for child in node.children:parents[child]=index
    translations=np.asarray([node.translation or [0,0,0] for node in gltf.nodes],dtype=float)
    rotations=Rotation.from_quat([node.rotation or [0,0,0,1] for node in gltf.nodes]).as_matrix()
    scales=np.asarray([node.scale or [1,1,1] for node in gltf.nodes],dtype=float)
    if any(node.matrix is not None for node in gltf.nodes):raise ValueError('本资产预期TRS骨骼')
    args.output.mkdir(parents=True,exist_ok=True)
    base_output=args.output
    digest=sha256(glb.read_bytes()+motions.read_bytes()+Path(__file__).read_bytes()).hexdigest()[:12]
    args.output=base_output/('vico_'+digest)
    args.output.mkdir(exist_ok=True)
    bones=[]
    for joint in range(len(skin.joints)):
        influence=np.where(joints==joint,weights,0).sum(1)
        indices=np.flatnonzero(influence>1e-8)
        if len(indices):bones.append((joint,indices,influence[indices]))
    with (args.output/'alex.skn').open('wb') as out:
        out.write(struct.pack('<4i',len(vertices),len(uv),len(faces),len(bones)))
        out.write(vertices.astype('<f4').tobytes());out.write(uv.astype('<f4').tobytes());out.write(faces.tobytes())
        for joint,indices,influence in bones:
            name=f'hrc_avatar_j{joint:02d}'.encode()
            out.write(name+b'\0'*(40-len(name)))
            out.write(bind[joint,:3,3].astype('<f4').tobytes())
            out.write(bind_quat[joint].astype('<f4').tobytes())
            out.write(struct.pack('<i',len(indices)));out.write(indices.astype('<i4').tobytes())
            out.write(influence.astype('<f4').tobytes())
    texture=gltf.textures[gltf.materials[primitive.material].pbrMetallicRoughness.baseColorTexture.index]
    image=gltf.images[texture.source];view=gltf.bufferViews[image.bufferView]
    Image.open(io.BytesIO(blob[view.byteOffset:view.byteOffset+view.byteLength])).convert('RGB').save(args.output/'alex_color.png')
    with motions.open('rb') as f:motion=pickle.load(f)
    frames={}
    for name in ['idle','walk','reach']:
        item=motion[name]
        quaternion=np.concatenate([item['rot'][:,None,:],item['joint']],axis=1)
        global_rot=Rotation.from_quat(quaternion.reshape(-1,4)[:,[1,2,3,0]]).as_matrix().reshape(-1,65,3,3)
        # Cached calibration matrices are constant bone coordinate frames;
        # some motion clips have differing cache lengths after resampling.
        basis=item['mat'][0][None]
        frames[name+'_delta']=basis.transpose(0,1,3,2)@global_rot@basis
        frames[name+'_trans']=item['trans'];frames[name+'_root_rotation']=item['rot']
    np.savez_compressed(args.output/'rig.npz',parents=parents,translations=translations,
                        rotations=rotations,scales=scales,joint_nodes=np.asarray(skin.joints),
                        bind_positions=bind[:,:3,3],bind_rotations=bind_rot,
                        vertices=vertices,joints=joints,weights=weights,**frames)
    metadata={'source_glb':str(glb),'source_motion':str(motions),
              'source_sha256':{'glb':sha256(glb.read_bytes()).hexdigest(),'motion':sha256(motions.read_bytes()).hexdigest()},
              'vertex_count':len(vertices),'face_count':len(faces),'skin_bones':len(bones),
              'joint_names':[gltf.nodes[node].name.removeprefix('mixamorig:') for node in skin.joints],
              'skin_file':'alex.skn','texture_file':'alex_color.png','rig_file':'rig.npz',
              'motion_fps':30,'interpretation':'复用既有人物/动作蒙皮资产；显示骨骼与物理接触分开，不代表完整人体动力学或动作策略学习。'}
    (args.output/'avatar.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    current=base_output/'current'
    if current.is_symlink():current.unlink()
    elif current.exists():raise ValueError('current入口必须为软链接')
    current.symlink_to(args.output)
    print(f'导出{len(vertices)}顶点、{len(faces)}面、{len(bones)}蒙皮骨骼：{args.output}')


if __name__=='__main__':main()
