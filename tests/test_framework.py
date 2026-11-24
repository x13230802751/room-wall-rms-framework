# 验证框架接口、原始支持点、洞口与局部测区、结构四角及失败状态。
import unittest
import numpy as np


def fixture():
    from room_measurement.contracts import Room
    points=[];walls=[]
    for i,(axis,value,length) in enumerate([(0,0,3),(1,3,4),(0,4,3),(1,0,4)]):
        u,z=np.meshgrid(np.arange(.02,length,.02),np.arange(.02,2.6,.02))
        p=np.c_[np.full(u.size,value),u.ravel(),z.ravel()] if axis==0 else np.c_[u.ravel(),np.full(u.size,value),z.ravel()]
        start=sum(len(x) for x in points);points.append(p)
        normal=np.eye(3)[axis]*(1 if value==0 else -1);basis=np.cross([0,0,1],normal)
        walls.append(dict(id=f'W{i+1:02d}',support_indices=np.arange(start,start+len(p)),
            plane_center_m=p.mean(0).tolist(),plane_normal=normal.tolist(),u=basis.tolist(),v=[0,0,1],
            coverage_grid_mm=100,warnings=[],native_plane_ids=[i]))
    return Room(np.vstack(points),walls,dict(center_m=[2,1.5,0],normal=[0,0,1]),
        dict(center_m=[2,1.5,2.6],normal=[0,0,1]),[0,0,1],{'source':'synthetic','sha256':'fixture'})


class FrameworkTests(unittest.TestCase):
    def test_raw_rms_and_original_ids(self):
        from room_measurement.rms import calculate_rms
        room=fixture();wall=room.walls[0];ids=wall['support_indices']
        r=calculate_rms(room,wall,ids)
        self.assertLess(r['rms_mm'],1e-9)
        np.testing.assert_array_equal(r['point_indices'],ids)
        with self.assertRaises(ValueError):calculate_rms(room,wall,np.r_[ids,ids[0]])
        with self.assertRaises(ValueError):calculate_rms(room,wall,[len(room.xyz_m)+1])

    def test_structural_corners_and_missing_ceiling(self):
        from room_measurement.corners import structural_corners
        room=fixture();r=structural_corners(room)
        self.assertEqual(r['status'],'ok');self.assertEqual(len(r['walls']),4)
        dims=r['room_dimensions'];self.assertAlmostEqual(dims['length_m'],4);self.assertAlmostEqual(dims['width_m'],3)
        self.assertAlmostEqual(dims['height_m'],2.6)
        room.ceiling=None;self.assertEqual(structural_corners(room)['status'],'needs_review')

    def test_local_and_opening_masks_without_residual_filter(self):
        from room_measurement.regions import select_local_region, exclude_openings
        from room_measurement.rms import calculate_rms
        room=fixture();wall=room.walls[0];ids=wall['support_indices']
        opening=dict(status='confirmed',corners_m=[[0,1,.4],[0,2,.4],[0,2,1.4],[0,1,1.4]])
        available=exclude_openings(room,wall,ids,[opening])
        p=room.xyz_m[available];self.assertFalse(np.any((p[:,1]>1)&(p[:,1]<2)&(p[:,2]>.4)&(p[:,2]<1.4)))
        local=select_local_region(room,wall,available,[opening]);self.assertEqual(local['status'],'ok')
        r=calculate_rms(room,wall,available,local['corners_m']);self.assertGreater(r['n_selected'],100)
        np.testing.assert_array_equal(room.xyz_m[r['point_indices']],r['selected_xyz_m'])
        # Geometric ROI retains a real 25 mm displacement; no distance slab.
        room.xyz_m[ids,0]=.025*np.sin(room.xyz_m[ids,1]*3)
        r=calculate_rms(room,wall,ids);self.assertGreater(r['rms_mm'],5)

    def test_bad_roi_and_no_silent_candidate_exclusion(self):
        from room_measurement.regions import exclude_openings,polygon_uv
        room=fixture();w=room.walls[0];ids=w['support_indices']
        pending={'status':'candidate','corners_m':[[0,1,0],[0,2,0],[0,2,1],[0,1,1]]}
        np.testing.assert_array_equal(exclude_openings(room,w,ids,[pending]),ids)
        with self.assertRaises(ValueError):polygon_uv(w,[[0,1,0],[0,2,1],[0,2,0],[0,1,1]])


if __name__=='__main__':unittest.main()
