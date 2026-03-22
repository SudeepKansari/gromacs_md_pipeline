import json
from pathlib import Path

cfg = json.load(open("config.json"))
output_dir = Path("output/gromacs")
output_dir.mkdir(parents=True, exist_ok=True)

def write(filename, content):
    filepath = output_dir / filename
    with open(filepath, "w") as f:
        f.write(content.strip() + "\n")

TEMP = cfg["temperature"]
PRESS = cfg["pressure"]

#--- ENERGY MINIMIZATION ---

write("em.mdp", f"""
title           = Minimization

integrator      = steep
emtol           = 1000.0
emstep          = 0.01
nsteps          = 50000

nstlist         = 1
cutoff-scheme   = Verlet
ns_type         = grid
rlist           = 1.2

coulombtype     = PME
rcoulomb        = 1.2

vdwtype         = cutoff
vdw-modifier    = force-switch
rvdw-switch     = 1.0
rvdw            = 1.2

pbc             = xyz
DispCorr        = no
""")

#--- NVT ---

write("nvt.mdp", f"""
title                   = Protein-ligand complex NVT equilibration
define                  = -DPOSRES

integrator              = md
nsteps                  = {cfg["nvt_steps"]}
dt                      = 0.002

nstenergy               = 500
nstlog                  = 500
nstxout-compressed      = 500

continuation            = no
constraint_algorithm    = lincs
constraints             = h-bonds
lincs_iter              = 1
lincs_order             = 4

cutoff-scheme           = Verlet
ns_type                 = grid
nstlist                 = 20
rlist                   = 1.2

vdwtype                 = cutoff
vdw-modifier            = force-switch
rvdw-switch             = 1.0
rvdw                    = 1.2

coulombtype             = PME
rcoulomb                = 1.2
pme_order               = 4
fourierspacing          = 0.16

tcoupl                  = V-rescale
tc-grps                 = Protein_LIG Water_and_ions
tau_t                   = 0.1 0.1
ref_t                   = {TEMP} {TEMP}

pcoupl                  = no

pbc                     = xyz
DispCorr                = no

gen_vel                 = yes
gen_temp                = {TEMP}
gen_seed                = -1
""")

#--- NPT ---

write("npt.mdp", f"""
title                   = Protein-ligand complex NPT equilibration
define                  = -DPOSRES

integrator              = md
nsteps                  = {cfg["npt_steps"]}
dt                      = 0.002

nstenergy               = 500
nstlog                  = 500
nstxout-compressed      = 500

continuation            = yes
constraint_algorithm    = lincs
constraints             = h-bonds
lincs_iter              = 1
lincs_order             = 4

cutoff-scheme           = Verlet
ns_type                 = grid
nstlist                 = 20
rlist                   = 1.2

vdwtype                 = cutoff
vdw-modifier            = force-switch
rvdw-switch             = 1.0
rvdw                    = 1.2

coulombtype             = PME
rcoulomb                = 1.2
pme_order               = 4
fourierspacing          = 0.16

tcoupl                  = V-rescale
tc-grps                 = Protein_LIG Water_and_ions
tau_t                   = 0.1 0.1
ref_t                   = {TEMP} {TEMP}

pcoupl                  = Berendsen
pcoupltype              = isotropic
tau_p                   = 2.0
ref_p                   = {PRESS}
compressibility         = 4.5e-5
refcoord_scaling        = com

pbc                     = xyz
DispCorr                = no

gen_vel                 = no
""")

#--- PRODUCTION MD ---

write("md.mdp", f"""
title                   = Protein-ligand complex MD simulation

integrator              = md
nsteps                  = {cfg["md_steps"]}
dt                      = 0.002

nstenergy               = 5000
nstlog                  = 5000
nstxout-compressed      = 5000

continuation            = yes
constraint_algorithm    = lincs
constraints             = h-bonds
lincs_iter              = 1
lincs_order             = 4

cutoff-scheme           = Verlet
ns_type                 = grid
nstlist                 = 20
rlist                   = 1.2

vdwtype                 = cutoff
vdw-modifier            = force-switch
rvdw-switch             = 1.0
rvdw                    = 1.2

coulombtype             = PME
rcoulomb                = 1.2
pme_order               = 4
fourierspacing          = 0.16

tcoupl                  = V-rescale
tc-grps                 = Protein_LIG Water_and_ions
tau_t                   = 0.1 0.1
ref_t                   = {TEMP} {TEMP}

pcoupl                  = Parrinello-Rahman
pcoupltype              = isotropic
tau_p                   = 2.0
ref_p                   = {PRESS}
compressibility         = 4.5e-5

pbc                     = xyz
DispCorr                = no

gen_vel                 = no
""")

print("MDP files generated")