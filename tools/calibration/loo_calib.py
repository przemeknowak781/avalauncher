"""Leave-one-event-out validation of the 5-event AvaFrame calibration grid + web/data/calibration.json.

Input:  data/avaframe/calib_results.csv (score_multi.py on the Spark, 234 com1DFA runs, 5 observed events)
        data/avaframe/calib_results_best.json (per-event best row and its selection rule)
Output: web/data/calibration.json  (existing Popeletzbach keys kept as they are; adds "events", "loo", "summary")
        data/avaframe/calib_loo.json (the same numbers + the simNames the board plots)

Setting = one friction model with its parameters (samosAT, samosATMedium, samosATSmall, Voellmy mu x xi),
the same on every event. Release thickness rule (main result): 1.2 m wherever the thickness is unknown
(4 of 5 events; middle of the 0.4-2.0 m grid, the only thickness the Voellmy block was run at), the measured
2.7 m (ESK_1 laser scan) at Eiskar. Leave-one-out: for each event, the setting with the smallest mean
|runout error| on the other four events is applied to it unchanged. Settings with a run that touched the
domain edge or hit tEnd are not candidates (Voellmy 0.15/8000 on Kleiner Oetscherbach).
Sensitivity variants: thickness chosen together with friction on the four training events (one global
value), and thickness fitted per event including the held-out one (optimistic, it peeks at the event).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "avaframe" / "calib_results.csv"
BEST = ROOT / "data" / "avaframe" / "calib_results_best.json"
OUT_WEB = ROOT / "web" / "data" / "calibration.json"
OUT_LOO = ROOT / "data" / "avaframe" / "calib_loo.json"
EV = ["avaPopeletzbach", "avaKleinerOetscherbach", "avaEiskar", "avaFilisur1", "avaFilisur2"]
RULE_TH, MEASURED = 1.2, {"avaEiskar": 2.7}
DOI, LIC = "10.5281/zenodo.20701552", "CC-BY-4.0"

SWISS_DEM = {
    "name": "swisstopo swissALTI3D 2 m (rocznik 2019), uśrednione do 5 m",
    "resolution_m": 5, "crs": "EPSG:2056",
    "licence": "© swisstopo, open government data (wolne użycie z podaniem źródła); do potwierdzenia przed pokazem",
    "caveat": "teren z 2019 r., zdarzenie z 2012 r.",
}
META = {
    "avaPopeletzbach": dict(
        name="Popeletzbach", region="Tyrol Wschodni", country="Austria", date="2009-04-07",
        snow="mokra lawina", observed="obserwowany obszar lawiny i obrys osadu",
        provider="dane zebrał Frank Perzl (BFW)",
        dem_used={"name": "Land Tirol, Gelaendemodell_5m_M28 (WCS gis.tirol.gv.at)", "resolution_m": 5,
                  "crs": "EPSG:31287", "licence": "CC BY 4.0 AT", "caveat": "teren współczesny, zdarzenie z 2009 r."}),
    "avaKleinerOetscherbach": dict(
        name="Kleiner Ötscherbach", region="Dolna Austria (masyw Ötscher)", country="Austria", date="2009-02-25",
        snow="sucha lawina płynąca (mała chmura pyłowa)", observed="obserwowany obszar lawiny",
        provider="dane zebrał Frank Perzl (BFW), częściowo wg Funder (2014), BOKU Wien",
        dem_used={"name": "BEV ALS DTM Österreich 1 m (stan na 15.09.2025), uśrednione do 5 m", "resolution_m": 5,
                  "crs": "EPSG:31287", "licence": "CC BY 4.0", "caveat": "teren z 2025 r., zdarzenie z 2009 r."}),
    "avaEiskar": dict(
        name="Eiskar", region="Ramsau am Dachstein, Styria", country="Austria", date="2019-01-15",
        snow="sucha lawina płynąca z dużą chmurą pyłową, silne porywanie śniegu",
        observed="tylko obrys osadu części płynącej (skan laserowy z drona); tor lawiny nie jest zmapowany",
        provider="WLV (austriacka służba przeciwlawinowa); odryw i grubość ze skanu laserowego z drona (Hartl Consulting)",
        dem_used={"name": "BEV ALS DTM 1 m (stan na 15.09.2024), uśrednione do 5 m", "resolution_m": 5,
                  "crs": "EPSG:31287", "licence": "CC BY 4.0", "caveat": "teren z 2024 r., zdarzenie z 2019 r."}),
    "avaFilisur1": dict(
        name="Filisur 1", region="Filisur, Gryzonia", country="Szwajcaria", date="2012-02-23",
        snow="mokra lawina zatrzymana przez las", observed="tylko obrys osadu",
        provider="dane SLF Davos; opis wg Feistl i in. (2014), Journal of Glaciology 60(219)",
        dem_used=SWISS_DEM),
    "avaFilisur2": dict(
        name="Filisur 2", region="Filisur, Gryzonia", country="Szwajcaria", date="2012-02-23",
        snow="mokra lawina zatrzymana na skraju lasu", observed="tylko obrys osadu",
        provider="dane SLF Davos; opis wg Feistl i in. (2014), Journal of Glaciology 60(219)",
        dem_used=SWISS_DEM),
}
CAVEATS = {
    "avaPopeletzbach": ["grubość odrywu nieznana, dobrana z siatki",
                        "samosAT to kalibracja dla suchego śniegu, tu użyta do lawiny mokrej"],
    "avaKleinerOetscherbach": ["grubość odrywu nieznana, dobrana z siatki", "bez lasu"],
    "avaEiskar": ["porywanie śniegu nie jest modelowane, a było istotne: rodzina samosAT staje 227-572 m za krótko",
                  "IoU liczone z samym osadem jest niskie z założenia; miarą jest pokrycie osadu i zasięg",
                  "względem obrysu Max (część płynąca + pył) najlepszy przebieg jest 386 m za krótki"],
    "avaFilisur1": ["grubość odrywu nieznana, dobrana z siatki",
                    "lawinę zatrzymał las, a przebiegi są bez lasu: wszystkie 43 przestrzeliwują o +40 do +205 m",
                    "samosAT to kalibracja dla suchego śniegu, tu użyta do lawiny mokrej"],
    "avaFilisur2": ["grubość odrywu nieznana, dobrana z siatki",
                    "lawinę zatrzymał skraj lasu, a przebiegi są bez lasu: wszystkie 43 przestrzeliwują o +67 do +191 m",
                    "samosAT to kalibracja dla suchego śniegu, tu użyta do lawiny mokrej"],
}


def pl(x, nd=2):
    return f"{x:.{nd}f}".replace(".", ",")


def plural(n):
    if n == 1:
        return "symulacja"
    return "symulacje" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "symulacji"


def fr_key(r):
    if r["frictModel"] == "Voellmy":
        return f"Voellmy mu={r['mu']:g} xi={int(r['xsi'])}"
    return r["frictModel"]


def fr_pl(fr):
    if fr.startswith("Voellmy"):
        mu, xi = fr.split()[1][3:], fr.split()[2][3:]
        return f"Voellmy μ {pl(float(mu))}, ξ {xi} m/s²"
    mu = {"samosAT": 0.155, "samosATMedium": 0.17, "samosATSmall": 0.22}[fr]
    return f"{fr} (μ {pl(mu, 3 if fr == 'samosAT' else 2)})"


def clean(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 3)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


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
        """Thickness fitted to the event itself (smallest |runout error|); Voellmy and Eiskar have one value."""
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

    def overlap(r):
        return ("iou", float(r.iou)) if r.obs_type == "event_area" else ("dep_hit", float(r.dep_hit))

    def loo(cands, fn):
        out = {}
        for h in EV:
            train = [e for e in EV if e != h]
            scores = {c: mae(lambda e, c=c: fn(c, e), train) for c in cands}
            c = min(scores, key=lambda k: (scores[k], k))
            r = fn(c, h)
            m, v = overlap(r)
            out[h] = dict(setting=c, train=scores[c], row=r, metric=m, value=v)
        return out

    main_loo = loo(fixed, lambda c, e: run(c[0], c[1], e))
    var_th = loo(with_th, lambda c, e: run(c[0], c[1], e))
    var_fit = loo(frs, lambda c, e: run_fitted(c, e))
    glob = {c: mae(lambda e, c=c: run(c[0], c[1], e), EV) for c in fixed}
    gbest = min(glob, key=glob.get)
    glob_th = {c: mae(lambda e, c=c: run(c[0], c[1], e), EV) for c in with_th}
    gbest_th = min(glob_th, key=glob_th.get)

    def errs(res):
        return [abs(float(res[h]["row"].runout_error_m)) for h in EV]

    best_json = json.loads(BEST.read_text(encoding="utf-8"))["best"]
    keys = ("frictModel", "mu", "xsi", "relTh", "relTh_source", "iou", "dep_hit", "dep_hit_max", "precision",
            "precision_below_dep_top", "recall", "runout_sim_m", "runout_obs_m", "runout_error_m",
            "runout_error_max_m", "area_sim_ha", "area_obs_ha", "group", "simName")
    events = []
    for e in EV:
        m, b = META[e], best_json[e]
        n = int((d.event == e).sum())
        th = ({"value_m": 2.7, "source": "zmierzona (skan laserowy z drona, odryw ESK_1)"} if e in MEASURED else
              {"value_m": None, "source": "nieznana w danych; przebiegi na siatce 0,4-2,0 m, najlepsza dobrana"})
        g = run(gbest[0], gbest[1], e)
        ev = {
            "id": e, "name": m["name"], "region": m["region"], "country": m["country"], "date": m["date"],
            "avalanche": m["snow"], "obs_type": b["obs_type"], "observed": m["observed"],
            "source": {"event_data": f"OpenNHM/AvaFrameData 1.0, {e}; {m['provider']}", "doi": DOI, "licence": LIC},
            "dem_used": m["dem_used"], "release_thickness": th, "runs": n,
            "best_rule": ("max IoU z obserwowanym obszarem" if b["obs_type"] == "event_area" else
                          "najmniejszy |błąd zasięgu| wśród przebiegów pokrywających co najmniej 50% osadu"),
            "best": {k: clean(b.get(k)) for k in keys},
            "global_setting": {"setting": gbest[0], "relTh": clean(g.relTh), "runout_error_m": clean(g.runout_error_m),
                               "iou": clean(g.iou), "dep_hit": clean(g.dep_hit)},
            "caveats": CAVEATS[e],
        }
        if e == "avaPopeletzbach":
            ev["published"] = {"frictModel": "samosAT", "mu": 0.155, "relTh": 0.6, "iou": 0.727,
                               "runout_error_m": 20.0, "dep_hit": 0.63,
                               "note": "wynik opublikowany wcześniej (klucz best); ponowiony w tej siatce identycznie"}
        events.append(ev)

    def loo_block(res, th_note):
        out = {}
        for h in EV:
            x, r = res[h], res[h]["row"]
            fr = x["setting"][0] if isinstance(x["setting"], tuple) else x["setting"]
            out[h] = {
                "setting": fr, "setting_pl": fr_pl(fr), "frictModel": r.frictModel, "mu": clean(r.mu),
                "xsi": clean(r.xsi), "relTh": clean(r.relTh),
                "relTh_source": "zmierzona 2,7 m" if h in MEASURED else th_note(r),
                "train_mean_abs_runout_error_m": round(x["train"], 1),
                "runout_error_m": clean(r.runout_error_m), "iou_or_overlap": round(x["value"], 3),
                "overlap_metric": x["metric"], "iou": clean(r.iou), "dep_hit": clean(r.dep_hit),
                "simName": r.simName, "group": r.group,
            }
        return out

    loo_main = loo_block(main_loo, lambda r: "reguła: 1,2 m (grubość nieznana)")
    e_main = errs(main_loo)
    same = sum(1 for h in EV if main_loo[h]["setting"] == gbest)
    gerr = [float(run(gbest[0], gbest[1], e).runout_error_m) for e in EV]
    ko = loo_main["avaKleinerOetscherbach"]
    sentence = (
        f"Na {len(EV)} prawdziwych lawinach z Austrii i Szwajcarii ({len(d)} {plural(len(d))} AvaFrame) jedno wspólne "
        f"ustawienie, niezmieniona kalibracja samosAT z odrywem 1,2 m, myli długość zasięgu średnio o "
        f"{glob[gbest]:.0f} m (ustawienie dobrane na tych samych {len(EV)} zdarzeniach). W teście leave-one-out, gdzie ustawienie wybiera się bez danego zdarzenia, "
        f"średni błąd to {np.mean(e_main):.0f} m, a mediana {np.median(e_main):.0f} m; w {same} z {len(EV)} prób "
        f"wybór pada na tę samą kalibrację samosAT. Największy błąd, {ko['runout_error_m']:+.0f} m, jest na "
        f"Kleiner Ötscherbach. Grubość odrywu zmierzono tylko dla Eiskar; dla pozostałych przyjęto 1,2 m."
    )
    summary = {
        "n_events": len(EV), "n_runs": int(len(d)),
        "events_by_country": {"Austria": 3, "Szwajcaria": 2},
        "loo_method": ("leave-one-event-out: dla każdego zdarzenia wybierane jest jedno ustawienie tarcia "
                       "(model + parametry), które minimalizuje średni |błąd zasięgu| na pozostałych czterech, "
                       "i stosowane bez zmian do pominiętego zdarzenia"),
        "thickness_rule": ("1,2 m tam, gdzie grubość odrywu jest nieznana (4 z 5 zdarzeń; środek siatki 0,4-2,0 m), "
                           "zmierzone 2,7 m na Eiskar"),
        "candidates": len(fixed),
        "excluded_settings": sorted(bad),
        "mean_abs_runout_error_loo_m": round(float(np.mean(e_main)), 1),
        "median_abs_runout_error_loo_m": round(float(np.median(e_main)), 1),
        "loo_same_setting_as_global": same,
        "best_global_setting": {
            "setting": gbest[0], "setting_pl": fr_pl(gbest[0]), "relTh": gbest[1],
            "relTh_rule": "1,2 m (nieznana), 2,7 m na Eiskar (zmierzona)",
            "mean_abs_runout_error_m": round(glob[gbest], 1),
            "runout_error_m": {e: round(v, 1) for e, v in zip(EV, gerr)},
            "note": "wybrane na wszystkich 5 zdarzeniach (w próbie), więc to nie jest wynik walidacji",
        },
        "variants": {
            "thickness_chosen_on_training_events": {
                "mean_abs_runout_error_loo_m": round(float(np.mean(errs(var_th))), 1),
                "median_abs_runout_error_loo_m": round(float(np.median(errs(var_th))), 1),
                "held_out": {h: {"setting": var_th[h]["setting"][0], "relTh": clean(var_th[h]["row"].relTh),
                                 "runout_error_m": clean(var_th[h]["row"].runout_error_m)} for h in EV},
                "best_global": {"setting": gbest_th[0], "relTh": gbest_th[1],
                                "mean_abs_runout_error_m": round(glob_th[gbest_th], 1)},
            },
            "thickness_fitted_per_event_optimistic": {
                "note": "grubość dopasowana także do pominiętego zdarzenia, więc test podgląda wynik; górna granica",
                "mean_abs_runout_error_loo_m": round(float(np.mean(errs(var_fit))), 1),
                "median_abs_runout_error_loo_m": round(float(np.median(errs(var_fit))), 1),
                "held_out": {h: {"setting": var_fit[h]["setting"], "relTh": clean(var_fit[h]["row"].relTh),
                                 "runout_error_m": clean(var_fit[h]["row"].runout_error_m)} for h in EV},
            },
        },
        "why_ko_fails": ("bez Kleiner Ötscherbach wygrywa Voellmy μ 0,15, ξ 1000, bo przy zmierzonej grubości "
                         "Eiskar wymaga małego tarcia (porywanie śniegu nie jest modelowane); na Kleiner "
                         "Ötscherbach to tarcie przestrzeliwuje"),
        "sentence_pl": sentence,
        "not_wording": "przykładowa kalibracja na zdarzeniach z Austrii i Szwajcarii, nie dla Tatr",
    }
    doc = json.loads(OUT_WEB.read_text(encoding="utf-8"))
    for k in ("events", "loo", "summary"):
        doc.pop(k, None)
    doc["events"], doc["loo"], doc["summary"] = events, loo_main, summary
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    plot = {e: {"best": best_json[e]["simName"], "best_group": best_json[e]["group"],
                "loo": loo_main[e]["simName"], "loo_group": loo_main[e]["group"]} for e in EV}
    OUT_LOO.write_text(json.dumps({"loo": loo_main, "summary": summary, "plot": plot}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print("excluded", bad)
    print("global", gbest, round(glob[gbest], 1), [round(v) for v in gerr])
    for h in EV:
        x = loo_main[h]
        print(f"{h:24s} {x['setting']:28s} train {x['train_mean_abs_runout_error_m']:6.1f}  "
              f"held {x['runout_error_m']:+7.1f}  {x['overlap_metric']} {x['iou_or_overlap']}")
    print("LOO mean", summary["mean_abs_runout_error_loo_m"], "median", summary["median_abs_runout_error_loo_m"])
    print("variants", {k: v["mean_abs_runout_error_loo_m"] for k, v in summary["variants"].items()})
    print(sentence)


if __name__ == "__main__":
    main()
