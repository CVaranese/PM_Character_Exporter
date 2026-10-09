import csv
import numpy as np
import matplotlib.pyplot as plt

CSV_PATH   = "./transn_keyframes.csv"
ANIM_NAME  = "SpecialAirHi"
FPS        = 60
SCALE      = 10.666   # animation-units → UE units
N_TERM     = 5         # last N keyframes treated as terminal velocity (linear fit)

# Palette (dataviz skill — light mode, categorical slots)
C_DATA      = '#2a78d6'   # slot 1 blue   — raw keyframes
C_FIT_ASC   = '#e34948'   # slot 6 red    — ascent parabola
C_FIT_DESC  = '#eda100'   # slot 3 yellow — descent curve parabola
C_FIT_TERM  = '#4a3aa7'   # slot 5 violet — terminal linear
C_FIT_Z_LIN = '#e34948'   # slot 6 red    — Z linear fit  (Z panel only)
C_FIT_Z_QD  = '#eda100'   # slot 3 yellow — Z quad fit    (Z panel only)
C_GRID      = '#e1e0d9'
C_AXIS      = '#c3c2b7'
C_INK       = '#0b0b0b'
C_INK_SEC   = '#52514e'
SURFACE     = '#fcfcfb'

# --- Load data ---
frames, ys, zs = [], [], []
with open(CSV_PATH, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['animation'] == ANIM_NAME:
            frames.append(int(row['frame']))
            ys.append(float(row['y']))
            zs.append(float(row['z']))

frames = np.array(frames)
ys     = np.array(ys)
zs     = np.array(zs)

# --- Find motion start ---
start_idx   = next(i for i in range(1, len(frames)) if abs(ys[i]) > 1e-3 or abs(zs[i]) > 1e-3)
start_frame = frames[start_idx - 1]
t           = (frames - start_frame).astype(float)
mask        = t >= 0
t_all, y_all, z_all, f_all = t[mask], ys[mask], zs[mask], frames[mask]

# --- Fit Y ascending ---
peak_idx      = int(np.argmax(y_all))
t_asc, y_asc = t_all[:peak_idx + 1], y_all[:peak_idx + 1]
yc_asc        = np.polyfit(t_asc, y_asc, 2)
gravity_asc   = yc_asc[0] * 2.0
v_y0          = yc_asc[1]           # continuous parabola initial velocity
v_y0_sim      = v_y0 + gravity_asc / 2  # discrete equivalent: pos += vel before gravity

# --- Fit Y descent: parabolic curve phase + linear terminal phase ---
# Curve portion: peak through the first terminal keyframe (shared boundary point)
t_desc_curve = t_all[peak_idx:-N_TERM + 1]
y_desc_curve = y_all[peak_idx:-N_TERM + 1]
# Terminal portion: last N_TERM keyframes
t_desc_term  = t_all[-N_TERM:]
y_desc_term  = y_all[-N_TERM:]

yc_desc      = np.polyfit(t_desc_curve, y_desc_curve, 2)
gravity_desc = yc_desc[0] * 2.0

yc_term      = np.polyfit(t_desc_term, y_desc_term, 1)
terminal_y   = float(yc_term[0])   # slope = terminal velocity

# --- Fit Z ---
zc1       = np.polyfit(t_all, z_all, 1)
zc2       = np.polyfit(t_all, z_all, 2)
z_vel_lin = float(zc1[0])
z_vel_q   = float(zc2[1])
z_acc_q   = float(zc2[0]) * 2.0
ss        = np.sum((z_all - z_all.mean()) ** 2)
r2_lin    = 1 - np.sum((z_all - np.polyval(zc1, t_all)) ** 2) / ss
r2_quad   = 1 - np.sum((z_all - np.polyval(zc2, t_all)) ** 2) / ss

# --- Print ---
def ue(v, per='frame'):
    return f"{v:+.4f} au/{per}  →  {v * SCALE:+.4f} UE/{per}"

sep = "─" * 62
print(f"\n{sep}")
print(f"  {ANIM_NAME} — Extracted Motion Parameters  (scale = {SCALE})")
print(sep)
print(f"  Motion onset       : frame {start_frame} → {start_frame + 1}")
print(f"  Y peak             : frame {f_all[peak_idx]}  (t = {int(t_all[peak_idx])})")
print(f"  Terminal vel onset : frame {f_all[-N_TERM]}  (last {N_TERM} keyframes)")
print()
print("  Y axis (vertical)")
print(f"    Rise gravity (ascent fit)  : {ue(gravity_asc, 'frame²')}  ({gravity_asc * SCALE * FPS**2:+.2f} UE/sec²)")
print(f"    Fall gravity (descent fit) : {ue(gravity_desc, 'frame²')}  ({gravity_desc * SCALE * FPS**2:+.2f} UE/sec²)")
print(f"    Ratio fall/rise            : {gravity_desc / gravity_asc:.2f}×")
print()
print(f"    Initial velocity : {ue(v_y0)}  ({v_y0 * SCALE * FPS:+.2f} UE/sec)")
print(f"    Terminal vel     : {ue(terminal_y)}  ({terminal_y * SCALE * FPS:+.2f} UE/sec)")
print()
print("  Z axis (forward)")
print(f"    Linear fit  v   : {ue(z_vel_lin)}  ({z_vel_lin * SCALE * FPS:+.2f} UE/sec)   R²={r2_lin:.5f}")
print(f"    Quad fit    v₀  : {ue(z_vel_q)}   R²={r2_quad:.5f}")
print(f"    Quad fit    a   : {z_acc_q:+.6f} au/frame²  →  {z_acc_q * SCALE:+.6f} UE/frame²")
print()
print(f"  Unreal Engine windows")
print(f"    Frame {start_frame + 1:>2}: Set Velocity Y   = {v_y0_sim * SCALE:+.4f} UE/frame  ({v_y0_sim * SCALE * FPS:+.2f} UE/sec)")
print(f"    Frame {start_frame + 1:>2}: Set Velocity Z   = {z_vel_lin * SCALE:+.4f} UE/frame  ({z_vel_lin * SCALE * FPS:+.2f} UE/sec)")
print(f"    Rise gravity     = {abs(gravity_asc)  * SCALE:.4f} UE/frame²  ({abs(gravity_asc)  * SCALE * FPS**2:.2f} UE/sec²)  [while vel > 0]")
print(f"    Fall gravity     = {abs(gravity_desc) * SCALE:.4f} UE/frame²  ({abs(gravity_desc) * SCALE * FPS**2:.2f} UE/sec²)  [while vel < 0]")
print(f"    Terminal Y       = {terminal_y * SCALE:+.4f} UE/frame  ({terminal_y * SCALE * FPS:+.2f} UE/sec)")
print(f"{sep}\n")

# --- Plot ---
t_dense      = np.linspace(0, t_all[-1], 600)
t_dense_asc  = np.linspace(0, t_all[peak_idx], 300)
t_dense_desc = np.linspace(t_all[peak_idx], t_all[-N_TERM], 300)
t_dense_term = np.linspace(t_all[-N_TERM], t_all[-1], 100)

fig, (ax_y, ax_z) = plt.subplots(2, 1, figsize=(12, 9), sharex=True, facecolor=SURFACE)

for ax in (ax_y, ax_z):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=C_GRID, linewidth=0.8, zorder=0)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color(C_AXIS)
    ax.tick_params(colors=C_INK_SEC, labelsize=10)

# Y panel
ax_y.scatter(f_all, y_all, color=C_DATA, s=60, zorder=5, label='Y keyframes')
ax_y.plot(t_dense_asc  + start_frame, np.polyval(yc_asc,  t_dense_asc),
          color=C_FIT_ASC, lw=2, ls='--', zorder=4,
          label=f'Ascent parabola   g = {gravity_asc:.4f}')
ax_y.plot(t_dense_desc + start_frame, np.polyval(yc_desc, t_dense_desc),
          color=C_FIT_DESC, lw=2, ls='--', zorder=4,
          label=f'Descent parabola  g = {gravity_desc:.4f}')
ax_y.plot(t_dense_term + start_frame, np.polyval(yc_term, t_dense_term),
          color=C_FIT_TERM, lw=2, ls='--', zorder=4,
          label=f'Terminal linear   v = {terminal_y:.4f}')
ax_y.axvline(start_frame + 1, color=C_AXIS, lw=1, ls=':')
ax_y.axhline(0, color=C_AXIS, lw=0.8)
ax_y.set_ylabel("Y Position (anim-units)", color=C_INK_SEC, fontsize=10)
ax_y.set_title(f"{ANIM_NAME} — Fitted Motion Model", color=C_INK, fontsize=12, pad=10)
ax_y.legend(frameon=False, fontsize=9, labelcolor=C_INK_SEC)

# Z panel
ax_z.scatter(f_all, z_all, color=C_DATA, s=60, zorder=5, label='Z keyframes')
ax_z.plot(t_dense + start_frame, np.polyval(zc1, t_dense),
          color=C_FIT_Z_LIN, lw=2, ls='--', zorder=4,
          label=f'Linear  v = {z_vel_lin:.4f}   R² = {r2_lin:.5f}')
ax_z.plot(t_dense + start_frame, np.polyval(zc2, t_dense),
          color=C_FIT_Z_QD, lw=2, ls=':', zorder=4,
          label=f'Quad    v₀ = {z_vel_q:.4f}  a = {z_acc_q:.5f}   R² = {r2_quad:.5f}')
ax_z.axvline(start_frame + 1, color=C_AXIS, lw=1, ls=':')
ax_z.axhline(0, color=C_AXIS, lw=0.8)
ax_z.set_ylabel("Z Position (anim-units)", color=C_INK_SEC, fontsize=10)
ax_z.set_xlabel("Frame", color=C_INK_SEC, fontsize=10)
ax_z.legend(frameon=False, fontsize=9, labelcolor=C_INK_SEC)

plt.tight_layout()
plt.show()
