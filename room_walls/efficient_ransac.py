# 在完整点云上调用原版 Efficient RANSAC，仅按墙体规则筛选支持点并提供可追溯索引。
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import numpy as np
from .vendor.geometry import fit_plane

NATIVE=Path(__file__).resolve().parents[1]/'native/bin'
PARAMETERS=dict(normal_neighbors=30,normal_estimator='PlaneDetection QUICK PCA',
    epsilon_m=.004,bitmap_epsilon_m=.03,normal_threshold=.9,min_support=500,probability=.001,
    primitive='plane only',downsampling=False,recovery=False,
    coplanar_merge_angle_deg=3,coplanar_merge_offset_m=.020)


def write_native_xyz(path,points):
    # Quantize once to the detector's native float32 precision, then use nine
    # significant digits. Formatting float64 first can double-round to a
    # different float32 value. Final RMS still uses caller's original points.
    np.savetxt(path,np.asarray(points,dtype=np.float32),fmt='%.9g')


def parse_supports(text,n_points):
    lines=text.splitlines()
    if not lines:raise ValueError('Empty native detector output')
    count=int(lines[0]);result=[];claimed=np.zeros(n_points,dtype=bool)
    if count<0 or len(lines)!=1+2*count:raise ValueError('Malformed native detector output')
    for i in range(count):
        header=lines[1+2*i].split()
        ids=np.array([int(x) for x in lines[2+2*i].split()],dtype=np.int64)
        if len(header)!=7 or len(ids)!=int(header[-1]):
            raise ValueError(f'Native support count mismatch: plane={i}, header={header}, indices={len(ids)}')
        if len(ids) and (ids.min()<0 or ids.max()>=n_points or len(np.unique(ids))!=len(ids)):
            raise ValueError('Invalid native support indices')
        if claimed[ids].any():raise ValueError('Native supports overlap')
        claimed[ids]=True;result.append(np.sort(ids))
    return result


def detect_supports(points,cfg):
    """No voxel filtering, radius filtering or point-set expansion is applied."""
    if len(points)<500:raise ValueError('Efficient RANSAC requires at least 500 finite points')
    manifest_path=NATIVE/'manifest.json'
    if not manifest_path.exists():raise ValueError('Build native programs first: python native/build.py --source-root PATH')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ['normals.exe','eransac.exe']:
        if not (NATIVE/name).exists() or sha(NATIVE/name)!=manifest['binaries'][name]:
            raise ValueError(f'Native binary absent or changed: {name}; rebuild')
    with tempfile.TemporaryDirectory(prefix='wall_er_') as tmp:
        work=Path(tmp)
        # Original C++ detector is float32; retain original float64 coordinates
        # in the caller for final SVD/RMS. Text round-trips all float32 values.
        write_native_xyz(work/'input.xyz',points)
        logs=[]
        for name,args in [('normals.exe',['input.xyz','input.xyzn']),
                          ('eransac.exe',['input.xyzn','planes.txt',str(cfg.seed)])]:
            proc=subprocess.run([str(NATIVE/name),*args],cwd=work,capture_output=True,text=True,timeout=600)
            logs.append(dict(program=name,arguments=args,returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr))
            if proc.returncode:raise ValueError(f'{name} failed ({proc.returncode}): {proc.stderr[-1500:]}')
        xyzn=np.loadtxt(work/'input.xyzn')
        if xyzn.shape!=(len(points),6) or not np.isfinite(xyzn).all():raise ValueError('Invalid native normals')
        if not np.array_equal(xyzn[:,:3].astype(np.float32),points.astype(np.float32)):
            raise ValueError('Native preprocessing changed point order or coordinates')
        text=(work/'planes.txt').read_text();supports=parse_supports(text,len(points))
        provenance=dict(parameters=PARAMETERS,seed=cfg.seed,n_detector_input=len(points),
            native_build=manifest,logs=logs,xyzn_sha256=sha(work/'input.xyzn'),
            supports_sha256=sha(work/'planes.txt'),support_text=text,
            precision='Native float32 detection; RMS uses original float64 input coordinates')
    return supports,provenance


def discover_native(points,cfg):
    from .discovery import wall_frame
    p=np.asarray(points,dtype=np.float64)
    if p.ndim!=2 or p.shape[1]!=3:raise ValueError('points must be N x 3, in meters')
    original=np.flatnonzero(np.isfinite(p).all(1));q=p[original];up=np.asarray(cfg.up)
    if len(q)<500:raise ValueError('Insufficient finite points for Efficient RANSAC')
    if np.ptp(q@up)<cfg.min_wall_height_m:raise ValueError('Cloud has insufficient height; check unit/up')
    supports,provenance=detect_supports(q,cfg)
    planes=[];degenerate=[]
    for i,ids in enumerate(supports):
        # The original library can return a tiny residual shape (M04 includes
        # one with one point). Preserve its native ID, but do not fit a plane.
        try:c,n,_=fit_plane(q[ids])
        except ValueError as e:
            degenerate.append(dict(native_plane_ids=[i],reasons=['DEGENERATE_NATIVE_SUPPORT'],n=len(ids),detail=str(e)))
            continue
        planes.append(dict(native_ids=[i],ids=ids,c=c,n=n))
    low,high=np.quantile(q@up,[.01,.99])
    horizontal=[w for w in planes if abs(w['n']@up)>=np.cos(np.deg2rad(cfg.max_floor_tilt_deg))]
    floors=[w for w in horizontal if w['c']@up<=low+.2*(high-low)]
    if not floors:raise ValueError('No reliable floor detected by Efficient RANSAC')
    floor=max(floors,key=lambda w:len(w['ids']));fn=floor['n'].copy()
    if fn@up<0:fn=-fn
    vertical=[w for w in planes if abs(w['n']@up)<=np.sin(np.deg2rad(cfg.max_wall_tilt_deg))]
    groups=[]
    # This adapter rule unions existing coplanar supports only. It never adds
    # points outside the native sets or trims a native set by residual distance.
    for w in sorted(vertical,key=lambda w:-len(w['ids'])):
        match=None
        for g in groups:
            offset=max(abs((w['c']-g['c'])@g['n']),abs((w['c']-g['c'])@w['n']))
            if abs(w['n']@g['n'])>=np.cos(np.deg2rad(3)) and offset<=.020:
                match=g;break
        if match is None:groups.append(dict(w))
        else:
            match['ids']=np.union1d(match['ids'],w['ids'])
            match['native_ids']=match['native_ids']+w['native_ids']
            match['c'],match['n'],_=fit_plane(q[match['ids']])
    walls=[];rejected=list(degenerate);center=np.median(q,axis=0)
    for w in groups:
        c=w['c'];n=w['n'].copy();s=q[w['ids']]
        if n@(center-c)<0:n=-n
        u,v=wall_frame(n,up);uv=np.c_[(s-c)@u,(s-c)@v];lo,hi=uv.min(0),uv.max(0)
        width,height=hi-lo;gap=float(np.quantile((s-floor['c'])@fn,.01));reasons=[]
        if width<cfg.min_wall_width_m:reasons.append('TOO_NARROW')
        if height<cfg.min_wall_height_m:reasons.append('TOO_SHORT')
        if width*height<cfg.min_wall_area_m2:reasons.append('TOO_SMALL')
        if abs(gap)>cfg.floor_touch_mm/1000:reasons.append('NOT_FLOOR_CONNECTED')
        if reasons:rejected.append(dict(native_plane_ids=w['native_ids'],reasons=reasons));continue
        corners=c+np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])@np.stack([u,v])
        walls.append(dict(plane_center_m=c.tolist(),plane_normal=n.tolist(),u=u.tolist(),v=v.tolist(),
            native_plane_ids=w['native_ids'],support_indices=original[np.sort(w['ids'])],
            discovery_support_count=len(w['ids']),width_m=float(width),height_m=float(height),floor_gap_m=gap,
            corners_m=corners.tolist(),coverage_grid_mm=cfg.coverage_grid_mm,mode='efficient_ransac',
            selection_definition='Exact union of retained native Efficient RANSAC plane supports on the full finite cloud; no recovery or further residual trimming',
            warnings=['CANDIDATE_REQUIRES_REVIEW','DETECTOR_SUPPORT_CAN_EXCLUDE_REAL_DEFECTS','NO_SEMANTIC_MODEL_CLUTTER_POSSIBLE']))
    if not walls:raise ValueError('No Efficient RANSAC wall candidates passed the geometric rules')
    walls.sort(key=lambda w:tuple(w['plane_center_m']))
    dominant=set(id(w) for w in sorted(walls,key=lambda w:-len(w['support_indices']))[:4])
    for i,w in enumerate(walls):w.update(id=f'W{i+1:02d}',dominant=id(w) in dominant)
    return dict(walls=walls,config=cfg.to_dict(),mode='efficient_ransac',n_input=len(p),n_invalid=len(p)-len(q),
        n_planes=len(supports),n_fittable_planes=len(planes),floor=dict(center_m=floor['c'].tolist(),normal=fn.tolist()),
        warnings=['GEOMETRIC_CANDIDATES_NOT_VERIFIED_WALL_IDENTITIES'],rejected_candidates=rejected,
        native_detection=provenance)
