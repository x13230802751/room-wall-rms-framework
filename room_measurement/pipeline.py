# 总控入口：串联五个可替换接口，导出可核查点索引及 Word 报告。
from pathlib import Path
import json
import numpy as np
from room_walls.artifacts import empty_output,dump
from .contracts import Interfaces,serial
from .segmentation import split_room
from .openings import detect_openings
from .corners import structural_corners
from .regions import exclude_openings,select_local_region,polygon_uv,uv,xyz
from .rms import calculate_rms
from .reporting import write_report


def run(source=None,unit='m',up=(0,0,1),out='outputs/room',annotations=None,interfaces=None,room=None,write_docx=True):
    hooks=interfaces or Interfaces();output=empty_output(out);output.mkdir(parents=True,exist_ok=True)
    room=room or (hooks.split or split_room)(source,unit,up)
    annotations=annotations or {};unknown=set(annotations)-{'schema_version','source_sha256','coordinate_unit','walls'}
    if unknown:raise ValueError('Unknown annotation fields: '+str(unknown))
    if annotations and (annotations.get('schema_version')!=1 or annotations.get('source_sha256')!=room.provenance['sha256']):
        raise ValueError('Annotations require schema_version=1 and matching source_sha256')
    if annotations and annotations.get('coordinate_unit')!='m':raise ValueError('Annotation coordinate_unit must explicitly be m')
    overrides=annotations.get('walls',{});wall_ids={w['id'] for w in room.walls}
    if set(overrides)-wall_ids:raise ValueError('Annotations reference unknown wall IDs')
    structural=(hooks.corners or structural_corners)(room);rows=[]
    native=dict(room.native);text=native.pop('support_text',None)
    if text:(output/'native_supports.txt').write_text(text,encoding='utf-8')
    def save(name,result,folder):
        if result.get('status')!='ok':return serial(result)
        ids=np.asarray(result['point_indices']);p=np.asarray(result['selected_xyz_m']);signed=np.asarray(result['signed_distance_mm'])
        np.savetxt(folder/(name+'.csv'),np.c_[ids,p,signed],delimiter=',',header='original_index,x_m,y_m,z_m,signed_distance_mm',comments='',fmt=['%d']+['%.17g']*4)
        return serial({k:v for k,v in result.items() if k not in ['point_indices','selected_xyz_m','signed_distance_mm']}|{'points_file':str((folder/(name+'.csv')).relative_to(output))})
    for wall in room.walls:
        wid=wall['id'];folder=output/wid;folder.mkdir();ids=wall['support_indices'];custom=overrides.get(wid,{})
        if set(custom)-{'openings','local_corners_m'}:raise ValueError('Unknown wall annotation fields')
        openings=custom.get('openings')
        if openings is None:openings=(hooks.openings or detect_openings)(room,wall)
        for index,o in enumerate(openings):
            if o.get('status') not in ['confirmed','candidate']:raise ValueError('Opening status must be confirmed or candidate')
            poly=polygon_uv(wall,o['corners_m']);o.update(id=o.get('id',f'O{index+1:02d}'),wall_id=wid,
                width_m=float(np.ptp(poly[:,0])),height_m=float(np.ptp(poly[:,1])),center_m=xyz(wall,poly.mean(0)).tolist())
        available=exclude_openings(room,wall,ids,openings)
        measure=hooks.rms or calculate_rms
        def safe_measure(indices,corners=None):
            try:
                r=measure(room,wall,indices,corners)
                if r.get('status')=='ok':
                    from .contracts import point_ids
                    used=point_ids(room,wall,r['point_indices'])
                    if not np.isin(used,indices).all() or not np.array_equal(r['selected_xyz_m'],room.xyz_m[used]):
                        raise ValueError('RMS interface changed coordinates or introduced points')
                return r
            except ValueError as e:return dict(status='needs_review',reason=str(e))
        raw=safe_measure(ids);surface=safe_measure(available)
        structural_wall=structural.get('walls',{}).get(wid);whole=dict(status='needs_review',reason=structural.get('reason','No reliable structural corners'))
        if structural_wall and structural_wall['status']=='ok':whole=safe_measure(available,structural_wall['corners_m'])
        try:
            local=(hooks.local or select_local_region)(room,wall,available,openings)
            if 'local_corners_m' in custom:
                polygon_uv(wall,custom['local_corners_m']);local=dict(status='ok',corners_m=custom['local_corners_m'],selection_rule='External explicit ROI',coverage_fraction=None)
        except ValueError as e:local=dict(status='needs_review',reason=str(e))
        lm=safe_measure(available,local['corners_m']) if local['status']=='ok' else dict(status='needs_review',reason=local['reason'])
        np.savez_compressed(folder/'indices.npz',native_support=ids,available=available)
        rows.append(dict(wall_id=wid,n_native_support=len(ids),n_available=len(available),
            native_plane_ids=wall.get('native_plane_ids'),frame={k:wall[k] for k in ['plane_center_m','plane_normal','u','v']},
            openings=openings,local_region=local,structural_corners=None if structural_wall is None else structural_wall.get('corners_m'),
            support_rms=save('support',raw,folder),surface_rms=save('surface',surface,folder),
            whole_wall_rms=save('whole',whole,folder),local_rms=save('local',lm,folder)))
    result=serial(dict(schema_version='1.0',method='Efficient RANSAC native support + wall rules + SVD RMS',
        filter='none',recovery='none',provenance=room.provenance,native_detection=native,
        floor=room.floor,ceiling=None if room.ceiling is None else {k:v for k,v in room.ceiling.items() if k!='support_indices'},
        structural=structural,n_wall_candidates=len(rows),walls=rows,
        physical_accuracy='not_validated_without_matched_reference'))
    dump(output/'result.json',result)
    if write_docx:write_report(result,output/'report.docx')
    return result
