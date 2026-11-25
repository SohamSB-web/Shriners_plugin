"""Offline regression tests using the five force-bearing Shriners reference exports."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import ezc3d
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "Gait-lab-Vicon-to-QTM"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ROOT))
from app.services import event_service
from Py3_Utils import ProcessForceplateData
from Py3_varExtractor import extract_c3d
from Py3_GaitModules import pair_strike_to_off, compute_forceplate_valid_zone

MATCH = list(ROOT.glob("Shriners_Gait_Model*/Shriners_Gait_Model*/Data/_/2026-10-27_Foot_Model_2"))
NAMES = [f"Dynamic {n}" for n in range(4, 9)]
SIDES = dict(zip(NAMES, ["L", "R", "R", "R", "L"]))


def read(path):
    return ezc3d.c3d(str(path), extract_forceplat_data=True)


def replicate(folder):
    if not MATCH:
        pytest.skip("The recorded reference session is required")
    folder.mkdir()
    for item in MATCH[0].iterdir():
        if item.suffix in (".qtm", ".c3d") or item.name == "session.xml":
            shutil.copyfile(item, folder / item.name)


def run_labels(folder, names):
    args = [sys.executable, str(ENGINE / "auto_event_trigger.py"), "-f"]
    result = subprocess.run(args + [str(folder / (n + ".qtm")) for n in names],
                            cwd=ROOT, capture_output=True, timeout=150,
                            env={**os.environ, "PYTHONPATH": str(ROOT), "SHRINERS_NON_INTERACTIVE": "1"})
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def read_events(folder, name):
    data = event_service.load_trial_events(folder, name + ".qtm")
    assert data and not data["meta"].get("projection_error")
    return [(e["label"], e["frame"]) for e in data["events"]]


@pytest.fixture(scope="module")
def processed(tmp_path_factory):
    folder = tmp_path_factory.mktemp("optima")
    seq, par = folder / "sequential", folder / "parallel"
    for target in (seq, par):
        replicate(target)
    run_labels(seq, NAMES)
    with ThreadPoolExecutor(5) as pool:
        list(pool.map(lambda name: run_labels(par, [name]), NAMES))
    return seq, par


def check_trial(source, folder, name):
    original = read(source / (name + ".c3d"))
    path = folder / (name + ".c3d")
    copy = read(path)
    pars = original["parameters"]
    assert "EVENT" not in pars or not pars["EVENT"]["USED"]["value"][0]
    assert int(pars["FORCE_PLATFORM"]["USED"]["value"][0]) == 1
    assert int(pars["FORCE_PLATFORM"]["TYPE"]["value"][0]) == 2
    np.testing.assert_array_equal(pars["FORCE_PLATFORM"]["CHANNEL"]["value"].ravel(), np.arange(1, 7))
    hz = float(pars["ANALOG"]["RATE"]["value"][0])
    fps = float(pars["POINT"]["RATE"]["value"][0])
    assert (hz, fps) == (1200, 120)
    for key in ("analogs", "points"):
        np.testing.assert_allclose(copy["data"][key], original["data"][key], rtol=0, atol=0)
    plat = original["data"]["platform"][0]
    assert (plat["unit_force"], plat["unit_moment"], plat["unit_position"]) == ("N", "Nmm", "mm")
    # These four recorded corners define local +X along lab +Y, +Y along lab +X, +Z down.
    raw = original["data"]["analogs"][0]
    rotation = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]])
    force, moment = rotation @ raw[:3], rotation @ raw[3:]
    np.testing.assert_allclose(plat["force"], force)
    np.testing.assert_allclose(plat["moment"], moment)
    payload = ProcessForceplateData(original)["FP0"]
    np.testing.assert_allclose([payload["Force"][a] for a in "XYZ"], -force)
    np.testing.assert_allclose([payload["Moment"][a] for a in "XYZ"], -moment)
    fz = force[2]
    edges = np.flatnonzero(np.diff(np.r_[False, fz > 20, False]))
    assert len(edges) == 2
    on, off = edges
    assert 0.45 < (off-on)/hz < 0.85 and np.percentile(abs(fz[:on]), 95) < 5
    mid = (on + off) // 2
    loaded = fz > 100
    center = plat["corners"].mean(axis=1)
    positions = plat["center_of_pressure"]
    calc = np.array([-moment[1,loaded], moment[0,loaded]]) / fz[loaded] + center[:2,None]
    np.testing.assert_allclose(calc, positions[:2,loaded])
    np.testing.assert_allclose([payload["Center_of_Pressure"][a][loaded] for a in "XY"], calc)
    assert np.all(calc >= plat["corners"][:2].min(axis=1)[:,None]-2)
    assert np.all(calc <= plat["corners"][:2].max(axis=1)[:,None]+2)
    labels = pars["POINT"]["LABELS"]["value"]
    pts = original["data"]["points"][:3, :, int(mid*fps/hz)]
    distances, heights = {}, {}
    for side, full in (("L","Left"), ("R","Right")):
        indices = [labels.index(full+"_"+part) for part in ("Posterior_Calcaneus", "2nd3rd_MT_Head")]
        foot = pts[:,indices].mean(axis=1)
        distances[side] = np.linalg.norm(foot[:2]-positions[:2,mid])
        heights[side] = foot[2]
    side = min(distances, key=distances.get)
    assert side == SIDES[name] == min(heights, key=heights.get)
    ev = read_events(folder, name)
    assert len(set(ev)) == len(ev) == 8
    assert len({f for _, f in ev}) == 8
    assert sorted(ev, key=lambda p:p[1]) == ev
    fields = extract_c3d(str(path), False)
    cycles = []
    for foot in "LR":
        strikes = sorted(f for l,f in ev if l == foot+"STRIKE")
        offs = [f for l,f in ev if l == foot+"OFF" and strikes[0] < f < strikes[1]]
        assert len(strikes)==2 and len(offs)==1
        duration = (strikes[1]-strikes[0])/fps
        stance = (offs[0]-strikes[0])/(strikes[1]-strikes[0])
        assert 0.8 < duration < 1.4 and 0.48 < stance < 0.75
        cycles.append((foot,*strikes,offs[0],duration,stance))
    imported = event_service._read_c3d_event_projection(path)
    assert [(e["label"],e["frame"]) for e in imported["events"]] == ev
    for l, f in ev:
        assert f in fields["EVENTS"][l]["FrameNo"]
    errors = []
    for index, kind in ((on, "STRIKE"), (off,"OFF")):
        nearest = min((f for l,f in ev if l==side+kind),key=lambda f:abs((f-1)/fps-index/hz))
        delta = (nearest-1)/fps-index/hz
        assert abs(delta) < .06
        errors.append(delta)
    return ev, cycles, (side,on/hz,off/hz,fz.max(),*errors), fz, hz, fps


@pytest.mark.parametrize("name", NAMES)
def test_reference_trial(processed, name):
    seq, par = processed
    ev, *_ = check_trial(MATCH[0], seq, name)
    assert read_events(par,name) == ev
    assert event_service._read_c3d_event_projection(par / (name+".c3d"))["events"] == [
        {"label": label, "frame": frame} for label, frame in ev]


def test_preserve_manual_and_crop(tmp_path):
    replicate(tmp_path / "manual")
    folder = tmp_path / "manual"
    path = folder / "Dynamic 4.c3d"
    c = read(path)
    c["header"]["points"]["first_frame"] = 7190
    c.write(str(path))
    # Cross a minute boundary and represent both QTM ON aliases.
    expected = [("LON",7199),("ROFF",7201),("RON",7209),("LOFF",7210)]
    assert event_service.write_events_to_c3d(path, [(f,l) for l,f in expected], 120)
    digest = hashlib.sha256(path.read_bytes()).digest()
    run_labels(folder, ["Dynamic 4"])
    assert digest == hashlib.sha256(path.read_bytes()).digest()
    ev = read_events(folder,"Dynamic 4")
    assert ev == [("LSTRIKE",7199),("ROFF",7201),("RSTRIKE",7209),("LOFF",7210)]
    fields = extract_c3d(str(path),False)
    for label, f in ev:
        assert f-7190 in fields["EVENTS"][label]["FrameNo"]


def test_no_synthetic_off_and_mixed_rates():
    assert pair_strike_to_off([100], [], "LSTRIKE","LOFF",200,120) == []
    assert pair_strike_to_off([100], [130,150], "LSTRIKE","LOFF",200,120) == []
    def plate(hz, pos):
        force = np.zeros(1000)
        force[pos] = 30
        return {"Frequency":hz,"Force":{"Z":force}}
    assert compute_forceplate_valid_zone({"a":plate(1200,600),"b":plate(600,450)},120,0,0) == (60,90,True)

def test_existing_live_timeline_has_priority(tmp_path, monkeypatch):
    import auto_event_trigger
    from app.services import event_sync_service
    folder = tmp_path / "live"
    replicate(folder)
    path = folder / "Dynamic 4.qtm"
    def snapshot(command, **kwargs):
        assert command == "GetEventSnapshot"
        return {"measurement_path": str(path), "frame_rate": 120.0,
                "recording_start_frame": 1, "initial_frame_offset": 0, "total_frames": 400,
                "events": [{"label":"LSTRIKE","frame":200},{"label":"ROFF","frame":215}]}
    monkeypatch.setattr(event_sync_service,"event_rpc",snapshot)
    auto_event_trigger.process_trial(str(path))
    assert read_events(folder,path.stem) == [("LSTRIKE",200),("ROFF",215)]
    assert len(read(folder/"Dynamic 4.c3d")["parameters"]["EVENT"]["LABELS"]["value"]) == 2

def test_reader_during_initial_database_creation(tmp_path):
    import sqlite3
    from app.services.event_store import EventStore
    store = EventStore(tmp_path)
    store.path.parent.mkdir()
    with sqlite3.connect(store.path) as creator:
        creator.execute("BEGIN IMMEDIATE")
        creator.execute("CREATE TABLE trials(id TEXT)")
        assert store.read("Dynamic 4.qtm") is None
        creator.rollback()

def read_gcd(path):
    values = {}
    key = None
    for line in path.read_text().splitlines():
        if line.startswith("!"):
            key = line[1:]
            values[key] = []
        elif line.startswith(("$", "#")):
            key = None
        elif key and line.strip():
            values[key].append(float(line))
    return {name: np.asarray(samples) for name, samples in values.items()}


def test_calibrated_gcd_preserves_stride_and_normalizes_force(tmp_path):
    import sqlite3

    sources = list(ROOT.glob("Shriners_Gait_Model*/Shriners_Gait_Model*/Data/Claudia_123-*/Claudia_123/2026-10-18_2"))
    if not sources:
        pytest.skip("The calibrated October regression fixture is required")
    source = sources[0]
    trial = "Dynamic 8"
    for file in (trial + ".qtm", trial + ".c3d", "session.xml", "Calibration/Static_BF_Claudia.py"):
        shutil.copyfile(source / file, tmp_path / Path(file).name)
    for file in (source / "Events").glob("events.sqlite3*"):
        shutil.copyfile(file, tmp_path / file.name)
    with sqlite3.connect(tmp_path / "events.sqlite3") as db:
        row = db.execute("""SELECT r.payload FROM trials t INNER JOIN event_revisions r
                            ON r.trial_id=t.id AND r.revision=t.revision
                            WHERE lower(t.measurement_path) LIKE '%dynamic 8.qtm'""").fetchone()
    events = json.loads(row[0])["events"]
    path = tmp_path / (trial + ".c3d")
    c = read(path)
    fps = c["header"]["points"]["frame_rate"]
    assert event_service.write_events_to_c3d(path, events, fps)
    c = read(path)
    times = c["parameters"]["EVENT"]["TIMES"]["value"].copy()
    # A quarter-frame timestamp should round down once, including in GCD.
    second_left_strike = [i for i,e in enumerate(events) if e["label"]=="LSTRIKE"][1]
    times[1, second_left_strike] += .25/fps
    c.add_parameter("EVENT", "TIMES", times)
    c.write(str(path))
    result = subprocess.run(
        [sys.executable, str(ENGINE / "Py3_DynamicMain.py"), "-s", str(tmp_path / "session.xml"),
         "-f", trial + ".qtm", "--leftPlate", "FP0"],
        cwd=ROOT, capture_output=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(ROOT), "SHRINERS_NON_INTERACTIVE": "1",
             "SHRINERS_AUTO_SELECT_CYCLE": "1"},
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    gcd = read_gcd(tmp_path/"GCD"/(trial+".GCD"))
    prior = read_gcd(source/"GCD"/(trial+".GCD"))
    for side in ("Left", "Right"):
        for metric in ("StrideTime", "FootOff", "StrideLength"):
            np.testing.assert_allclose(gcd[side+metric], prior[side+metric], atol=1e-6)
    c = read(path)
    plat = c["data"]["platform"][0]
    fz = plat["force"][2]
    ratio = c["parameters"]["ANALOG"]["RATE"]["value"][0]/fps
    first = c["header"]["points"]["first_frame"]
    strikes = [e["frame"]-1-first for e in events if e["label"]=="LSTRIKE"]
    path_samples = np.linspace(*(np.asarray(strikes)*ratio),101)
    force = np.interp(path_samples,np.arange(len(fz)),fz)
    np.testing.assert_allclose(gcd["LeftGRF_Vertical"],force/(gcd["Mass"][0]*9.81),atol=5.1e-7)
    assert force.max() > 500 and np.percentile(abs(force[-12:]),90) < 5
    for axis, name in enumerate(("LeftCOPx","LeftCOPy")):
        expected = np.where(abs(fz)>=10,plat["center_of_pressure"][axis],np.nan)
        # DynamicMain applies the plate's default rounded alignment offset.
        center = plat["corners"][axis].mean()
        expected += round(center) - center
        np.testing.assert_allclose(gcd[name],np.interp(path_samples,np.arange(len(fz)),expected),atol=5.1e-6,
                                   equal_nan=True)
        assert np.isnan(gcd[name][-1])
    for joint, axes in (
        ("Hip", ("HipFlexExt","HipAbAdduct","HipRotation")),
        ("Knee", ("KneeFlexExt","KneeValgVar","KneeRotation")),
        ("Ankle", ("DorsiPlanFlex","FootAbAdduct","FootRotation")),
    ):
        power = gcd["Left"+joint+"Power"]
        components = [gcd["Left"+axis+"Power"] for axis in axes]
        assert power.size == 101 and (power.min() < 0 < power.max())
        np.testing.assert_allclose(power,np.sum(components,axis=0),atol=2.5e-6)
        for axis in axes:
            moment = gcd["Left"+axis+"Moment"]
            assert moment.size==101 and np.isfinite(moment).all() and np.ptp(moment)>0
