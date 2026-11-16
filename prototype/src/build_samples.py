"""Build the demo sample bank from HELD-OUT TEST data only (PTB-XL fold 10, NIH test patients), so the website never
shows the models an example they were trained on."""
import ast, glob, json, os, numpy as np, pandas as pd, wfdb
from PIL import Image
from sklearn.model_selection import GroupShuffleSplit

rng = np.random.default_rng(7)
# ---- ECG ----
ROOT = glob.glob("data/ptbxl/ptb-xl-*")[0]
meta = pd.read_csv(f"{ROOT}/ptbxl_database.csv", index_col="ecg_id")
meta.scp_codes = meta.scp_codes.apply(ast.literal_eval)
scp = pd.read_csv(f"{ROOT}/scp_statements.csv", index_col=0); scp = scp[scp.diagnostic == 1]
meta["super"] = meta.scp_codes.apply(lambda d: sorted({scp.loc[k, "diagnostic_class"] for k in d if k in scp.index}))
te = meta[(meta.strat_fold == 10) & (meta.super.map(len) > 0)]
picks = []
for want in [["NORM"], ["NORM"], ["MI"], ["MI"], ["STTC"], ["CD"], ["MI", "STTC"], ["HYP"]]:
    cand = te[te.super.apply(lambda s: s == want) & ~te.index.isin(picks)]
    picks.append(int(rng.choice(cand.index)))
sig = np.stack([wfdb.rdsamp(f"{ROOT}/{meta.loc[i, 'filename_lr']}")[0] for i in picks]).astype(np.float32)
np.savez_compressed("app/samples/ecg.npz", x=sig, ids=np.array(picks))
ecg_manifest = [{"id": f"ecg-{i}", "ecg_id": i, "true_labels": meta.loc[i, "super"], "age": float(meta.loc[i, "age"]),
                 "sex": "M" if meta.loc[i, "sex"] == 0 else "F"} for i in picks]

# ---- CXR (same patient-level split as cxr_train.py) ----
files = {os.path.basename(p): p for p in glob.glob("data/nih/img/**/*.png", recursive=True)}
lab = pd.read_csv("data/nih/Data_Entry_2017_v2020.csv")
lab = lab[lab["Image Index"].isin(files)].reset_index(drop=True)
g = lab["Patient ID"].values
_, tei = next(GroupShuffleSplit(1, test_size=0.2, random_state=0).split(lab, groups=g))
tl = lab.iloc[tei]
cxr_manifest, chosen = [], []
for want in ["No Finding", "No Finding", "Effusion", "Edema", "Pneumothorax", "Cardiomegaly", "Atelectasis", "Mass"]:
    cand = tl[(tl["Finding Labels"].str.split("|").apply(lambda s: want in s)) & ~tl["Image Index"].isin(chosen)]
    if want != "No Finding": cand = cand[cand["Finding Labels"].str.count(r"\|") <= 1] if len(cand[cand["Finding Labels"].str.count(r"\|") <= 1]) else cand
    r = cand.sample(1, random_state=int(rng.integers(1e6))).iloc[0]
    chosen.append(r["Image Index"])
    Image.open(files[r["Image Index"]]).convert("L").resize((256, 256), Image.BILINEAR).save(f"app/samples/cxr/{r['Image Index']}")
    cxr_manifest.append({"id": f"cxr-{r['Image Index'][:-4]}", "file": r["Image Index"],
                         "true_labels": r["Finding Labels"].split("|"), "age": int(r["Patient Age"]), "sex": r["Patient Gender"]})
json.dump({"ecg": ecg_manifest, "cxr": cxr_manifest}, open("app/samples/manifest.json", "w"), indent=2)
print(json.dumps({"ecg": ecg_manifest, "cxr": cxr_manifest}, indent=1))
