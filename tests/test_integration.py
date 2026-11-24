# 验证五接口总控、非 Z 轴结构角点、洞口识别及外部数据的来源约束。
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from test_framework import fixture


class IntegrationTests(unittest.TestCase):
    def test_five_interfaces_and_saved_coordinates(self):
        from room_measurement.pipeline import run
        from room_measurement.contracts import Interfaces
        calls=[]
        def openings(room,wall):calls.append(wall['id']);return []
        with tempfile.TemporaryDirectory() as temp:
            room=fixture();result=run(out=temp,room=room,interfaces=Interfaces(openings=openings),write_docx=False)
            self.assertEqual(len(calls),4);self.assertEqual(result['structural']['status'],'ok')
            for w in result['walls']:
                for key in ['support_rms','surface_rms','whole_wall_rms','local_rms']:
                    self.assertEqual(w[key]['status'],'ok')
                    data=np.genfromtxt(Path(temp)/w[key]['points_file'],delimiter=',',names=True)
                    ids=data['original_index'].astype(int);xyz=np.c_[data['x_m'],data['y_m'],data['z_m']]
                    np.testing.assert_array_equal(xyz,room.xyz_m[ids])
                    self.assertTrue(np.isin(ids,room.walls[int(w['wall_id'][1:])-1]['support_indices']).all())
            self.assertEqual(json.loads((Path(temp)/'result.json').read_text())['filter'],'none')

    def test_annotations_require_matching_cloud_hash(self):
        from room_measurement.pipeline import run
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'source_sha256'):
                run(room=fixture(),out=temp,annotations={'schema_version':1,'source_sha256':'wrong','walls':{}},write_docx=False)

    def test_structure_with_rotated_up_axis(self):
        from room_measurement.corners import structural_corners
        room=fixture();a=.4;rot=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
        room.xyz_m=room.xyz_m@rot.T;room.up=(rot@np.array(room.up)).tolist()
        for w in room.walls:
            for key in ['plane_center_m','plane_normal','u','v']:w[key]=(rot@w[key]).tolist()
        for h in [room.floor,room.ceiling]:
            for key in ['center_m','normal']:h[key]=(rot@h[key]).tolist()
        r=structural_corners(room);self.assertEqual(r['status'],'ok');self.assertAlmostEqual(r['room_dimensions']['height_m'],2.6)

    def test_void_is_only_a_candidate(self):
        from room_measurement.openings import detect_openings
        room=fixture();w=room.walls[0];ids=w['support_indices'];p=room.xyz_m[ids]
        keep=~((p[:,1]>.8)&(p[:,1]<1.8)&(p[:,2]>.7)&(p[:,2]<1.8));w['support_indices']=ids[keep]
        found=detect_openings(room,w);self.assertGreaterEqual(len(found),1)
        self.assertTrue(all(o['status']=='candidate' and not o['excluded_from_rms'] for o in found))


if __name__=='__main__':unittest.main()
