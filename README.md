# Plans from Demonstrations, Skills from Reinforcement Learning

A blog post by Visak Kumar: *Plans from Demonstrations, Skills from Reinforcement Learning: An agentic teacher and
student for long-horizon bimanual tower manipulation*. It describes our entry to the TOWER challenge at the G2A
workshop (CoRL 2026): reinforcement-learned contact skills run by an agentic controller in simulation, distilled into
a camera-only student.

Live at https://visakk.github.io/agentic-tower/

Code and reproduction scripts: https://github.com/VisakK/tower_rl

- `index.html`: the post (static, no build step; equations rendered by KaTeX from a CDN)
- `assets/img/`: figures, video posters and the preview image
- `assets/video/`: the per-task clips, the teaser loop and the full video (H.264)
- `tools/`: scripts that regenerate the diagrams (`diagrams.py`), the perception figure (`perception_figure.py`) and
  the video clips (`make_media.py`) from the project's renders

All results are in simulation (Isaac Sim and Isaac Lab, PhysX). Demonstration frames and the station and block assets
are from TOWER-SimData and TOWER-Assets by the TOWER Benchmark contributors (CC BY 4.0), cropped, re-rendered and
annotated by us; this post is not affiliated with or endorsed by the organizers.
