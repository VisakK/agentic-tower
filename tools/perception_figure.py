"""Perception figure for the blog post: one camera view, the keypoint network's maps, and the fitted block boxes.

Runs the trained keypoint network and the multi-view pose fit on CPU on one held-out frame of the public
TOWER-SimData dataset (CC BY 4.0). Read-only use of the tower_rl code and checkpoint.

    source ~/Documents/moves/env_isaaclab/bin/activate
    python tools/perception_figure.py --tower_rl ~/Documents/tower_rl --out assets/img/perception.jpg
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tower_rl", required=True)
    ap.add_argument("--variant", default="task1-3_tower_transfer_3")
    ap.add_argument("--episode", type=int, default=0, help="index of the held-out episode folder")
    ap.add_argument("--frame", type=int, default=5, help="frame index inside the episode")
    ap.add_argument("--camera", default="right_front_camera")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.tower_rl).expanduser().resolve()
    sys.path.insert(0, str(root))
    import cv2
    import torch
    from PIL import Image, ImageDraw

    from tower_rl import geometry as geo
    from tower_rl.perception.boxes import corners_world
    from tower_rl.perception.calib import EDGES
    from tower_rl.perception.cameras import CAMERA_IDS, Camera
    from tower_rl.perception.estimator import PoseEstimator
    from tower_rl.perception.model import peaks

    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    vdir = root / "data/perception/dataset_val" / args.variant
    shard = sorted(p for p in vdir.iterdir() if p.is_dir())[args.episode]
    recs = [json.loads(line) for line in open(shard / "frames.jsonl")]
    rec = next(r for r in recs if r["idx"] == args.frame)

    est = PoseEstimator(str(root / "results/perception/models/kp_v2/model_last.pt"), device="cpu", source="evaluator")
    est.reset(rec["variant"])
    order = [rec["block_ids"].index(b) for b in est.block_ids]
    gt_p = np.asarray(rec["pos"])[order]
    gt_R = geo.quat_to_mat(torch.as_tensor(np.asarray(rec["quat"])[order], dtype=torch.float64)).numpy()
    # start from a perturbed truth, as tracking would (4 mm, 3 deg yaw, 1 deg tilt), then one estimator call
    n = len(gt_p)
    dp = rng.normal(0, 0.004, (n, 3)) * np.array([1, 1, 0.5])
    rv = np.concatenate([rng.normal(0, np.radians(1.0), (n, 2)), rng.normal(0, np.radians(3.0), (n, 1))], 1)
    Rn = geo.quat_to_mat(geo.quat_from_rotvec(torch.as_tensor(rv))).numpy()
    est.pos = torch.as_tensor(gt_p + dp, dtype=torch.float32, device=est.dev)
    est.R = torch.as_tensor(Rn @ gt_R, dtype=torch.float32, device=est.dev)
    est.calls = 1
    images = {c: cv2.imread(str(shard / "img" / f"{rec['idx']:06d}_{c}.jpg"), cv2.IMREAD_COLOR)[..., ::-1] for c in CAMERA_IDS}
    pos, quat, conf = est(images, np.asarray(rec["q"]), np.asarray(rec["width"]))
    corner, edge, mask, hidden = est.heatmaps(images)

    ci = CAMERA_IDS.index(args.camera)
    img = images[args.camera].astype(np.float32)
    cam = Camera.from_dict(rec["cams"][args.camera])

    # panel 1: the camera image
    p1 = Image.fromarray(img.astype(np.uint8))
    # panel 2: the network's maps on a dimmed grey image (edges cyan, corner peaks yellow, arm-hidden surface magenta)
    grey = img.mean(-1, keepdims=True).repeat(3, -1) * 0.35
    e = edge[ci].numpy()[..., None]
    h = hidden[ci].numpy()[..., None]
    p2a = grey * (1 - e) + e * np.array([60, 220, 255])
    p2a = p2a * (1 - 0.6 * h) + 0.6 * h * np.array([255, 70, 200])
    p2 = Image.fromarray(p2a.clip(0, 255).astype(np.uint8))
    d2 = ImageDraw.Draw(p2)
    for x, y, _ in peaks(corner[ci].float()).numpy():
        d2.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 214, 0), width=2)
    # panel 3: the fitted boxes (movable blocks orange, fixed foundations white)
    p3 = Image.fromarray(img.astype(np.uint8))
    d3 = ImageDraw.Draw(p3)
    cw = corners_world(pos, quat, est.half.cpu().numpy())
    fixed = est.fixed.cpu().numpy() if hasattr(est.fixed, "cpu") else np.asarray(est.fixed)
    for b in range(len(cw)):
        uv, z = cam.project(cw[b])
        if (z > 0).all():
            col = (255, 255, 255) if fixed[b] else (255, 140, 0)
            for i, j in EDGES:
                d3.line([tuple(uv[i]), tuple(uv[j])], fill=col, width=2)

    W, H = p1.size
    gap = 8
    fig = Image.new("RGB", (3 * W + 2 * gap, H), (255, 255, 255))
    for k, p in enumerate((p1, p2, p3)):
        fig.paste(p, (k * (W + gap), 0))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.save(out, quality=88)
    err = 1000 * np.linalg.norm(pos - gt_p, axis=1)
    mov = ~fixed.astype(bool)
    print(f"{shard.name} frame {rec['idx']} t={rec['t']:.1f}s  movable error mm: median {np.median(err[mov]):.2f} "
          f"max {err[mov].max():.2f}  conf {np.round(conf[mov], 2).tolist()}")


if __name__ == "__main__":
    main()
