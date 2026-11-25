from pathlib import Path
import csv
import hashlib
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

out = Path(__file__).resolve().parent
root = out.parents[1]
sys.path.insert(0, str(root/"tests"))
from test_optima_reference_trials import MATCH, NAMES, check_trial, read_events

source = MATCH[0]
seq = out/"regression1/optima0/sequential"
par = out/"regression1/optima0/parallel"
nov = out/"verified/november-matched"
plots = out/"plots"
plots.mkdir(exist_ok=True)
event_rows, trial_rows, cycle_rows = [], [], []
comparison = json.loads((out/"qtm-comparison.json").read_text())
assert hashlib.sha256((nov/"Dynamic 4.c3d").read_bytes()).hexdigest() == (out/"november-manual-pre-run.sha256").read_text()
colors = {"L":"#00756d","R":"#a14f00"}
fig, axes = plt.subplots(5, 1, figsize=(10,10), sharex=True, layout="constrained")
for name, overview in zip(NAMES, axes):
    ev, cycles, stats, fz, hz, fps = check_trial(source,seq,name)
    assert ev == read_events(par,name)
    side,on,off,peak,hs_error,to_error = stats
    for source_name, events in (("October",ev),("November matched recording",read_events(nov,name))):
        saved = comparison["saved_events"].get(str(Path("Foot_Volunteer_111226")/(name+".qtm")),[]) if source_name.startswith("November") else []
        if saved:
            assert [(e["label"],e["frame"]) for e in saved] == events
        else:
            assert events == ev
        trial_rows.append([source_name,name,len(saved),len(events),side,on,off,peak,hs_error if not saved else "",to_error if not saved else ""])
        for label,frame in events:
            event_rows.append([source_name,name,label,frame,frame-1,(frame-1)/fps,"QTM saved" if saved else "marker estimate"])
        if not saved:
            for foot,s1,s2,to,period,fraction in cycles:cycle_rows.append([source_name,name,foot,s1,to,s2,period,100*fraction])
        own, ax = plt.subplots(figsize=(9.4,3.2),layout="constrained")
        for axis in ([ax,overview] if source_name=="October" else [ax]):
            axis.plot([i/hz for i in range(len(fz))],fz,c="#283447",lw=1.4)
            axis.axhline(20,color="gray",lw=.65)
            axis.axvspan(on,off,color="#b2dccf",alpha=.35)
            for label,frame in events:
                axis.axvline((frame-1)/fps,color=colors[label[0]],linestyle="-" if label.endswith("STRIKE") else "--",lw=1)
            axis.set_ylabel("Vertical GRF (N)")
            axis.set_title(name+"  |  "+side+" foot on plate",loc="left",fontsize=10)
            axis.spines[["top","right"]].set_visible(False)
        legend=[Line2D([0],[0],color=colors[x[0]],ls="-" if "strike" in x else "--",label=x) for x in ("L strike","L off","R strike","R off")]
        ax.legend(handles=legend,loc="upper left",ncol=2,fontsize=8)
        ax.set_xlabel("Recording time (s)")
        own.suptitle(source_name+"  |  "+("Saved QTM events" if saved else "Marker-derived events"))
        own.savefig(plots/(source_name.split()[0]+"-"+name.replace(" ","-")+".png"),dpi=150)
        plt.close(own)
axes[-1].set_xlabel("Recording time (s)")
fig.suptitle("October reference trials  |  Marker events and measured vertical force")
axes[0].legend(handles=legend,loc="upper left",ncol=2,fontsize=7)
fig.savefig(plots/"five-trials.png",dpi=150)
plt.close(fig)
for file,header,rows in [
    ("events.csv","session,trial,label,QTM_frame,zero_based_sample,time_seconds,source",event_rows),
    ("trial-summary.csv","session,trial,events_before,events_after,contact_side,force_on_s,force_off_s,peak_N,marker_strike_minus_on_s,marker_off_minus_off_s",trial_rows),
    ("gait-cycles.csv","session,trial,side,first_strike_frame,toe_off_frame,next_strike_frame,stride_s,stance_percent",cycle_rows)]:
    with (out/file).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.writer(stream);writer.writerow(header.split(","));writer.writerows(rows)
