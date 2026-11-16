"""Stage-2 ECG model on PTB-XL, following the official benchmark protocol (Strodthoff et al. 2020):
5 diagnostic superclasses (NORM, MI, STTC, CD, HYP), 100 Hz, folds 1-8 train / 9 val / 10 test (patient-disjoint)."""
import ast, json, os, glob, numpy as np, pandas as pd, wfdb, torch, torch.nn as nn
from sklearn.metrics import roc_auc_score

ROOT = glob.glob("data/ptbxl/ptb-xl-*")[0]
CLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]
CACHE = "data/ptbxl/x100.npy"

meta = pd.read_csv(f"{ROOT}/ptbxl_database.csv", index_col="ecg_id")
meta.scp_codes = meta.scp_codes.apply(ast.literal_eval)
scp = pd.read_csv(f"{ROOT}/scp_statements.csv", index_col=0)
scp = scp[scp.diagnostic == 1]
meta["super"] = meta.scp_codes.apply(lambda d: sorted({scp.loc[k, "diagnostic_class"] for k in d if k in scp.index}))
meta = meta[meta.super.map(len) > 0]  # standard: drop records with no diagnostic superclass label
Y = np.array([[c in s for c in CLASSES] for s in meta.super], dtype=np.float32)

if os.path.exists(CACHE) and np.load(CACHE, mmap_mode="r").shape[0] == len(meta):
    X = np.load(CACHE)
else:
    X = np.stack([wfdb.rdsamp(f"{ROOT}/{f}")[0] for f in meta.filename_lr]).astype(np.float32)  # (N,1000,12)
    np.save(CACHE, X)
X = X.transpose(0, 2, 1)  # (N,12,1000)
fold = meta.strat_fold.values
tr, va, te = fold <= 8, fold == 9, fold == 10
mu, sd = X[tr].mean((0, 2), keepdims=True), X[tr].std((0, 2), keepdims=True)
X = (X - mu) / sd

class Block(nn.Module):
    def __init__(s, ci, co, st):
        super().__init__()
        s.c = nn.Sequential(nn.Conv1d(ci, co, 7, st, 3, bias=False), nn.BatchNorm1d(co), nn.ReLU(),
                            nn.Conv1d(co, co, 7, 1, 3, bias=False), nn.BatchNorm1d(co))
        s.sk = nn.Sequential() if ci == co and st == 1 else nn.Sequential(nn.Conv1d(ci, co, 1, st, bias=False), nn.BatchNorm1d(co))
    def forward(s, x): return torch.relu(s.c(x) + s.sk(x))

class ResNet1d(nn.Module):
    def __init__(s, n=5):
        super().__init__()
        s.f = nn.Sequential(nn.Conv1d(12, 64, 15, 2, 7, bias=False), nn.BatchNorm1d(64), nn.ReLU(),
                            Block(64, 64, 1), Block(64, 128, 2), Block(128, 128, 1), Block(128, 256, 2),
                            Block(256, 256, 1), Block(256, 256, 2), nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Dropout(0.3))
        s.h = nn.Linear(256, n)
    def forward(s, x): return s.h(s.f(x))

dev = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0)
model = ResNet1d().to(dev)
opt = torch.optim.AdamW(model.parameters(), 1e-3, weight_decay=1e-2)
EPOCHS = 30
sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=EPOCHS * int(np.ceil(tr.sum() / 128)))
lossf = nn.BCEWithLogitsLoss()
Xt, Yt = torch.tensor(X), torch.tensor(Y)

def predict(mask):
    model.eval(); out = []
    with torch.no_grad():
        for i in np.array_split(np.where(mask)[0], 20):
            out.append(torch.sigmoid(model(Xt[i].to(dev))).cpu().numpy())
    return np.concatenate(out)

best, best_state = 0, None
for ep in range(EPOCHS):
    model.train()
    for b in np.array_split(np.random.permutation(np.where(tr)[0]), int(np.ceil(tr.sum() / 128))):
        xb = Xt[b].to(dev)
        xb = xb * (1 + 0.1 * torch.randn(len(b), 1, 1, device=dev)) + 0.02 * torch.randn_like(xb)  # light amplitude/noise aug
        loss = lossf(model(xb), Yt[b].to(dev))
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
    auc = roc_auc_score(Y[va], predict(va), average="macro")
    if auc > best: best, best_state = auc, {k: v.clone() for k, v in model.state_dict().items()}
    print(f"epoch {ep:2d} loss {loss.item():.3f} val macro-AUROC {auc:.4f}", flush=True)

model.load_state_dict(best_state)  # model selected on fold 9 only; fold 10 touched once below
pt = predict(te)
res = {"n_train": int(tr.sum()), "n_val": int(va.sum()), "n_test": int(te.sum()), "val_macro_auroc": best,
       "test_macro_auroc": roc_auc_score(Y[te], pt, average="macro"),
       "test_auroc_per_class": {c: roc_auc_score(Y[te][:, i], pt[:, i]) for i, c in enumerate(CLASSES)},
       "test_prevalence": dict(zip(CLASSES, Y[te].mean(0).round(3).tolist())),
       "literature_reference": "Strodthoff et al. 2020 superdiagnostic test macro-AUROC ~0.92-0.93 (xresnet1d/inception1d)"}
np.save("outputs/ecg_val_probs.npy", predict(va)); np.save("outputs/ecg_val_labels.npy", Y[va])
np.save("outputs/ecg_test_probs.npy", pt); np.save("outputs/ecg_test_labels.npy", Y[te])
torch.save({"state": best_state, "mu": mu, "sd": sd, "classes": CLASSES}, "outputs/ecg_resnet1d.pt")
json.dump(res, open("outputs/ecg_results.json", "w"), indent=2, default=float)
print(json.dumps(res, indent=2, default=float))
