"""Stage-2 chest X-ray model on NIH ChestX-ray14 (local subset: images_001 archive).
ImageNet-pretrained DenseNet-121 (CheXNet architecture), 14 findings, PATIENT-disjoint 70/10/20 split.
Note: subset is ~1/11 of NIH; NIH labels are NLP-mined from reports (~90% accurate per the dataset authors)."""
import json, os, glob, numpy as np, pandas as pd, torch, torch.nn as nn, torchvision
from PIL import Image
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

FIND = ["Atelectasis", "Cardiomegaly", "Effusion", "Infiltration", "Mass", "Nodule", "Pneumonia", "Pneumothorax",
        "Consolidation", "Edema", "Emphysema", "Fibrosis", "Pleural_Thickening", "Hernia"]
S, CACHE = 256, "data/nih/img256.npy"
files = {os.path.basename(p): p for p in glob.glob("data/nih/img/**/*.png", recursive=True)}
lab = pd.read_csv("data/nih/Data_Entry_2017_v2020.csv")
lab = lab[lab["Image Index"].isin(files)].reset_index(drop=True)
Y = np.array([[f in s.split("|") for f in FIND] for s in lab["Finding Labels"]], dtype=np.float32)

if os.path.exists(CACHE) and np.load(CACHE, mmap_mode="r").shape[0] == len(lab):
    X = np.load(CACHE)
else:
    X = np.stack([np.asarray(Image.open(files[f]).convert("L").resize((S, S), Image.BILINEAR)) for f in lab["Image Index"]])
    np.save(CACHE, X)

g = lab["Patient ID"].values
tv, te = next(GroupShuffleSplit(1, test_size=0.2, random_state=0).split(X, groups=g))
tr_i, va_i = next(GroupShuffleSplit(1, test_size=0.125, random_state=0).split(tv, groups=g[tv]))
tr, va = tv[tr_i], tv[va_i]
assert not (set(g[tr]) & set(g[te])) and not (set(g[va]) & set(g[te]))

dev = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0); np.random.seed(0)
m = torchvision.models.densenet121(weights="IMAGENET1K_V1")
m.classifier = nn.Linear(m.classifier.in_features, len(FIND))
m = m.to(dev).to(memory_format=torch.channels_last)
MEAN = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)

def batch(idx, train):
    x = torch.tensor(X[idx], device=dev).float().div(255).unsqueeze(1)
    if train:  # random crop + small rotation-free shift, horizontal flip off (anatomy is lateralized)
        i, j = np.random.randint(0, S - 224, 2)
        x = x[:, :, i:i + 224, j:j + 224]
    else:
        o = (S - 224) // 2; x = x[:, :, o:o + 224, o:o + 224]
    return ((x.expand(-1, 3, -1, -1) - MEAN) / STD).contiguous(memory_format=torch.channels_last)

pos = Y[tr].mean(0).clip(1e-3)
lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.sqrt((1 - pos) / pos), device=dev))  # tempered class weighting
opt = torch.optim.AdamW(m.parameters(), 1e-4, weight_decay=1e-4)
EPOCHS, BS = 12, 32
scaler = torch.amp.GradScaler()

def predict(idx):
    m.eval(); out = []
    with torch.no_grad(), torch.autocast(dev, dtype=torch.float16):
        for b in np.array_split(idx, max(1, len(idx) // 64)):
            out.append(torch.sigmoid(m(batch(b, False)).float()).cpu().numpy())
    return np.concatenate(out)

def macro(yt, p):
    ok = [i for i in range(len(FIND)) if 0 < yt[:, i].sum() < len(yt)]
    return float(np.mean([roc_auc_score(yt[:, i], p[:, i]) for i in ok]))

best, state = 0, None
for ep in range(EPOCHS):
    m.train()
    for b in np.array_split(np.random.permutation(tr), len(tr) // BS):
        with torch.autocast(dev, dtype=torch.float16):
            loss = lossf(m(batch(b, True)), torch.tensor(Y[b], device=dev))
        opt.zero_grad(); scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
    auc = macro(Y[va], predict(va))
    if auc > best: best, state = auc, {k: v.clone() for k, v in m.state_dict().items()}
    print(f"epoch {ep:2d} loss {loss.item():.3f} val macro-AUROC {auc:.4f}", flush=True)

m.load_state_dict(state)  # selected on validation patients only; test patients evaluated once
pt = predict(te)
per = {f: (roc_auc_score(Y[te][:, i], pt[:, i]) if 0 < Y[te][:, i].sum() < len(te) else None) for i, f in enumerate(FIND)}
nf = Y[te].sum(1) == 0
res = {"n_images": len(lab), "n_patients": int(len(set(g))), "n_train": len(tr), "n_val": len(va), "n_test": len(te),
       "val_macro_auroc": best, "test_macro_auroc": macro(Y[te], pt), "test_auroc_per_finding": per,
       "test_positives_per_finding": dict(zip(FIND, Y[te].sum(0).astype(int).tolist())),
       "test_auroc_any_finding_vs_no_finding": roc_auc_score(~nf, pt.max(1)),
       "literature_reference": "CheXNet-style DenseNet-121 on full NIH (~112k images): mean AUROC ~0.81-0.84"}
np.save("outputs/cxr_val_probs.npy", predict(va)); np.save("outputs/cxr_val_labels.npy", Y[va])
np.save("outputs/cxr_test_probs.npy", pt); np.save("outputs/cxr_test_labels.npy", Y[te])
torch.save({"state": state, "classes": FIND}, "outputs/cxr_densenet121.pt")
json.dump(res, open("outputs/cxr_results.json", "w"), indent=2, default=float)
print(json.dumps(res, indent=2, default=float))
