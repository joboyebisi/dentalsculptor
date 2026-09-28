import numpy as np
import trimesh

from scripts.crown_mesh_graft import graft_candidate_crown


def test_cut_and_stitch_graft_is_closed_and_contains_candidate_crown():
    baseline=trimesh.creation.icosphere(subdivisions=3,radius=1.0)
    candidate=baseline.copy(); crown=candidate.vertices[:,2]>0.35; candidate.vertices[crown,0]*=1.12
    graft,receipt=graft_candidate_crown(baseline,candidate,cut_height=0.70)
    assert len(graft.vertices)>0 and len(graft.faces)>0
    assert receipt["rootLoopVertexCount"]>2 and receipt["crownLoopVertexCount"]>2
    assert receipt["bridgeFaceCount"]==receipt["rootLoopVertexCount"]+receipt["crownLoopVertexCount"]
    assert receipt["boundaryEdgeCount"]==0
    assert receipt["nonManifoldEdgeCount"]==0
    assert graft.is_watertight
    assert graft.vertices[:,0].max()>baseline.vertices[:,0].max()


def test_graft_rejects_invalid_cut_height():
    mesh=trimesh.creation.icosphere()
    try: graft_candidate_crown(mesh,mesh,cut_height=1.0)
    except ValueError as error: assert "cut height" in str(error)
    else: raise AssertionError("invalid cut height should fail")
