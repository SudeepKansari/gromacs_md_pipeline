import subprocess
from pathlib import Path

scripts = Path("scripts")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

def run_script(script_name):
    print(f"\n Running {script_name} ...")
    subprocess.run(["python", str(scripts / script_name)], check=True)

pipeline_steps = [
    "01_prepare_complex.py",   # Split protein/ligand
    "02_tleap_system.py",      # Build system with tleap
    "03_convert_parmed.py",    # Convert Amber → GROMACS
    "04_mdp_generator.py",     # Generate MD MDP files
    "05_run_gromacs.py",       # Run GROMACS MD
    "06_analysis.py"           # Analyze trajectory & create PDF
]

try:
    for step in pipeline_steps:
        run_script(step)
    print("\n Molecular dynamics for protein-ligand complex completed successfully!")

except subprocess.CalledProcessError as e:
    print(f"\n Error occurred in step: {e}")