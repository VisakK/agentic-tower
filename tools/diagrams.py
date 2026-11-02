"""Draw the three architecture diagrams as inline SVG and write them into index.html.

The SVGs use the page's CSS variables (classes d-learned, d-planned, ...), so they follow light and dark mode.
Each diagram replaces the text between <!-- BEGIN diagram:NAME --> and <!-- END diagram:NAME --> in index.html.

    python3 tools/diagrams.py            # from the repository root
"""
import re
from html import escape
from pathlib import Path

STYLE = """<style>
.d-box{stroke-width:1.6}
.d-learned{fill:var(--teal-bg);stroke:var(--teal)}
.d-planned{fill:var(--amber-bg);stroke:var(--amber)}
.d-demo{fill:var(--blue-bg);stroke:var(--blue)}
.d-priv{fill:var(--grey-bg);stroke:var(--grey);stroke-dasharray:6 4}
.d-neutral{fill:var(--surface);stroke:var(--rule-strong)}
.d-group{fill:none;stroke:var(--rule-strong);stroke-dasharray:3 4}
.d-t{fill:var(--ink);font-size:15.5px;font-weight:650}
.d-s{fill:var(--muted);font-size:13.5px}
.d-l{fill:var(--muted);font-size:12.5px;font-style:italic}
.d-g{fill:var(--muted);font-size:12.5px;font-weight:650;letter-spacing:.04em;text-transform:uppercase}
.d-a{fill:none;stroke:var(--muted);stroke-width:1.5}
.d-a.dash{stroke-dasharray:5 4}
.d-head{fill:var(--muted)}
</style>"""


class Svg:
    def __init__(self, name: str, w: int, h: int):
        self.name, self.w, self.h = name, w, h
        self.parts = []

    def box(self, x, y, w, h, kind, title, lines=(), align="middle", r=9):
        self.parts.append(f'<rect class="d-box d-{kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>')
        n = 1 + len(lines)
        lh_t, lh_s = 19, 17
        total = lh_t + lh_s * (n - 1)
        ty = y + (h - total) / 2 + 13
        cx = x + w / 2 if align == "middle" else x + 12
        self.parts.append(f'<text class="d-t" x="{cx}" y="{ty:.1f}" text-anchor="{align}">{escape(title)}</text>')
        for k, line in enumerate(lines):
            yy = ty + lh_t + lh_s * k - 1
            self.parts.append(f'<text class="d-s" x="{cx}" y="{yy:.1f}" text-anchor="{align}">{escape(line)}</text>')

    def group(self, x, y, w, h, label):
        self.parts.append(f'<rect class="d-group" x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/>')
        self.parts.append(f'<text class="d-g" x="{x + 12}" y="{y + 20}">{escape(label)}</text>')

    def arrow(self, pts, label=None, lx=None, ly=None, dash=False, anchor="middle"):
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        cls = "d-a dash" if dash else "d-a"
        self.parts.append(f'<path class="{cls}" d="{d}" marker-end="url(#ah-{self.name})"/>')
        if label:
            self.parts.append(f'<text class="d-l" x="{lx}" y="{ly}" text-anchor="{anchor}">{escape(label)}</text>')

    def line(self, pts, dash=False):
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        cls = "d-a dash" if dash else "d-a"
        self.parts.append(f'<path class="{cls}" d="{d}"/>')

    def render(self) -> str:
        defs = (f'<defs><marker id="ah-{self.name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto-start-reverse"><path class="d-head" d="M0,0 L10,5 L0,10 z"/></marker></defs>')
        body = "\n".join(self.parts)
        return (f'<svg viewBox="0 0 {self.w} {self.h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
                f'focusable="false">\n{STYLE}\n{defs}\n{body}\n</svg>')


def teacher() -> str:
    s = Svg("teacher", 940, 470)
    s.box(20, 20, 220, 120, "demo", "Task graph", ["one per task variant, from", "the demonstrations: block", "order, arm per step, goals"])
    s.box(20, 200, 220, 96, "priv", "Simulator state", ["exact pose of every block,", "joint angles, gripper widths"])
    s.box(290, 50, 230, 210, "planned", "Executor", ["runs one skill call at a time", "and checks its outcome:", "lifted and held? placed within", "5 mm and 5°? pushed clear with", "the tower intact? On failure:", "retry, skip, other arm, park"])
    s.group(600, 12, 320, 336, "Skills")
    chips = [
        ("learned", "Grasp and lift", "PPO, one policy per arm"),
        ("learned", "Place and release", "PPO, one policy per arm"),
        ("learned", "Push (Task 4)", "PPO, one policy per arm"),
        ("planned", "Transit", "IK path, quintic timing"),
        ("planned", "Park", "joint-space move home"),
        ("planned", "Task 5 grasp, insert, push-in", "closed-loop controllers"),
    ]
    for y, (kind, t, sub) in zip((42, 90, 138, 196, 244, 292), chips):
        s.box(614, y, 292, 44, kind, t, [sub], r=8)
    s.box(290, 362, 230, 72, "planned", "Arm controller", ["damped least-squares IK,", "gravity-sag compensation"])
    s.box(600, 362, 320, 72, "neutral", "Physics (PhysX, CPU, 120 Hz)", ["each 10 Hz row is held for", "12 physics steps"])
    s.arrow([(240, 80), (288, 110)])
    s.arrow([(240, 248), (288, 210)])
    s.arrow([(520, 120), (598, 120)], "skill call", 559, 110)
    s.arrow([(600, 200), (522, 200)], "outcome", 561, 192)
    s.arrow([(600, 318), (405, 318), (405, 360)], "pose change or joint targets", 500, 310)
    s.arrow([(520, 398), (598, 398)], "1–16 rows", 559, 390)
    s.arrow([(760, 434), (760, 456), (130, 456), (130, 298)])
    s.parts.append('<text class="d-l" x="445" y="452" text-anchor="middle">next state</text>')
    return s.render()


def student() -> str:
    s = Svg("student", 940, 560)
    s.box(20, 20, 200, 110, "neutral", "Official observation", ["4 RGB cameras, 640 × 480,", "joint angles, gripper", "widths, time"])
    s.box(260, 20, 200, 110, "learned", "Keypoint network", ["ResNet-34 U-Net: corners,", "edges, block surface,", "arm-covered surface"])
    s.box(500, 20, 200, 110, "planned", "Multi-view pose fit", ["and tracker: all 4 cameras,", "robust Gauss-Newton,", "pose + confidence"])
    s.box(740, 20, 180, 110, "neutral", "Estimated state", ["block poses, arm state,", "memory of subtasks", "and their outcomes"])
    s.arrow([(220, 75), (258, 75)])
    s.arrow([(460, 75), (498, 75)])
    s.arrow([(700, 75), (738, 75)])
    s.box(20, 196, 200, 96, "demo", "Task plan", ["goals and prescribed arms,", "from the demonstrations"])
    s.box(260, 180, 220, 128, "learned", "High-level policy", ["transformer over block, goal", "and arm tokens; picks the", "subtask, goal block and arm", "(BC + DAgger)"])
    s.box(520, 180, 200, 128, "planned", "Option executor", ["expands the subtask into", "skill calls and checks", "each outcome (the", "teacher's executor code)"])
    s.arrow([(830, 130), (830, 156), (370, 156), (370, 178)])
    s.arrow([(220, 244), (258, 244)])
    s.arrow([(480, 244), (518, 244)], "option", 499, 236)
    s.arrow([(650, 178), (650, 132)], dash=True)
    s.parts.append('<text class="d-l" x="642" y="148" text-anchor="end">block to track</text>')
    s.group(12, 336, 916, 116, "Skills")
    s.box(26, 366, 200, 70, "learned", "Grasp, place", ["PPO, the teacher's", "policies unchanged"])
    s.box(240, 366, 200, 70, "learned", "Push", ["PPO, fine-tuned under", "perception errors"])
    s.box(454, 366, 250, 70, "learned", "Task 5 grasp, insert, push-in", ["behaviour cloning of the", "planned controllers (DART)"])
    s.box(718, 366, 196, 70, "planned", "Transit, park", ["planned, as in", "the teacher"])
    s.arrow([(620, 308), (620, 334)])
    s.box(260, 478, 240, 64, "planned", "Arm controller", ["damped least-squares IK,", "gravity-sag compensation"])
    s.box(560, 478, 360, 64, "neutral", "Action chunk to the evaluator", ["1–16 rows × 16 joint targets, 10 Hz"])
    s.arrow([(380, 452), (380, 476)])
    s.arrow([(500, 510), (558, 510)])
    return s.render()


def pipeline() -> str:
    s = Svg("pipeline", 940, 500)
    s.box(20, 20, 200, 64, "demo", "Demonstrations", ["531 episodes, 10 variants"])
    s.box(20, 110, 200, 168, "demo", "Taken from them", ["task plans (order, arm)", "layouts and rest heights", "grasp and push geometry", "arm drive gains", "camera calibration", "2,800 labelled frames"])
    s.arrow([(120, 84), (120, 108)])
    s.box(260, 20, 200, 64, "neutral", "Recreated evaluator", ["Isaac Lab, CPU PhysX"])
    s.box(260, 110, 200, 80, "learned", "PPO skill training", ["GPU, privileged critic,", "randomized physics"])
    s.box(260, 216, 200, 84, "priv", "Privileged teacher", ["task graph, executor,", "skills, exact state"])
    s.arrow([(220, 140), (258, 60)])
    s.arrow([(220, 200), (258, 250)])
    s.arrow([(360, 84), (360, 108)])
    s.arrow([(360, 190), (360, 214)])
    rows = [
        (20, "Rollouts, injected failures", ["labelled by a privileged", "expert; perception errors"], "High-level policy", ["BC, then 3 DAgger rounds"]),
        (112, "Rollouts with DART noise", ["of the planned Task 5", "controllers"], "Task 5 skills", ["behaviour cloning"]),
        (204, "Rendered frames", ["28k, random lighting,", "+ organizer frames"], "Keypoint network", ["supervised heatmaps"]),
        (296, "Perception-error model", ["recorded estimator errors,", "replayed by block class"], "Push fine-tuning", ["PPO under perception", "errors"]),
    ]
    s.line([(460, 258), (480, 258)])
    s.line([(480, 52), (480, 328)])
    for y, t1, l1, t2, l2 in rows:
        s.arrow([(480, y + 32), (498, y + 32)])
        s.box(500, y, 210, 64, "neutral", t1, l1)
        s.box(740, y, 180, 64, "learned", t2, l2)
        s.arrow([(710, y + 32), (738, y + 32)])
    # the keypoint network, run in closed loop, provides the error traces
    s.arrow([(770, 268), (770, 282), (640, 282), (640, 294)], dash=True)
    s.box(500, 410, 420, 72, "neutral", "Student v1.3: one frozen bundle", ["perception, high-level policy, all skills, task plans"])
    s.line([(920, 52), (932, 52), (932, 446)])
    for y, *_ in rows:
        s.line([(920, y + 32), (932, y + 32)])
    s.arrow([(932, 446), (922, 446)])
    s.arrow([(360, 300), (360, 446), (498, 446)])
    s.parts.append('<text class="d-l" x="368" y="420">grasp and place</text><text class="d-l" x="368" y="436">policies, unchanged</text>')
    return s.render()


def main():
    root = Path(__file__).resolve().parents[1]
    p = root / "index.html"
    html = p.read_text()
    for name, fn in (("teacher", teacher), ("student", student), ("pipeline", pipeline)):
        pat = re.compile(rf"(<!-- BEGIN diagram:{name} -->\n).*?(<!-- END diagram:{name} -->)", re.S)
        if not pat.search(html):
            raise SystemExit(f"marker for {name} not found")
        html = pat.sub(lambda m: m.group(1) + fn() + "\n" + m.group(2), html)
    p.write_text(html)
    print("diagrams written")


if __name__ == "__main__":
    main()
