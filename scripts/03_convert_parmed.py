import parmed as pmd
from pathlib import Path

amber_top = "output/amber/complex.prmtop"
amber_crd = "output/amber/complex.inpcrd"

# --- Load Amber system ---
system = pmd.load_file(amber_top, amber_crd)

gmx_dir = Path("output/gromacs")
gmx_dir.mkdir(parents=True, exist_ok=True)

# --- Save in GROMACS format ---
system.save(str(gmx_dir / "complex.gro"))
system.save(str(gmx_dir / "topol.top"))

print("Converted Amber files to GROMACS format.")