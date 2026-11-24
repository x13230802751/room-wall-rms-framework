# 定义五个接口共享的米单位坐标、墙支持点和原始点编号契约。
from dataclasses import dataclass,field
from typing import Callable
import numpy as np


@dataclass
class Room:
    xyz_m: np.ndarray
    walls: list
    floor: dict
    ceiling: dict | None
    up: list
    provenance: dict
    native: dict=field(default_factory=dict)


@dataclass
class Interfaces:
    split: Callable | None=None
    openings: Callable | None=None
    corners: Callable | None=None
    local: Callable | None=None
    rms: Callable | None=None


def point_ids(room,wall,indices):
    ids=np.asarray(indices)
    if ids.ndim!=1 or not np.issubdtype(ids.dtype,np.integer) or len(ids)<3:
        raise ValueError('Require at least 3 integer original point indices')
    if ids.min()<0 or ids.max()>=len(room.xyz_m) or len(np.unique(ids))!=len(ids):
        raise ValueError('Invalid or duplicate original point indices')
    if not np.isin(ids,wall['support_indices']).all():raise ValueError('Points outside native wall support')
    if not np.isfinite(room.xyz_m[ids]).all():raise ValueError('Nonfinite measurement points')
    return ids.astype(np.int64)


def serial(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    return value
