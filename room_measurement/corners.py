# 墙角接口：仅在四墙闭合、顶面可靠且实测支持充分时给出结构四角和房间尺寸。
import numpy as np
from scipy.spatial import cKDTree


def structural_corners(room,max_support_gap_m=.25):
    fail=lambda reason:dict(status='needs_review',reason=reason,walls={},room_dimensions=None)
    if len(room.walls)!=4:return fail('Exactly four verified geometric candidates required for this corner implementation')
    if room.ceiling is None:return fail('No reliable ceiling plane; support bounding boxes are not structural corners')
    up=np.asarray(room.up);ref=np.eye(3)[np.argmin(abs(up))];u=np.cross(up,ref);u/=np.linalg.norm(u);v=np.cross(up,u)
    center=np.mean([w['plane_center_m'] for w in room.walls],axis=0)
    walls=sorted(room.walls,key=lambda w:np.arctan2((np.array(w['plane_center_m'])-center)@v,(np.array(w['plane_center_m'])-center)@u))
    def intersect(a,b,h):
        n=np.array([a['plane_normal'],b['plane_normal'],h['normal']]);c=np.array([a['plane_center_m'],b['plane_center_m'],h['center_m']])
        if np.linalg.cond(n)>100:raise ValueError('Unstable or nearly parallel plane intersection')
        return np.linalg.solve(n,np.einsum('ij,ij->i',n,c))
    try:
        bottom=np.array([intersect(walls[i],walls[(i+1)%4],room.floor) for i in range(4)])
        top=np.array([intersect(walls[i],walls[(i+1)%4],room.ceiling) for i in range(4)])
    except ValueError as e:return fail(str(e))
    if np.any((top-bottom)@up<1.):return fail('Invalid floor/ceiling height')
    for w in walls:
        if np.min((bottom-w['plane_center_m'])@w['plane_normal'])<-.05:return fail('Four walls do not close around a convex interior')
    output={}
    for i,w in enumerate(walls):
        corners=np.array([bottom[(i-1)%4],bottom[i],top[i],top[(i-1)%4]])
        distances=cKDTree(room.xyz_m[w['support_indices']]).query(corners)[0]
        if np.max(distances)>max_support_gap_m:
            r=fail('Structural intersection too far from measured wall support')
            r['diagnostics']=dict(wall_id=w['id'],candidate_corners_m=corners.tolist(),
                nearest_support_distance_m=distances.tolist(),max_allowed_m=max_support_gap_m)
            return r
        output[w['id']]=dict(status='ok',corners_m=corners.tolist(),nearest_support_distance_m=distances.tolist())
    edge=np.roll(bottom,-1,axis=0)-bottom;lengths=np.linalg.norm(edge,axis=1)
    angles=np.rad2deg(np.arccos(np.clip(np.sum(edge*np.roll(edge,-1,axis=0),axis=1)/(lengths*np.roll(lengths,-1)),-1,1)))
    dims=None
    if np.all(abs(angles-90)<=10):
        sides=[float((lengths[0]+lengths[2])/2),float((lengths[1]+lengths[3])/2)]
        dims=dict(status='geometric_estimate',length_m=max(sides),width_m=min(sides),height_m=float(np.mean((top-bottom)@up)),
            method='Opposite floor-edge averages and mean vertical floor-to-ceiling separation')
    return dict(status='ok',walls=output,room_dimensions=dims,bottom_corners_m=bottom.tolist(),
        note='Geometric closure passed; physical accuracy still requires independent reference')
