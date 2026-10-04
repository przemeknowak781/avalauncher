"""Leave-one-event-out for the "las_porywanie" variant, same rule as loo_calib.py (round 1), reported next to it.

Input:  data/avaframe/calib_results_las.csv, calib_results_las_best.json (score_multi_las.py),
        data/avaframe/calib_loo.json (round 1, for comparison), web/data/calibration.json (round-1 summary)
Output: data/avaframe/calib_loo_las.json (loo, summary, plot: the simNames export_board_multi.py --runs runs_las reads)
        web/data/calibration.json: adds only the top-level key "variants" = {"bez_lasu", "las_porywanie"};
        every existing key is left as it is (checked before writing). Round-1 files are not touched.

Rule (pre-registered, identical to round 1): setting = one friction model with its parameters, the same on every event;
thickness 1.2 m where unknown, the measured 2.7 m at Eiskar; for each held-out event the setting with the smallest mean
|runout error| on the other four is applied to it unchanged; settings with any run that touched the domain edge or hit
tEnd are not candidates. Sensitivity variants as in round 1 (thickness chosen on the training events; thickness fitted
per event, optimistic). Cross-check: loo_calib.main() pointed at the las CSV (outputs to a scratch dir) gives the same
held-out settings and errors.
"""

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from loo_calib import EV, MEASURED, RULE_TH, clean, fr_key, fr_pl

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "avaframe" / "calib_results_las.csv"
BEST = ROOT / "data" / "avaframe" / "calib_results_las_best.json"
R1 = ROOT / "data" / "avaframe" / "calib_loo.json"
OUT = ROOT / "data" / "avaframe" / "calib_loo_las.json"
WEB = ROOT / "web" / "data" / "calibration.json"
NEAR_M = 100  # "within 100 m" share
NAME = {"avaPopeletzbach": "Popeletzbach", "avaKleinerOetscherbach": "Kleiner Ötscherbach", "avaEiskar": "Eiskar",
        "avaFilisur1": "Filisur 1", "avaFilisur2": "Filisur 2"}
DS = "OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552)"
NO_ENT = "brak obszarów porywania w danych zdarzenia: bez porywania, jak w wariancie bez lasu"
INPUTS_PL = {  # what the event data give and how it was used; counts checked against the dataset files
    "avaPopeletzbach": dict(
        forest="las z danych zdarzenia: forest20090407.shp (drzewa ≥ 10 m), 11 poligonów, kopia bez zmian",
        entrainment=NO_ENT, ent_th_m=None, ent_th_source=None,
        source=f"{DS}, avaPopeletzbach/forest20090407.shp"),
    "avaKleinerOetscherbach": dict(
        forest="las z danych zdarzenia: forest20090225.shp (drzewa ≥ 10 m), 15 poligonów, kopia bez zmian",
        entrainment=NO_ENT, ent_th_m=None, ent_th_source=None,
        source=f"{DS}, avaKleinerOetscherbach/forest20090225.shp"),
    "avaEiskar": dict(
        forest="obszary oporu z danych zdarzenia: resistanceEvent20190115.gpkg, 4 poligony, ta sama geometria w .shp",
        entrainment="obszary porywania z danych zdarzenia: entrainmentEvent20190115.gpkg, 3 poligony",
        ent_th_m=0.3,
        ent_th_source=("0,3 m to wartość domyślna AvaFrame 2.1 (entThIfMissingInShp): plik nie ma atrybutu "
                       "grubości, a raport WLV jej nie podaje"),
        source=f"{DS}, avaEiskar/resistanceEvent20190115.gpkg, entrainmentEvent20190115.gpkg"),
    "avaFilisur1": dict(
        forest=("las z danych zdarzenia: avaFilisur1_forest_area.gpkg, 14 poligonów, ta sama geometria w .shp "
                "(klasy gęsty/rzadki model domyślny nie rozróżnia)"),
        entrainment=NO_ENT, ent_th_m=None, ent_th_source=None,
        source=f"{DS}, avaFilisur1/avaFilisur1_forest_area.gpkg"),
    "avaFilisur2": dict(
        forest=("las z danych zdarzenia: avaFiisur2_forest_area.gpkg (literówka w nazwie pliku zbioru), 11 "
                "stykających się poligonów scalonych w 4 rozłączne części, ta sama powierzchnia (31 205,6 m², "
                "różnica symetryczna 0 m²); AvaFrame odrzuca stykające się obiekty. To nie jest warstwa pochodna"),
        entrainment=NO_ENT, ent_th_m=None, ent_th_source=None,
        source=f"{DS}, avaFilisur2/avaFiisur2_forest_area.gpkg; scalenie: tools/calibration/events/avaFilisur2/forest_las.py"),
}
PARAMS_PL = ("parametry lasu i porywania domyślne (AvaFrame 2.1), niestrojone: model oporu domyślny, cResH 0,01, "
             "detrainment włączony, detK 5, forestVMin 6, forestVMax 40, forestThMin 0,6, forestThMax 10; "
             "rhoEnt 100, entEroEnergy 5000")


def pl(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def near(errs_abs):
    n = int(sum(e <= NEAR_M for e in errs_abs))
    return {"threshold_m": NEAR_M, "n": n, "of": len(errs_abs), "share": round(n / len(errs_abs), 2)}


def main():
    d = pd.read_csv(CSV)
    d["fr"] = d.apply(fr_key, axis=1)
    bad = set(d[d.touches_edge | (d.stopped_by_tEnd.astype(str) == "True")].fr)

    def run(fr, th, ev):
        t = MEASURED.get(ev, RULE_TH if fr.startswith("Voellmy") else th)
        r = d[(d.event == ev) & (d.fr == fr) & np.isclose(d.relTh, t)]
        assert len(r) == 1, (fr, th, ev, len(r))
        return r.iloc[0]

    def run_fitted(fr, ev):
        if ev in MEASURED or fr.startswith("Voellmy"):
            return run(fr, RULE_TH, ev)
        r = d[(d.event == ev) & (d.fr == fr) & (d.relTh_source == "grid")]
        return r.loc[r.runout_error_m.abs().idxmin()]

    frs = [f for f in sorted(d.fr.unique()) if f not in bad]
    fixed = [(f, RULE_TH) for f in frs]
    with_th = [(f, RULE_TH) for f in frs if f.startswith("Voellmy")] + [
        (f, float(t)) for f in frs if not f.startswith("Voellmy")
        for t in sorted(d[(d.fr == f) & (d.relTh_source == "grid")].relTh.unique())]

    def mae(fn, evs):
        return float(np.mean([abs(fn(e).runout_error_m) for e in evs]))

    def loo(cands, fn):
        out = {}
        for h in EV:
            train = [e for e in EV if e != h]
            scores = {c: mae(lambda e, c=c: fn(c, e), train) for c in cands}
            c = min(scores, key=lambda k: (scores[k], k))
            out[h] = dict(setting=c, train=scores[c], row=fn(c, h))
        return out

    main_loo = loo(fixed, lambda c, e: run(c[0], c[1], e))
    var_th = loo(with_th, lambda c, e: run(c[0], c[1], e))
    var_fit = loo(frs, lambda c, e: run_fitted(c, e))
    glob = {c: mae(lambda e, c=c: run(c[0], c[1], e), EV) for c in fixed}
    gbest = min(glob, key=glob.get)

    def errs(res):
        return [abs(float(res[h]["row"].runout_error_m)) for h in EV]

    r1 = json.loads(R1.read_text(encoding="utf-8"))
    r1_loo, r1_sum = r1["loo"], r1["summary"]
    held = {}
    for h in EV:
        x, r = main_loo[h], main_loo[h]["row"]
        fr = x["setting"][0]
        metric = "iou" if r.obs_type == "event_area" else "dep_hit"
        held[h] = {
            "setting": fr, "setting_pl": fr_pl(fr), "relTh": clean(r.relTh),
            "relTh_source": "zmierzona 2,7 m" if h in MEASURED else "reguła: 1,2 m (grubość nieznana)",
            "train_mean_abs_runout_error_m": round(x["train"], 1),
            "runout_error_m": clean(r.runout_error_m), "iou": clean(r.iou), "dep_hit": clean(r.dep_hit),
            "simType": r.simType, "res_input": r.res_input, "ent_input": r.ent_input, "ent_th_m": clean(r.ent_th_m),
            "simName": r.simName, "group": r.group,
            "round1": {"setting": r1_loo[h]["setting"], "runout_error_m": r1_loo[h]["runout_error_m"]},
            # same fields as the round-1 loo block (board_multi.py reads them)
            "frictModel": r.frictModel, "mu": clean(r.mu), "xsi": clean(r.xsi),
            "overlap_metric": metric, "iou_or_overlap": round(float(r[metric]), 3),
        }
    e_main = errs(main_loo)
    e_r1 = [abs(float(r1_loo[h]["runout_error_m"])) for h in EV]
    summary = {
        "variant": "las_porywanie",
        "design": ("pre-registered: same 5 events, friction grid and thickness rule as round 1; forest/resistance and "
                   "entrainment polygons from the event data switched on (res; entres on Eiskar); resistance and "
                   "entrainment parameters at AvaFrame 2.1 defaults"),
        "n_runs": int(len(d)), "candidates": len(fixed), "excluded_settings": sorted(bad),
        "mean_abs_runout_error_loo_m": round(float(np.mean(e_main)), 1),
        "median_abs_runout_error_loo_m": round(float(np.median(e_main)), 1),
        "runout_error_loo_m": {h: clean(main_loo[h]["row"].runout_error_m) for h in EV},
        "round1": {"mean_abs_runout_error_loo_m": r1_sum["mean_abs_runout_error_loo_m"],
                   "median_abs_runout_error_loo_m": r1_sum["median_abs_runout_error_loo_m"],
                   "runout_error_loo_m": {h: r1_loo[h]["runout_error_m"] for h in EV}},
        "best_global_setting": {
            "setting": gbest[0], "setting_pl": fr_pl(gbest[0]), "mean_abs_runout_error_m": round(glob[gbest], 1),
            "runout_error_m": {e: clean(run(gbest[0], gbest[1], e).runout_error_m) for e in EV},
            "note": "wybrane na wszystkich 5 zdarzeniach (w próbie), więc to nie jest wynik walidacji",
            "round1": r1_sum["best_global_setting"]["setting"],
            "round1_mean_abs_runout_error_m": r1_sum["best_global_setting"]["mean_abs_runout_error_m"],
        },
        "variants": {
            "thickness_chosen_on_training_events": {
                "mean_abs_runout_error_loo_m": round(float(np.mean(errs(var_th))), 1),
                "median_abs_runout_error_loo_m": round(float(np.median(errs(var_th))), 1),
                "held_out": {h: {"setting": var_th[h]["setting"][0], "relTh": clean(var_th[h]["row"].relTh),
                                 "runout_error_m": clean(var_th[h]["row"].runout_error_m)} for h in EV},
                "round1_mean": r1_sum["variants"]["thickness_chosen_on_training_events"]["mean_abs_runout_error_loo_m"],
            },
            "thickness_fitted_per_event_optimistic": {
                "mean_abs_runout_error_loo_m": round(float(np.mean(errs(var_fit))), 1),
                "median_abs_runout_error_loo_m": round(float(np.median(errs(var_fit))), 1),
                "held_out": {h: {"setting": var_fit[h]["setting"], "relTh": clean(var_fit[h]["row"].relTh),
                                 "runout_error_m": clean(var_fit[h]["row"].runout_error_m)} for h in EV},
                "round1_mean": r1_sum["variants"]["thickness_fitted_per_event_optimistic"]["mean_abs_runout_error_loo_m"],
            },
        },
        "within_100m": near(e_main),
        "loo_same_setting_as_global": sum(1 for h in EV if main_loo[h]["setting"] == gbest),
    }
    summary["round1"]["within_100m"] = near(e_r1)
    best = json.loads(BEST.read_text(encoding="utf-8"))["best"]
    plot = {e: {"best": best[e]["simName"], "best_group": best[e]["group"],
                "loo": held[e]["simName"], "loo_group": held[e]["group"]} for e in EV}
    OUT.write_text(json.dumps({"loo": held, "summary": summary, "plot": plot}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    write_web(held, summary, best, d)
    print("excluded", sorted(bad))
    print("global", gbest[0], round(glob[gbest], 1))
    for h in EV:
        x = held[h]
        print(f"{h:24s} {x['setting']:28s} train {x['train_mean_abs_runout_error_m']:6.1f}  "
              f"held {x['runout_error_m']:+7.1f}   (round 1: {x['round1']['setting']:28s} {x['round1']['runout_error_m']:+7.1f})")
    print("LOO mean", summary["mean_abs_runout_error_loo_m"], "median", summary["median_abs_runout_error_loo_m"],
          "| round 1", summary["round1"]["mean_abs_runout_error_loo_m"], summary["round1"]["median_abs_runout_error_loo_m"])
    print("within 100 m", summary["within_100m"], "| round 1", summary["round1"]["within_100m"])
    print("variants", {k: (v["mean_abs_runout_error_loo_m"], v["round1_mean"]) for k, v in summary["variants"].items()})


def write_web(held, S, best, d):
    """Add the top-level key "variants" to web/data/calibration.json; every other key stays byte-for-byte the same."""
    raw = WEB.read_text(encoding="utf-8")
    doc = json.loads(raw)
    if "variants" not in doc:  # same serialisation as loo_calib.py, so the existing keys keep their bytes
        assert json.dumps(doc, ensure_ascii=False, indent=1) == raw, "calibration.json not in loo_calib.py format"
    old = {k: copy.deepcopy(v) for k, v in doc.items() if k != "variants"}
    r1s, r1l = doc["summary"], doc["loo"]
    r1_err = {h: r1l[h]["runout_error_m"] for h in EV}
    bez = copy.deepcopy(r1s)
    bez.update({"label_pl": "bez lasu i porywania śniegu", "runout_error_loo_m": r1_err,
                "within_100m": near([abs(v) for v in r1_err.values()]),
                "source": "kopia klucza summary (loo_calib.py, data/avaframe/calib_results.csv)"})
    g = S["best_global_setting"]
    m, m1 = S["mean_abs_runout_error_loo_m"], r1s["mean_abs_runout_error_loo_m"]
    md, md1 = S["median_abs_runout_error_loo_m"], r1s["median_abs_runout_error_loo_m"]
    n, n1 = S["within_100m"]["n"], bez["within_100m"]["n"]
    pick = sum(1 for h in EV if held[h]["setting"] == g["setting"])
    fil = [held[h]["runout_error_m"] for h in ("avaFilisur1", "avaFilisur2")]
    sentence = (
        f"Z lasem i porywaniem śniegu z danych zdarzeń (parametry lasu i porywania domyślne, niestrojone) test "
        f"leave-one-out daje średni błąd zasięgu {pl(m)} m (bez lasu {pl(m1)} m) i medianę {md:.0f} m (bez lasu "
        f"{md1:.0f} m); w granicach {NEAR_M} m mieści się {n} z {len(EV)} zdarzeń (bez lasu {n1} z {len(EV)}). "
        f"Las poprawia dopasowanie w próbie, więc trening w {pick} z {len(EV)} prób wybiera {g['setting_pl']}, "
        f"a to ustawienie przestrzeliwuje oba zdarzenia Filisur o {min(fil):.0f}–{max(fil):.0f} m. "
        f"To przykładowa kalibracja na zdarzeniach z Austrii i Szwajcarii, nie dla Tatr.")
    loo_pl = {h: {k: held[h][k] for k in ("setting", "setting_pl", "frictModel", "mu", "xsi", "relTh", "relTh_source",
                                          "train_mean_abs_runout_error_m", "runout_error_m", "overlap_metric",
                                          "iou_or_overlap", "iou", "dep_hit", "simType", "simName", "group")}
              | {"round1_setting": held[h]["round1"]["setting"],
                 "round1_runout_error_m": held[h]["round1"]["runout_error_m"]} for h in EV}
    best_pl = {h: {k: clean(best[h].get(k)) for k in ("frictModel", "mu", "xsi", "relTh", "relTh_source", "iou",
                                                       "dep_hit", "runout_error_m", "simName", "group")} for h in EV}
    pr = d.groupby("event").particles_removed.median()
    las = {
        "label_pl": "z lasem i porywaniem śniegu (z danych zdarzeń)",
        "design_pl": ("zaplanowane przed wynikami: te same 5 zdarzeń, ta sama siatka tarcia i reguła grubości co bez "
                      "lasu; włączone poligony lasu/oporu i porywania, które dają dane zdarzeń (AvaFrame simType res, "
                      "na Eiskar entres); żadna warstwa nie jest pochodna"),
        "params_pl": PARAMS_PL,
        "n_runs": S["n_runs"], "candidates": S["candidates"], "excluded_settings": S["excluded_settings"],
        "inputs": {h: {"name": NAME[h], "simType": held[h]["simType"], **INPUTS_PL[h]} for h in EV},
        "loo": loo_pl,
        "runout_error_loo_m": S["runout_error_loo_m"],
        "mean_abs_runout_error_loo_m": m, "median_abs_runout_error_loo_m": md,
        "within_100m": S["within_100m"],
        "loo_same_setting_as_global": S["loo_same_setting_as_global"],
        "best_global_setting": {k: g[k] for k in ("setting", "setting_pl", "mean_abs_runout_error_m",
                                                  "runout_error_m", "note")},
        "best_per_event": best_pl,
        "thickness_variants": {k: {kk: v[kk] for kk in ("mean_abs_runout_error_loo_m", "median_abs_runout_error_loo_m")}
                               for k, v in S["variants"].items()},
        "thickness_variants_note": ("oba warianty grubości dają to samo co reguła: każdy wybór w teście to Voellmy "
                                    "(liczony tylko przy 1,2 m) albo Eiskar przy zmierzonych 2,7 m"),
        "caveats": [
            PARAMS_PL,
            "grubość odrywu zmierzono tylko na Eiskar; dla pozostałych 4 zdarzeń przyjęto 1,2 m",
            "porywanie śniegu jest w danych tylko dla Eiskar, i to bez grubości: użyto domyślnych 0,3 m",
            f"na Kleiner Ötscherbach com1DFA usuwa w medianie {pr['avaKleinerOetscherbach']:.0f} cząstek na przebieg: "
            "to śnieg zatrzymany w lesie (cząstki bez masy po detrainmencie), nie lawina wychodząca poza obszar; "
            "żaden zasięg nie dotyka brzegu obszaru",
            "teren jest nowszy niż każde zdarzenie",
            "samosAT to kalibracja dla suchego śniegu, tu użyta też do lawin mokrych",
            "to przykładowa kalibracja na zdarzeniach z Austrii i Szwajcarii, nie dla Tatr",
        ],
        "source": ("data/avaframe/calib_results_las.csv (234 wiersze), calib_results_las_best.json, calib_loo_las.json; "
                   "tools/calibration/run_multi_las.py, run_calib_las.py, score_multi_las.py, loo_calib_las.py"),
        "sentence_pl": sentence,
    }
    doc["variants"] = {"bez_lasu": bez, "las_porywanie": las}
    for k, v in old.items():  # nothing that was there changes
        assert doc[k] == v, k
    new = json.dumps(doc, ensure_ascii=False, indent=1)
    assert json.loads(new) == doc
    WEB.write_text(new, encoding="utf-8")
    print(sentence)


if __name__ == "__main__":
    main()
