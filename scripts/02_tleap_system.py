import json
import subprocess
from pathlib import Path

cfg = json.load(open("config.json"))

protein_file = Path("output/protein_ligand_prepared/protein.pdb")
ligand_mol2 = Path("output/protein_ligand_prepared/ligand.mol2")
ligand_frcmod = Path("output/protein_ligand_prepared/ligand.frcmod")

output_dir = Path(cfg.get("amber_output_dir", "output/amber"))
output_dir.mkdir(parents=True, exist_ok=True)

# --- TLEAP SCRIPT ---
tleap_script = f"""
# -----------------------------
# Force fields: ff19SB
# -----------------------------
source leaprc.protein.ff19SB 
source leaprc.gaff2
source leaprc.water.tip3p

# -----------------------------
# Load protein and ligand
# -----------------------------
protein = loadpdb "{protein_file}"
ligand  = loadmol2 "{ligand_mol2}"
loadamberparams "{ligand_frcmod}"

# -----------------------------
# Combine
# -----------------------------
complex = combine {{ protein ligand }}

# -----------------------------
# Solvate
# -----------------------------
solvate{cfg['box_type']} complex TIP3PBOX {cfg['box_distance']}

# -----------------------------
# Neutralize / add salt
# -----------------------------
addions complex Na+ 0
addions complex Cl- 0

# -----------------------------
# Save output
# -----------------------------
saveamberparm complex "{output_dir}/complex.prmtop" "{output_dir}/complex.inpcrd"
savepdb complex "{output_dir}/complex.pdb"

quit
"""

tleap_input = output_dir / "tleap.in"
tleap_input.write_text(tleap_script)

subprocess.run(["tleap", "-f", str(tleap_input)], check=True)

print(f"TLeap system prepared successfully! Files saved in {output_dir}")