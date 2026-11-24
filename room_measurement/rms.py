# RMS 接口：对传入原始点的几何测区作 SVD，返回点索引和毫米单位结果。
import numpy as np
from room_walls.vendor.geometry import fit_plane,inside_polygon
from .contracts import point_ids
from .regions import polygon_uv,uv


def calculate_rms(room,wall,indices,corners_m=None):
    ids=point_ids(room,wall,indices)
    if corners_m is not None:
        ids=ids[inside_polygon(uv(wall,room.xyz_m[ids]),polygon_uv(wall,corners_m))]
    if len(ids)<3:raise ValueError('Measurement region has fewer than 3 support points')
    p=room.xyz_m[ids];center,normal,_=fit_plane(p)
    if normal@wall['plane_normal']<0:normal=-normal
    signed=(p-center)@normal*1000
    return dict(status='ok',rms_mm=float(np.sqrt(np.mean(signed**2))),n_selected=len(ids),
        plane_center_m=center.tolist(),plane_normal=normal.tolist(),point_indices=ids,
        selected_xyz_m=p,signed_distance_mm=signed,coordinate_unit='m',distance_unit='mm',
        corners_m=corners_m,definition='Unweighted original-coordinate orthogonal RMS about SVD best-fit plane',
        filter='none',recovery='none')
