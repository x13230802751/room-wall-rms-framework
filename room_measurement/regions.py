# 用二维测区和确认洞口限制原始支持点，不使用厚度带、去噪或残差筛选。
import numpy as np
from scipy.ndimage import uniform_filter
from room_walls.vendor.geometry import inside_polygon
from .contracts import point_ids


def uv(wall,points):
    return (np.asarray(points)-wall['plane_center_m'])@np.array([wall['u'],wall['v']]).T


def xyz(wall,coords):
    return np.asarray(wall['plane_center_m'])+np.asarray(coords)@np.array([wall['u'],wall['v']])


def polygon_uv(wall,corners):
    corners=np.asarray(corners,dtype=float)
    if corners.shape!=(4,3) or not np.isfinite(corners).all():raise ValueError('corners_m must be finite 4 x 3 coordinates')
    if np.max(abs((corners-wall['plane_center_m'])@np.asarray(wall['plane_normal'])))>.01:
        raise ValueError('ROI corners must lie within 10 mm of the wall reference plane')
    poly=uv(wall,corners);edges=np.roll(poly,-1,axis=0)-poly
    turns=np.cross(edges,np.roll(edges,-1,axis=0))
    if not (np.all(turns>1e-10) or np.all(turns< -1e-10)):raise ValueError('ROI corners must form an ordered convex quadrilateral')
    return poly


def exclude_openings(room,wall,indices,openings):
    ids=point_ids(room,wall,indices);coords=uv(wall,room.xyz_m[ids]);keep=np.ones(len(ids),bool)
    for item in openings:
        if item.get('status')!='confirmed':continue
        keep &= ~inside_polygon(coords,polygon_uv(wall,item['corners_m']))
    return ids[keep]


def select_local_region(room,wall,indices,openings,size_m=1.,cell_m=.05,min_coverage=.8):
    ids=point_ids(room,wall,indices);coords=uv(wall,room.xyz_m[ids]);lo=coords.min(0);hi=coords.max(0)
    if np.any(hi-lo<size_m):return dict(status='needs_review',reason='Wall support smaller than requested region')
    dims=np.ceil((hi-lo)/cell_m).astype(int);counts=np.zeros(tuple(dims),int)
    grid=np.minimum(((coords-lo)/cell_m).astype(int),dims-1);np.add.at(counts,tuple(grid.T),1)
    occupied=counts>0;n=int(round(size_m/cell_m))
    integral=np.pad(occupied.astype(int),((1,0),(1,0))).cumsum(0).cumsum(1)
    sums=integral[n:,n:]-integral[:-n,n:]-integral[n:,:-n]+integral[:-n,:-n]
    if not sums.size:return dict(status='needs_review',reason='Insufficient footprint for local region')
    # Rank by area coverage only, never by low RMS.
    ordered=np.argsort(-sums.ravel(),kind='stable')
    for flat in ordered:
        i,j=np.unravel_index(flat,sums.shape);coverage=float(sums[i,j]/(n*n))
        if coverage<min_coverage:break
        a=lo+np.array([i,j])*cell_m;b=a+size_m
        if np.any(b>hi+1e-9):continue
        overlap=False
        for opening in openings:
            poly=polygon_uv(wall,opening['corners_m']);x0,x1=poly.min(0),poly.max(0)
            if np.all(np.minimum(b,x1)-np.maximum(a,x0)>0):overlap=True;break
        if overlap:continue
        corners=xyz(wall,[[a[0],a[1]],[b[0],a[1]],[b[0],b[1]],[a[0],b[1]]])
        return dict(status='ok',corners_m=corners.tolist(),size_m=size_m,coverage_fraction=coverage,
            selection_rule='Maximum occupied grid coverage; no RMS-based choice',cell_m=cell_m)
    return dict(status='needs_review',reason='No 1x1 m region meets coverage and opening-clearance rules')
