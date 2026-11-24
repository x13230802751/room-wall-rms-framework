# 门窗接口：从墙面投影的连续空洞生成边线拟合候选，遮挡与真实洞口必须复核。
import numpy as np
from scipy.ndimage import label
from .regions import uv,xyz


def detect_openings(room,wall,cell_m=.05):
    coords=uv(wall,room.xyz_m[wall['support_indices']]);lo=coords.min(0);hi=coords.max(0)
    dims=np.maximum(np.ceil((hi-lo)/cell_m).astype(int),1)
    counts=np.zeros(tuple(dims),int);grid=np.minimum(((coords-lo)/cell_m).astype(int),dims-1)
    np.add.at(counts,tuple(grid.T),1);regions,n=label(counts==0)
    output=[]
    for index in range(1,n+1):
        cells=np.argwhere(regions==index);start=cells.min(0);stop=cells.max(0)+1
        a=lo+start*cell_m;b=lo+stop*cell_m;width,height=b-a
        if width<.3 or height<.4 or width>3 or height>3.5:continue
        if start[0]==0 or stop[0]>=dims[0] or stop[1]>=dims[1]:continue
        fill=len(cells)/np.prod(stop-start)
        if fill<.85:continue
        door=start[1]<=1;corners=np.array([[a[0],a[1]],[b[0],a[1]],[b[0],b[1]],[a[0],b[1]]])
        lines=[];valid=True;details=[]
        for axis,value,range_axis,range_lo,range_hi in [(1,a[1],0,a[0],b[0]),(0,b[0],1,a[1],b[1]),(1,b[1],0,a[0],b[0]),(0,a[0],1,a[1],b[1])]:
            selected=coords[(abs(coords[:,axis]-value)<=2*cell_m)&(coords[:,range_axis]>=range_lo)&(coords[:,range_axis]<=range_hi)]
            if axis==1 and value==a[1] and door:
                normal=np.array([np.asarray(wall['u'])@room.floor['normal'],np.asarray(wall['v'])@room.floor['normal']])
                offset=float((np.asarray(wall['plane_center_m'])-room.floor['center_m'])@room.floor['normal'])
                lines.append((normal,offset));details.append('floor intersection');continue
            if len(selected)<10:valid=False;break
            center=selected.mean(0);_,_,vectors=np.linalg.svd(selected-center,full_matrices=False);normal=vectors[-1]
            if abs(normal[axis])<np.cos(np.deg2rad(15)):valid=False;break
            lines.append((normal,-normal@center));details.append('PCA edge fit')
        if valid:
            try:
                corners=np.array([np.linalg.solve(np.array([lines[i][0],lines[(i-1)%4][0]]),-np.array([lines[i][1],lines[(i-1)%4][1]])) for i in range(4)])
                # Order: bottom-left, bottom-right, top-right, top-left.
            except np.linalg.LinAlgError:valid=False
        if not valid:continue
        size=np.ptp(corners,axis=0)
        output.append(dict(id=f'O{len(output)+1:02d}',wall_id=wall['id'],status='candidate',
            kind='door_candidate' if door else 'window_or_occlusion_candidate',corners_m=xyz(wall,corners).tolist(),
            center_m=xyz(wall,corners.mean(0)).tolist(),width_m=float(size[0]),height_m=float(size[1]),
            empty_fraction=float(fill),edge_sources=details,
            reason='Geometric void can be an opening, occlusion, or missing scan; needs confirmation',excluded_from_rms=False))
    return output
