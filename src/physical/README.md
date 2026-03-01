# Physical Robot Data — Replay Guide

This folder contains recorded episode datasets for 5 pick tasks + 2 defect pick tasks collected using an **SO101 follower** arm via LeRobot teleoperation.

## Dataset Structure

```
data/
├── pick_AGR_400/              # AGR-400 component pick task
├── pick_IOT_200/              # IOT-200 component pick task
├── pick_MED_300/              # MED-300 component pick task
├── pick_PCB_IND_100/          # PCB-IND-100 component pick task
├── pick_PCB_PWR_500/          # PCB-PWR-500 component pick task
├── pick_PCB_IND_100_defect/   # PCB-IND-100 defect pick task
└── pick_MED_300_defect/       # MED-300 defect pick task
```

Each dataset folder contains:
- `data/chunk-000/` — recorded episode parquet files
- `meta/info.json` — dataset metadata
- `meta/stats.json` — dataset statistics
- `meta/episodes/` — per-episode metadata

---

## How to Replay Episodes

> **Prerequisites:** Make sure `lerobot` is installed and the SO101 follower arm is connected at `/dev/ttyACM1`.

### Replay Commands

Use the `--dataset.root` path relative to where you run the command. If running from the workspace root (`ILS_Hackathon/`), point to the `physical/data` copy:

**PCB-IND-100:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_PCB_IND_100 \
    --dataset.root=ILS_hackathon/src/physical/data/pick_PCB_IND_100 \
    --dataset.episode=0
```

**MED-300:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_MED_300 \
    --dataset.root=ILS_hackathon/src/physical/data/pick_MED_300 \
    --dataset.episode=0
```

**IOT-200:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_IOT_200 \
    --dataset.root=ILS_hackathon/src/physical/data/pick_IOT_200 \
    --dataset.episode=0
```

**AGR-400:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_AGR_400 \
    --dataset.root=ILS_hackathon/src/physical/data/pick_AGR_400 \
    --dataset.episode=0
```

**PCB-PWR-500:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_PCB_PWR_500 \
    --dataset.root=ILS_hackathon/src/physical/data/pick_PCB_PWR_500 \
    --dataset.episode=0
```

### Defect Datasets

**PCB-IND-100-Defect:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_PCB_IND_100_defect \
    --dataset.root=ILS_hackathon/src/physical/data/pick_PCB_IND_100_defect \
    --dataset.episode=0
```

**MED-300-Defect:**
```bash
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \  # <-- Change to YOUR port (run lerobot-find-port to check)
    --robot.id=Follower \
    --dataset.repo_id=local/pick_MED_300_defect \
    --dataset.root=ILS_hackathon/src/physical/data/pick_MED_300_defect \
    --dataset.episode=0
```

---

## Replaying a Specific Episode

To replay a different episode, change the `--dataset.episode` flag:

```bash
--dataset.episode=1   # replay episode 1 (0-indexed)
```

---

## Notes for Contributors

- **Port setup:** The follower arm must be on `/dev/ttyACM1`. If your port differs, update `--robot.port` accordingly. Run `lerobot-find-port` to discover your port.
- **WSL users:** You need to attach USB devices via `usbipd` in PowerShell before they appear in WSL (see `calibration_notes.txt` in the project root for details).
- **Calibration:** Ensure the follower arm is calibrated before replay. Run:
  ```bash
  lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/ttyACM1 --robot.id=Follower
  ```
- The full calibration and recording reference is in [calibration_notes.txt](../../calibration_notes.txt) at the `ILS_hackathon/` root.
