# 独立核对完整运行输出的原始索引、原版支持集及 RMS，导出可公开的摘要。
from pathlib import Path
import json
import hashlib
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from room_walls.artifacts import load_metric_cloud,dump
from room_walls.efficient_ransac import parse_supports


def main():
    records=[]
    expected={'M04':[1.351415697825274,1.3247150661367377,1.1105114123676154,1.4138054226069932],
              'M26':[2.413860478526333,1.262144917573085,1.1422074980850732,1.0833182527586587]}
    for room in ['M04','M26']:
        folder=ROOT/'outputs'/f'{room}_full';r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
        p,sha=load_metric_cloud(r['provenance']['source'],r['provenance']['input_unit']);assert sha==r['provenance']['sha256']
        original=np.flatnonzero(np.isfinite(p).all(1));native=parse_supports((folder/'native_supports.txt').read_text(),len(original))
        rows=[];errors=[]
        assert r['filter']=='none' and r['recovery']=='none'
        assert r['native_detection']['n_detector_input']==len(original)
        for i,w in enumerate(r['walls']):
            with np.load(folder/w['wall_id']/'indices.npz') as saved:
                ids=saved['native_support'];available=saved['available']
                exact=original[np.sort(np.concatenate([native[k] for k in w['native_plane_ids']]))]
                np.testing.assert_array_equal(ids,exact);assert np.isin(available,ids).all()
            for key in ['support_rms','surface_rms','whole_wall_rms','local_rms']:
                m=w[key]
                if m['status']!='ok':continue
                a=np.genfromtxt(folder/m['points_file'],delimiter=',',names=True,ndmin=1)
                used=a['original_index'].astype(int);xyz=np.c_[a['x_m'],a['y_m'],a['z_m']]
                np.testing.assert_array_equal(xyz,p[used]);assert np.isin(used,ids).all()
                if key=='support_rms':np.testing.assert_array_equal(used,ids)
                centered=xyz-xyz.mean(0);independent=np.sqrt(max(0,np.linalg.eigvalsh(centered.T@centered/len(xyz))[0]))*1000
                error=abs(independent-m['rms_mm']);assert error<1e-6;errors.append(error)
            assert abs(w['support_rms']['rms_mm']-expected[room][i])<1e-9
            rows.append(dict(wall=w['wall_id'],n_support=w['n_native_support'],support_rms_mm=w['support_rms']['rms_mm'],
                surface_rms_mm=w['surface_rms'].get('rms_mm'),whole_status=w['whole_wall_rms']['status'],
                local_status=w['local_rms']['status'],local_rms_mm=w['local_rms'].get('rms_mm'),
                opening_candidates=len(w['openings'])))
        records.append(dict(room=room,source_sha256=sha,n_input=len(p),n_native_input=len(original),
            n_wall_candidates=len(rows),structural_status=r['structural']['status'],structural_reason=r['structural'].get('reason'),
            exact_native_membership=True,original_coordinates_preserved=True,filter='none',recovery='none',
            max_independent_rms_difference_mm=max(errors),walls=rows,physical_accuracy_validated=False))
    dump(ROOT/'results/integration_verification.json',dict(status='passed',records=records))
    print(json.dumps(records,ensure_ascii=True))


if __name__=='__main__':main()
