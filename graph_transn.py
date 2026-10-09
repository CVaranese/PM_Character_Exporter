import csv
import matplotlib.pyplot as plt

CSV_PATH = "./transn_keyframes.csv"
ANIM_NAME = "SpecialAirHi"

frames, xs, ys, zs = [], [], [], []

with open(CSV_PATH, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['animation'] == ANIM_NAME:
            frames.append(int(row['frame']))
            xs.append(float(row['x']))
            ys.append(float(row['y']))
            zs.append(float(row['z']))

def velocity(frames, values):
    """Average velocity between each consecutive keyframe pair, placed at the midpoint frame."""
    mid, vel = [], []
    for i in range(len(frames) - 1):
        dt = frames[i + 1] - frames[i]
        mid.append((frames[i] + frames[i + 1]) / 2)
        vel.append((values[i + 1] - values[i]) / dt)
    return mid, vel

fig, (ax_pos, ax_vel, ax_acc) = plt.subplots(3, 1, figsize=(12, 14), sharex=True)

# Position
ax_pos.plot(frames, xs, marker='o', label='X')
ax_pos.plot(frames, ys, marker='o', label='Y')
ax_pos.plot(frames, zs, marker='o', label='Z')
ax_pos.set_title(f"TransN keyframes — {ANIM_NAME}")
ax_pos.set_ylabel("Position")
ax_pos.legend()
ax_pos.grid(True)

# Velocity (derived)
mx, vx = velocity(frames, xs)
my, vy = velocity(frames, ys)
mz, vz = velocity(frames, zs)

ax_vel.plot(mx, vx, marker='o', label='X')
ax_vel.plot(my, vy, marker='o', label='Y')
ax_vel.plot(mz, vz, marker='o', label='Z')
ax_vel.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax_vel.set_title("Derived velocity (Δposition / Δframe)")
ax_vel.set_xlabel("Frame")
ax_vel.set_ylabel("Velocity (units/frame)")
ax_vel.legend()
ax_vel.grid(True)

# Acceleration (derived from velocity)
ma, ay = velocity(my, vy)
_, ax_ = velocity(mx, vx)
_, az = velocity(mz, vz)

ax_acc.plot(ma, ax_, marker='o', label='X')
ax_acc.plot(ma, ay, marker='o', label='Y')
ax_acc.plot(ma, az, marker='o', label='Z')
ax_acc.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax_acc.set_title("Derived acceleration (Δvelocity / Δframe)")
ax_acc.set_xlabel("Frame")
ax_acc.set_ylabel("Acceleration (units/frame²)")
ax_acc.legend()
ax_acc.grid(True)

plt.tight_layout()
plt.show()
