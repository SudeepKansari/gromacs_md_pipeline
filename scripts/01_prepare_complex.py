import json
import subprocess
from pathlib import Path
from MDAnalysis import Universe

cfg = json.load(open("config.json"))

resname = cfg.get("ligand_resname")
if not resname:
    raise KeyError("ligand_resname missing from config.json")

protein_pdb = cfg["protein_pdb"]
output_dir = Path("output/protein_ligand_prepared")
output_dir.mkdir(parents=True, exist_ok=True)

u = Universe(protein_pdb)
protein_atoms = u.select_atoms("protein")
ligand_atoms = u.select_atoms(f"resname {resname}")

prot_raw = output_dir / "protein_split.pdb"
lig_raw = output_dir / "ligand.pdb"
lig_h_pdb = output_dir / "ligand_h.pdb" 

protein_atoms.write(str(prot_raw))
ligand_atoms.write(str(lig_raw))

# --- CLEANUP PROTEIN ---
with open(prot_raw, "r") as f:
    lines = [line for line in f if not line.startswith("CONECT")]
with open(prot_raw, "w") as f:
    f.writelines(lines)

# --- PROTEIN PREPARATION ---
protein_file = output_dir / "protein.pdb"
subprocess.run([
    "pdb4amber",
    "-i", str(prot_raw),
    "-o", str(protein_file),
    "--nohyd"
], check=True)

# --- LIGAND PREPARATION: TRY RAW FIRST ---
mol2_file = lig_raw.with_suffix(".mol2")
frcmod_file = lig_raw.with_suffix(".frcmod")

def run_antechamber(input_file):
    subprocess.run([
        "antechamber",
        "-i", str(input_file),
        "-fi", "pdb",
        "-o", str(mol2_file),
        "-fo", "mol2",
        "-c", "bcc",
        "-at", "gaff2",              
        "-rn", resname,
        "-nc", "0",  
        "-pf", "y"   
    ], check=True, capture_output=True, text=True)

try:
    print(f"Attempting antechamber on raw ligand: {lig_raw}")
    # Strip CONECT from raw 
    with open(lig_raw, "r") as f:
        lines = [l for l in f if not l.startswith("CONECT")]
    with open(lig_raw, "w") as f:
        f.writelines(lines)
        
    run_antechamber(lig_raw)
    print("Success: Raw ligand processed.")

except subprocess.CalledProcessError:
    print("Raw ligand failed. Running 'reduce' to fix hydrogens and retrying...")
    
    # 1. Add hydrogens
    with open(lig_h_pdb, "w") as f_out:
        subprocess.run(["reduce", "-Build", str(lig_raw)], 
                       stdout=f_out, stderr=subprocess.PIPE, check=True)
    
    # 2. Strip CONECT from reduced file
    with open(lig_h_pdb, "r") as f:
        lines = [line for line in f if not line.startswith("CONECT")]
    with open(lig_h_pdb, "w") as f:
        f.writelines(lines)
    
    # 3. Retry Antechamber
    try:
        run_antechamber(lig_h_pdb)
        print("Success: Ligand processed after reduction.")
    except subprocess.CalledProcessError as e:
        print(f"Antechamber failed again: {e.stderr}")
        raise

# --- PARMCHK2 ---
subprocess.run([
    "parmchk2",
    "-i", str(mol2_file),
    "-f", "mol2",
    "-o", str(frcmod_file)
], check=True)

print(f"Protein and ligand prepared: {protein_file}, {mol2_file}, and {frcmod_file}")
