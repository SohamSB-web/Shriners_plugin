"""Batched geometry, wrapping and production sampling compared with scalar formulas."""
import ast
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Gait-lab-Vicon-to-QTM'))
sys.path.insert(0,str(Path(__file__).parent/'fixtures'))
import Py3_MathModules as math
import Py3_GaitModules as gait
import legacy_dynamic_geometry as legacy
from test_dynamic_numpy import assert_same


@pytest.mark.parametrize('side',['Left','Right'])
@pytest.mark.parametrize('model',['Newington','Harrington','Harrington2'])
def test_hip_models_keep_original_regressions(side,model):
    rng=np.random.default_rng(46)
    points=rng.normal(size=(3,39,3))*100
    technical,origin=gait.TechCS_Pelvis_Newington(*points)
    def arguments(i=None):
        xyz=points if i is None else points[:,i]
        frame=technical if i is None else technical[i]
        center=origin if i is None else origin[i]
        # API order is RASIS, LASIS, SACR.
        if model=='Newington':return (side,14,220,80,800,810,xyz[1],xyz[0],frame,center)
        if model=='Harrington':return (side,220,xyz[1],xyz[0],xyz[2],frame,center)
        return (side,220,800,810,xyz[1],xyz[0],xyz[2],frame,center)
    name='JointCenterModel_Hip_'+model
    actual=getattr(gait,name)(*arguments())
    expected=[getattr(legacy,name)(*arguments(i)) for i in range(39)]
    assert_same(actual[1],[e[1] for e in expected],atol=1e-10)


@pytest.mark.parametrize('matrix_type',[np.asarray,np.matrix])
@pytest.mark.parametrize('axis',['X','Y','Z'])
def test_rotations_accept_static_and_batched_frames(matrix_type,axis):
    rng=np.random.default_rng(11)
    frames=np.linalg.qr(rng.normal(size=(39,3,3)))[0]
    angles=np.linspace(-180,180,39)
    name='RotateCSaround'+axis+'axis'
    expected=[getattr(legacy,name)(f,a) for f,a in zip(frames,angles)]
    assert_same(getattr(math,name)(frames,angles),expected)
    constant=matrix_type(frames[0])
    assert_same(getattr(math,name)(constant,angles),[getattr(legacy,name)(np.asarray(constant),a) for a in angles])
    assert_same(math.TransformAnatCoorSysFromTechCoors(matrix_type(frames[1]),frames),
                [legacy.TransformAnatCoorSysFromTechCoors(np.asarray(frames[1]),f) for f in frames])


def test_trunk_and_delp_pelvis_match_scalar_geometry():
    points=np.random.default_rng(18).normal(size=(6,39,3))*100
    points[:,0]=0
    with np.errstate(all='ignore'):
        actual=gait.TechCS_Trunk_Newington(*points)
        expected=[legacy.TechCS_Trunk_Newington(*points[:,i]) for i in range(39)]
        for j in range(3):assert_same(actual[j],[e[j] for e in expected],atol=1e-10)
        actual=gait.AnatCS_Pelvis_Delp(*points[:3],7.)
        expected=[legacy.AnatCS_Pelvis_Delp(*points[:3,i],7.) for i in range(39)]
        for j in range(2):assert_same(actual[j],[e[j] for e in expected],atol=1e-10)


def test_com_and_gyration_preserve_degenerate_nan_behavior():
    points=np.random.default_rng(22).normal(size=(2,39,3))*300
    points[:,0]=0
    points[0,1]=np.nan
    with np.errstate(all='ignore'):
        assert_same(math.MassCenter(*points,.3),[legacy.MassCenter(*points[:,i],.3) for i in range(39)],atol=1e-10)
        assert_same(math.RadiusOfGyration(*points,.3,.4,.5),[legacy.RadiusOfGyration(*points[:,i],.3,.4,.5) for i in range(39)],atol=1e-10)


@pytest.mark.parametrize('side',['Left','Right'])
@pytest.mark.parametrize('path',['ReFe','VaLa','GaMe'])
def test_wrapping_retains_attachment_thresholds_and_nan_decisions(side,path):
    rng=np.random.default_rng(35)
    count=11
    angles=np.array([-1.,44.,44.00001,68.99999,69.,82.99999,83.,109.99999,110.,180.,np.nan])
    rotations=np.linalg.qr(rng.normal(size=(5,count,3,3)))[0]
    origins=rng.normal(size=(5,count,3))*300
    points=rng.normal(size=({'ReFe':3,'VaLa':5,'GaMe':4}[path],3))*100
    segments={'ReFe':['Pelvis','Thigh','Patella'],
              'VaLa':['Thigh','Thigh','Thigh','Thigh','Patella'],
              'GaMe':['Thigh','Thigh','Shank','Calcaneus']}[path]
    mask=np.ones((count,len(points)),dtype=bool)
    if path=='ReFe':mask[:,1]=~(angles<83)
    elif path=='VaLa':mask[:,2]=~(angles<69);mask[:,3]=~(angles<110)
    else:mask[:,1]=~(angles>44)
    args=[v for pair in zip(rotations,origins) for v in pair]
    actual,lab=math.ComputeMuscleLength(side,points,segments,*args,active_points=mask)
    expected=[]
    for i in range(count):
        selected=mask[i]
        old_args=[v for pair in zip(rotations[:,i],origins[:,i]) for v in pair]
        result=legacy.ComputeMuscleLength(side,points[selected],[s for s,keep in zip(segments,selected) if keep],*old_args)
        expected.append(result[0])
        assert_same(lab[i,selected],result[1],atol=1e-10)
    assert_same(actual,expected,atol=1e-10)


@pytest.mark.parametrize('rate',[60.,100.,1000.,1200.,2000.])
@pytest.mark.parametrize('last_index',[0,4,128])
def test_production_forceplate_indices_match_original_integer_sampling(rate,last_index):
    source=(ROOT/'Gait-lab-Vicon-to-QTM/Py3_DynamicMain.py').read_text(encoding='utf8')
    assignments=[n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Assign)
                 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='FP_FrameNumber']
    context={'np':np,'_batch_frames':np.arange(3,81),'FP_FrameRate':rate,'MarkerFrameRate':120.,'FP_MaxIndex':last_index}
    exec(compile(ast.fix_missing_locations(ast.Module(body=assignments[:2],type_ignores=[])),'<production sample indices>','exec'),context)
    expected=[min(int(frame*rate/120.),last_index) for frame in range(3,81)]
    np.testing.assert_array_equal(context['FP_FrameNumber'],expected)


def test_euler_singular_and_out_of_domain_masks_are_preserved():
    eps=np.finfo(float).eps
    matrices=np.broadcast_to(np.eye(3),(7,3,3)).copy()
    matrices[:,1,2]=[1.,1-eps,1+eps,-1.,-1+eps,-1-eps,np.nan]
    with np.errstate(all='ignore'):
        actual=math.EulerAngles_YXZ(matrices,np.eye(3))
        expected=[legacy.EulerAngles_YXZ(m,np.eye(3)) for m in matrices]
    assert_same(actual,expected)
