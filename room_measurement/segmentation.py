# 分墙接口：完整点云交给原版 Efficient RANSAC，并保留地面、顶面及原始支持点索引。
import numpy as np
from room_walls.artifacts import load_metric_cloud,load_catalog
from room_walls.config import Config
from room_walls.discovery import discover
from room_walls.efficient_ransac import parse_supports
from room_walls.vendor.geometry import fit_plane
from .contracts import Room


def assemble(points,result,provenance,text):
    original=np.flatnonzero(np.isfinite(points).all(1));up=np.asarray(result['config']['up'])
    supports=parse_supports(text,len(original));heights=points[original]@up;low,high=np.quantile(heights,[.01,.99])
    ceilings=[]
    for i,ids in enumerate(supports):
        if len(ids)<3:continue
        try:c,n,_=fit_plane(points[original[ids]])
        except ValueError:continue
        if abs(n@up)>=np.cos(np.deg2rad(15)) and c@up>=high-.2*(high-low):
            if n@up<0:n=-n
            ceilings.append(dict(center_m=c.tolist(),normal=n.tolist(),n_support=len(ids),native_plane_id=i,
                support_indices=original[ids]))
    ceiling=max(ceilings,key=lambda x:x['n_support']) if ceilings else None
    if ceiling is not None:
        wall_area=max(w['width_m']*w['height_m'] for w in result['walls'])
        p=points[ceiling['support_indices']];c=np.asarray(ceiling['center_m']);_,_,v=np.linalg.svd(p-c,full_matrices=False)
        area=float(np.prod(np.ptp((p-c)@v[:2].T,axis=0)))
        if area<max(1.,.15*wall_area):ceiling=None
    return Room(points,result['walls'],result['floor'],ceiling,up.tolist(),provenance,result.get('native_detection',{}))


def split_room(source,unit='m',up=(0,0,1)):
    points,sha=load_metric_cloud(str(source),unit);result=discover(points,Config(up=tuple(up)))
    return assemble(points,result,dict(source=str(source),sha256=sha,input_unit=unit,coordinate_unit='m',
        n_input=len(points),index_convention='0-based original point record; not a PCD text line'),result['native_detection']['support_text'])


def from_catalog(path):
    from pathlib import Path
    points,catalog=load_catalog(path)
    if catalog['mode']!='efficient_ransac':raise ValueError('Only original Efficient RANSAC catalogs are accepted')
    support=Path(path).parent/catalog['native_detection']['saved_supports_file']
    from room_walls.artifacts import digest
    if digest(support)!=catalog['native_detection']['saved_supports_sha256']:raise ValueError('Native output hash mismatch')
    return assemble(points,catalog,dict(source=catalog['cloud_source'],sha256=catalog['cloud_payload_sha256'],
        input_unit=catalog['source_unit'],coordinate_unit='m',n_input=len(points),catalog=str(Path(path).resolve()),
        index_convention='0-based original point record; not a PCD text line'),support.read_text())
