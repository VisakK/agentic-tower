"""Cut the blog's videos from the closed-loop renders and write the video sections of index.html.

The renders come from ~/Documents/tower_rl/results/blog_renders/render.sh: one mp4 per episode, 1280 x 1040 at 10 fps,
an 80 px status bar on top of a 2 x 2 grid of the four camera views (front camera top left). The status bar carries
internal labels, so every clip is cropped to the camera grid.

    python3 tools/make_media.py --src ~/Documents/tower_rl/results/blog_renders            # from the repository root
    python3 tools/make_media.py --src <dir> --out /tmp/test --no_html                      # dry test elsewhere

Outputs (in --out, default the repository):
  assets/video/{transfer,cross,stacking,pushdown,insertion}.mp4   per-family loops, 2x speed
  assets/video/teaser.mp4                                          front camera of four tasks, 2 x 2, 2x speed
  assets/video/all_variants.mp4                                    every variant with a title card, real call pace
  assets/video/reaching.mp4                                        v1.3 vs v1.5 on the same episode seed (if rendered)
  assets/img/*_poster.jpg, og.jpg
and the chapter list, the family captions and the reaching figure in index.html.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAMES = {
    "task1-2": "Task 1-2 · Tower transfer, 2 layers", "task1-3": "Task 1-3 · Tower transfer, 3 layers",
    "task2-2": "Task 2-2 · Cross transfer, 2 layers", "task2-3": "Task 2-3 · Cross transfer, 3 layers",
    "task3-2": "Task 3-2 · Vertical stacking, 2 layers", "task3-3": "Task 3-3 · Vertical stacking, 3 layers",
    "task4-2": "Task 4-2 · Push-down, 2 layers", "task4-3": "Task 4-3 · Push-down, 3 layers",
    "task5-2": "Task 5-2 · Insertion, 2 layers", "task5-3": "Task 5-3 · Insertion, 3 layers",
}
CASES = {"nominal": "nominal", "heavy": "heavy blocks", "lighting": "changed lighting", "lightweight": "light blocks",
         "slippery": "slippery blocks", "high_friction": "high friction", "uneven_weights": "uneven masses",
         "shifted_assembly": "shifted tower", "irregular_layers": "irregular layers", "combined": "combined case"}
FAMILIES = [  # key, title, variant preference (first success wins), caption
    ("transfer", "Transfer", ["task1-3", "task1-2"], "six blocks, top layer first, the two arms alternating by layer."),
    ("cross", "Cross transfer", ["task2-3", "task2-2"], "the centre block of each layer, rebuilt as a cross on the other pad."),
    ("stacking", "Vertical stacking", ["task3-3", "task3-2"], "single blocks stacked by the back arm, centres aligned."),
    ("pushdown", "Push-down", ["task4-3", "task4-2"], "every block pushed off the tower, top layer first, with closed fingers."),
    ("insertion", "Insertion", ["task5-3", "task5-2"], "blocks inserted into the tower's centre slots, then pushed home."),
]
ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-movflags", "+faststart", "-an", "-threads", "4"]
GRID = "crop=1280:960:0:80"          # the four camera views, without the status bar
FRONT = "crop=640:480:0:80"          # the front camera (top-left panel)


def run(cmd):
    subprocess.run(["nice", "-n", "15", *cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def parse(p: Path) -> dict:
    """<variant>_<tier>_<case>_seed<seed>_<success|fail>.mp4"""
    m = re.match(r"(task\d-\d)_[a-z0-9_]+?_(D\de?)_(\w+?)_seed(\d+)_(success|fail)\.mp4$", p.name)
    if not m:
        raise ValueError(p.name)
    return {"path": p, "variant": m.group(1), "tier": m.group(2), "case": m.group(3), "seed": int(m.group(4)),
            "ok": m.group(5) == "success"}


def episodes(d: Path) -> list:
    return sorted((parse(p) for p in d.glob("*.mp4")), key=lambda e: (e["variant"], not e["ok"], e["seed"]))


def pick(eps: list, variant: str, need_ok: bool = False):
    c = [e for e in eps if e["variant"] == variant]
    ok = [e for e in c if e["ok"]]
    return ok[0] if ok else (None if need_ok else (c[0] if c else None))


def poster(video: Path, img: Path, at: float):
    run(["ffmpeg", "-y", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(img)])


def loop_clip(e: dict, out: Path, width=960):
    run(["ffmpeg", "-y", "-i", str(e["path"]), "-vf", f"{GRID},setpts=PTS/2,scale={width}:-2", "-r", "20",
         "-crf", "27", *ENC, str(out)])


def teaser(eps4: list, out: Path):
    ins, chains = [], []
    longest = max(duration(e["path"]) for e in eps4) / 2
    for k, e in enumerate(eps4):
        ins += ["-i", str(e["path"])]
        pad = longest - duration(e["path"]) / 2
        chains.append(f"[{k}:v]{FRONT},setpts=PTS/2,fps=20,tpad=stop_mode=clone:stop_duration={pad + 1.5:.2f}[v{k}]")
    lay = "[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[g]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(chains) + ";" + lay, "-map", "[g]", "-crf", "28", *ENC,
         str(out)])


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")


def card(text1: str, text2: str, out: Path, w=1024, h=768, secs=2.0):
    vf = (f"drawtext=fontfile={FONT_B}:text='{esc(text1)}':fontcolor=0xE6EDF2:fontsize=40:x=(w-tw)/2:y=h/2-50,"
          f"drawtext=fontfile={FONT}:text='{esc(text2)}':fontcolor=0x9AA8B4:fontsize=28:x=(w-tw)/2:y=h/2+14")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x0f1418:s={w}x{h}:r=10:d={secs}", "-vf", vf, "-crf", "24",
         *ENC, str(out)])


def full_video(items: list, out: Path, tmp: Path):
    """items: (episode, card title, card subtitle). Real call pace (10 fps), 1024 x 768."""
    parts, chapters, t = [], [], 0.0
    for k, (e, t1, t2) in enumerate(items):
        c = tmp / f"card_{k:02d}.mp4"
        card(t1, t2, c)
        v = tmp / f"clip_{k:02d}.mp4"
        run(["ffmpeg", "-y", "-i", str(e["path"]), "-vf", f"{GRID},scale=1024:768", "-r", "10", "-crf", "24", *ENC,
             str(v)])
        chapters.append((t, t1.split(" · ")[0], t1.split(" · ")[1] + (", " + t2.split(" · ")[0] if "nominal" not in t2 else "")))
        t += duration(c) + duration(v)
        parts += [c, v]
    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)])
    return chapters


def reaching(e13: dict, e15: dict, out: Path):
    """Front camera, v1.3 (left) and v1.5 (right), same episode seed, 2x speed; the shorter one holds its last frame."""
    d13, d15 = duration(e13["path"]) / 2, duration(e15["path"]) / 2
    longest = max(d13, d15)
    lab = (f"drawtext=fontfile={FONT_B}:fontcolor=white:fontsize=24:box=1:boxcolor=0x000000@0.55:boxborderw=8:x=14:y=14:"
           "text='{t}'")
    fc = (f"[0:v]{FRONT},setpts=PTS/2,fps=20,tpad=stop_mode=clone:stop_duration={longest - d13 + 1.5:.2f},"
          + lab.format(t=esc("student v1.3: planned transits")) + "[a];"
          f"[1:v]{FRONT},setpts=PTS/2,fps=20,tpad=stop_mode=clone:stop_duration={longest - d15 + 1.5:.2f},"
          + lab.format(t=esc("student v1.5: learned reaching")) + "[b];[a][b]hstack=inputs=2[g]")
    run(["ffmpeg", "-y", "-i", str(e13["path"]), "-i", str(e15["path"]), "-filter_complex", fc, "-map", "[g]",
         "-crf", "27", *ENC, str(out)])


def record(src: Path, e: dict):
    """The episode's rehearsal record (simulated duration, success, policy calls), matched by variant and seed."""
    for f in src.glob(f"{e['variant']}_*/{e['tier']}_*/episodes.json"):
        try:
            rows = json.loads(f.read_text())
        except Exception:
            continue
        for r in rows:
            if int(r.get("extra", {}).get("seed", -1)) == e["seed"]:
                return {"t": float(r["duration_s"]), "ok": bool(r["task_success"]),
                        "calls": int(r["extra"].get("act_calls", 0))}
    return None


def outcome(src: Path, e: dict) -> str:
    r = record(src, e)
    if r is None:
        return "succeeded" if e["ok"] else "did not succeed"
    return f"succeeded at {r['t']:.0f} s" if r["ok"] else f"did not succeed in {r['t']:.0f} s"


def replace_block(html: str, name: str, body: str) -> str:
    a, b = f"<!-- BEGIN {name} -->\n", f"<!-- END {name} -->"
    i, j = html.index(a) + len(a), html.index(b)
    return html[:i] + body + html[j:]


def mmss(t: float) -> str:
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="results/blog_renders of tower_rl")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--no_html", action="store_true")
    args = ap.parse_args()
    src, out = Path(args.src).expanduser(), Path(args.out)
    vid, img, tmp = out / "assets/video", out / "assets/img", out / "tools/.tmp"
    for d in (vid, img, tmp):
        d.mkdir(parents=True, exist_ok=True)
    d0 = episodes(src / "v1_3_D0/videos")
    d1 = episodes(src / "v1_3_D1/videos") if (src / "v1_3_D1/videos").exists() else []
    report = []

    fam_html, fam_eps = [], {}
    for key, title, prefs, cap in FAMILIES:
        e = next((x for x in (pick(d0, v, need_ok=True) for v in prefs) if x), None) or pick(d0, prefs[0])
        fam_eps[key] = e
        loop_clip(e, vid / f"{key}.mp4")
        poster(vid / f"{key}.mp4", img / f"{key}_poster.jpg", duration(vid / f"{key}.mp4") * 0.45)
        note = "" if e["ok"] else " This episode did not succeed; the tower is disturbed at the end."
        fam_html.append(f'''    <figure>
      <video src="assets/video/{key}.mp4" poster="assets/img/{key}_poster.jpg" autoplay muted loop playsinline preload="none"
             aria-label="{title}: the student's four camera views"></video>
      <figcaption><b>{title}.</b> {NAMES[e["variant"]].split(" · ")[0]}: {cap}{note}</figcaption>
    </figure>
''')
        report.append(f"family {key}: {e['path'].name}")

    fail_html = ""
    fails = [e for e in d0 if e["variant"] == "task4-3" and not e["ok"]]
    if fails:
        loop_clip(fails[0], vid / "failure.mp4")
        dur = duration(vid / "failure.mp4")
        poster(vid / "failure.mp4", img / "failure_poster.jpg", dur - 0.5)
        fail_html = ('  <figure>\n    <video src="assets/video/failure.mp4" poster="assets/img/failure_poster.jpg" controls muted '
                     'playsinline preload="none"\n           aria-label="A failed three-layer push-down episode, four camera '
                     'views"></video>\n    <figcaption>FAILURE_CAPTION</figcaption>\n  </figure>\n')
        rf = record(src / "v1_3_D0", fails[0])
        fail_html = fail_html.replace("FAILURE_CAPTION", (
            "A three-layer push-down that fails, from the same renders (nominal case, 2× speed). The pushes of the top "
            "two layers succeed, but blocks of the bottom layer come to rest on the debris of the upper layers, where "
            "the cameras lose track of them: the white boxes are their true poses, far from the student's estimates. "
            "Eight of the nine pushes count; the task needs all nine."))
        report.append(f"failure: {fails[0]['path'].name}, {rf}")

    four = [fam_eps[k] for k in ("transfer", "cross", "pushdown", "insertion")]
    teaser(four, vid / "teaser.mp4")
    poster(vid / "teaser.mp4", img / "teaser_poster.jpg", duration(vid / "teaser.mp4") * 0.5)
    poster(vid / "teaser.mp4", img / "og_src.jpg", duration(vid / "teaser.mp4") * 0.5)
    subprocess.run(["ffmpeg", "-y", "-i", str(img / "og_src.jpg"), "-vf", "crop=1280:672:0:144,scale=1200:630",
                    "-q:v", "3", str(img / "og.jpg")], check=True, capture_output=True)
    (img / "og_src.jpg").unlink()

    items = []
    for v in NAMES:
        e = pick(d0, v)
        if e is None:
            continue
        items.append((e, NAMES[v], "nominal · " + outcome(src / "v1_3_D0", e)))
    for e in d1:
        items.append((e, NAMES[e["variant"]], f"{CASES.get(e['case'], e['case'])} · " + outcome(src / "v1_3_D1", e)))
    chapters = full_video(items, vid / "all_variants.mp4", tmp)
    poster(vid / "all_variants.mp4", img / "full_poster.jpg", 2.5)
    ch_html = "".join(f'    <li><button data-t="{t:.1f}"><span class="t">{mmss(t)}</span><span>{a}: {b}</span></button></li>\n'
                      for t, a, b in chapters)
    report.append(f"full video {duration(vid / 'all_variants.mp4'):.0f} s, {len(items)} chapters")

    reach_html = ""
    v15 = episodes(src / "v1_5_D0/videos") if (src / "v1_5_D0/videos").exists() else []
    if v15:
        e15 = v15[0]
        e13 = next((e for e in d0 if e["variant"] == e15["variant"] and e["seed"] == e15["seed"]), None)
        if e13:
            reaching(e13, e15, vid / "reaching.mp4")
            poster(vid / "reaching.mp4", img / "reaching_poster.jpg", duration(vid / "reaching.mp4") * 0.3)
            report.append(f"reaching: {e13['path'].name} vs {e15['path'].name}; v1.3 {record(src / 'v1_3_D0', e13)} "
                          f"v1.5 {record(src / 'v1_5_D0', e15)}")
            r13, r15 = record(src / "v1_3_D0", e13), record(src / "v1_5_D0", e15)
            cap = ("The same Task 1-3 episode (same layout and seed) with planned transits (left, student v1.3) and "
                   "learned reaching (right, student v1.5), front camera, one frame per policy call, 2× speed. ")
            if r13 and r15:
                cap += (f"Student v1.3 finishes at {r13['t']:.0f} s of simulated time in {r13['calls']} policy calls; "
                        f"student v1.5 at {r15['t']:.0f} s in {r15['calls']}. ")
            cap += "One episode each; the rendered closed loop is not deterministic."
            reach_html = (f'  <figure>\n    <video src="assets/video/reaching.mp4" poster="assets/img/reaching_poster.jpg" '
                          f'controls muted loop playsinline preload="none"\n           aria-label="The same episode with planned '
                          f'transits and with learned reaching, front camera"></video>\n'
                          f'    <figcaption>{cap}</figcaption>\n  </figure>\n')

    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()
    print("\n".join(report))
    if args.no_html:
        print(ch_html)
        return
    p = out / "index.html"
    html = p.read_text()
    html = replace_block(html, "videos:families", "".join(fam_html))
    html = replace_block(html, "videos:chapters", ch_html)
    if fail_html and "<!-- BEGIN videos:failure -->" in html:
        html = replace_block(html, "videos:failure", fail_html)
    if reach_html and "<!-- BEGIN videos:reaching -->" in html:
        html = replace_block(html, "videos:reaching", reach_html)
    p.write_text(html)
    print("index.html updated")


if __name__ == "__main__":
    main()
