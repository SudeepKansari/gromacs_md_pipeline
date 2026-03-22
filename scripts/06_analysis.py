import subprocess
import json
import shutil
from pathlib import Path

cfg = json.load(open("config.json"))
lig_res = cfg["ligand_resname"]

output_dir = Path("output/analysis")
output_dir.mkdir(parents=True, exist_ok=True)

gmx = "gmx_mpi"
tpr = "output/gromacs/md.tpr"
xtc = "output/gromacs/md_centered.xtc"
ndx = "output/gromacs/index.ndx"

def run_gmx(cmd, input_str, output_file, output_flag="-o"):
    full_cmd = list(cmd) + [output_flag, str(output_dir / output_file)]
    if Path(ndx).exists():
        full_cmd += ["-n", ndx]
    subprocess.run(full_cmd, input=input_str.encode(), check=True, capture_output=True)

def set_xvg_title(filename, title, subtitle=""):
    path = output_dir / filename
    if not path.exists(): 
        return
    with open(path, "r") as f:
        lines = f.readlines()
    header = [f'@ title "{title}"\n']
    if subtitle:  
        header.append(f'@ subtitle "{subtitle}"\n')
    new_content = header + lines
    with open(path, "w") as f:
        f.writelines(new_content)

run_gmx([gmx, "rms", "-s", tpr, "-f", xtc, "-tu", "ps"], "3\n3\n", "rmsd_prot.xvg")
run_gmx([gmx, "rms", "-s", tpr, "-f", xtc, "-tu", "ps"], f"3\n13\n", "rmsd_lig.xvg")

run_gmx([gmx, "rmsf", "-s", tpr, "-f", xtc, "-res"], "1\n", "rmsf_prot.xvg")
set_xvg_title("rmsf_prot.xvg", "Protein RMS Fluctuation", "Per-residue")

run_gmx([gmx, "rmsf", "-s", tpr, "-f", xtc], "13\n", "rmsf_lig.xvg")
set_xvg_title("rmsf_lig.xvg", f"Ligand ({lig_res}) RMS Fluctuation", "Per-atom")

run_gmx([gmx, "gyrate", "-s", tpr, "-f", xtc], "1\n", "gyrate.xvg")
set_xvg_title("gyrate.xvg", "Radius of gyration (total and around axes)", "Rg")

run_gmx([gmx, "sasa", "-s", tpr, "-f", xtc], "1\n", "sasa.xvg")
set_xvg_title("sasa.xvg", "Solvent Accessible Surface", "Total")

run_gmx([gmx, "hbond", "-s", tpr, "-f", xtc], f"1\n13\n", "hbonds.xvg", output_flag="-num")
set_xvg_title("hbonds.xvg", "Hydrogen bonds", "Number of hydrogen bonds")

label_in = output_dir / "label.in"
label_content = f"""READ NXY "{output_dir}/rmsd_prot.xvg"
READ NXY "{output_dir}/rmsd_lig.xvg"
s0 line color 1
s1 line color 2
s0 legend "Protein C-alpha"
s1 legend "{lig_res} Ligand"
title "RMSD"
subtitle "{lig_res} after lsq fit to Protein"
xaxis label "Time (ps)"
yaxis label "RMSD (nm)"
"""
label_in.write_text(label_content)

rmsd_ps = output_dir / "rmsd_combined.ps"
subprocess.run(["gracebat", "-nosafe", "-batch", str(label_in), 
                "-hdevice", "PostScript", "-hardcopy", "-printfile", str(rmsd_ps)], check=True)

def xvg_to_ps(xvg_list, output_name):
    ps_file = output_dir / f"{output_name}.ps"
    cmd = ["gracebat", "-nosafe", "-nxy"] + [str(output_dir/f) for f in xvg_list] + ["-hdevice", "PostScript", "-hardcopy", "-printfile", str(ps_file)]
    subprocess.run(cmd, check=True)
    return ps_file

other_ps = []
for xvg, name in [("rmsf_prot.xvg", "rmsf_protein"), ("rmsf_lig.xvg", "rmsf_ligand"), 
                  ("gyrate.xvg", "gyration"), ("sasa.xvg", "sasa"), ("hbonds.xvg", "hbonds")]:
    ps = xvg_to_ps([xvg], name)
    other_ps.append(ps)

ps_files = [rmsd_ps] + other_ps

final_pdf = output_dir / "MD_Analysis_Report.pdf"
subprocess.run(["gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", f"-sOutputFile={final_pdf}"] + [str(p) for p in ps_files], check=True)

for p in ps_files: p.unlink()
label_in.unlink()

from sid_analysis import run_sid_analysis
from sid_plot import plot_sid
run_sid_analysis(tpr, xtc, lig_res)
plot_sid()

print("Analysis complete")