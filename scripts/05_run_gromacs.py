import subprocess
import json
import os
from pathlib import Path

#--- CONFIG ---
cfg = json.load(open("config.json"))

gmx = "gmx_mpi"
output_dir = Path("output/gromacs")
output_dir.mkdir(parents=True, exist_ok=True)

ligand_res = cfg["ligand_resname"]
MAX_WARN = 6

#--- PERFORMANCE SETTINGS ---
NTOMP = int(os.getenv("OMP_NUM_THREADS", "8"))

# GPU detection (safe default)
GPU_IDS = os.getenv("CUDA_VISIBLE_DEVICES", "0")
USE_GPU = GPU_IDS != ""

#--- FILES ---
gro_init = output_dir / "complex.gro"
top_file = output_dir / "topol.top"
ndx_file = output_dir / "index.ndx"

#--- HELPER: RUN COMMAND ---
def run(cmd, input_text=None):
    print(f"\n Running: {' '.join(map(str, cmd))}")
    try:
        subprocess.run(
            cmd,
            input=input_text.encode() if input_text else None,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(" Command failed:", e)
        exit(1)

# 1. INDEX GENERATION 
print(f"\n Generating index for ligand: {ligand_res}")

make_ndx_cmds = f"""
1 | 13
name 18 Protein_LIG
14 | 15
name 19 Water_and_ions
q
"""

run([gmx, "make_ndx", "-f", gro_init, "-o", ndx_file], make_ndx_cmds)

# 2.  GROMPP + MDRUN
def run_md_step(mdp, gro_in, tpr, deffnm, ref_gro=None, use_gpu=True):

    print(f"\n Starting step: {deffnm}")

    # -------- GROMPP --------
    grompp_cmd = [
        gmx, "grompp",
        "-f", str(output_dir / mdp),
        "-c", str(gro_in),
        "-p", str(top_file),
        "-n", str(ndx_file),
        "-o", str(output_dir / tpr),
        "-maxwarn", str(MAX_WARN)
    ]

    if ref_gro:
        grompp_cmd += ["-r", str(ref_gro)]

    run(grompp_cmd)

    # -------- MDRUN --------
    mdrun_cmd = [
        gmx, "mdrun",
        "-deffnm", str(output_dir / deffnm),

        # Parallelism
        "-ntomp", str(NTOMP),

        # Restart support
        "-cpi", str(output_dir / f"{deffnm}.cpt"),

        "-v"
    ]

    if use_gpu and USE_GPU:
        mdrun_cmd += [
            "-nb", "gpu",
            "-pme", "gpu",
            "-bonded", "gpu",
            "-update", "gpu"
        ]

    run(mdrun_cmd)

# 2. PIPELINE EXECUTION

# Energy Minimization
run_md_step("em.mdp", gro_init, "em.tpr", "em", use_gpu=False)

# NVT
run_md_step(
    "nvt.mdp",
    output_dir / "em.gro",
    "nvt.tpr",
    "nvt",
    ref_gro=output_dir / "em.gro",
    use_gpu=True
)

# NPT
run_md_step(
    "npt.mdp",
    output_dir / "nvt.gro",
    "npt.tpr",
    "npt",
    ref_gro=output_dir / "nvt.gro",
    use_gpu=True
)

# Production MD 
run_md_step(
    "md.mdp",
    output_dir / "npt.gro",
    "md.tpr",
    "md",
    use_gpu=True
)

# 3. TRAJECTORY CENTERING
print("\n Centering trajectory...")

centered_traj = output_dir / "md_centered.xtc"

run([
    gmx, "trjconv",
    "-s", str(output_dir / "md.tpr"),
    "-f", str(output_dir / "md.xtc"),
    "-o", str(centered_traj),
    "-n", str(ndx_file),
    "-center",
    "-pbc", "mol"
], input_text="Protein_LIG\nSystem\n")

print(f"\n All outputs saved in {output_dir}")