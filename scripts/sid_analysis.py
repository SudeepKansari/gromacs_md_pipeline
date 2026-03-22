import MDAnalysis as mda
import numpy as np
import pandas as pd
from MDAnalysis.analysis.hydrogenbonds import HydrogenBondAnalysis
from MDAnalysis.lib.distances import distance_array
from pathlib import Path

def run_sid_analysis(tpr, xtc, lig_res, output_dir="output/analysis"):
    u = mda.Universe(tpr, xtc)

    protein = u.select_atoms("protein")
    ligand = u.select_atoms(f"resname {lig_res}")
    residues = protein.residues

    n_frames = len(u.trajectory)
    n_res = len(residues)

    contacts = np.zeros((n_frames, n_res))
    hbonds = np.zeros((n_frames, n_res))
    salt = np.zeros((n_frames, n_res))
    pipi = np.zeros((n_frames, n_res))

    hbond = HydrogenBondAnalysis(
    universe=u,
    donors_sel="protein",
    acceptors_sel=f"resname {lig_res}",
    d_a_cutoff=3.5,
    d_h_a_angle_cutoff=120
    )
    hbond.run()

    for i, ts in enumerate(u.trajectory):
        for j, res in enumerate(residues):
            d = distance_array(res.atoms.positions, ligand.positions)

            if np.any(d < 4.5):
                contacts[i, j] = 1

            if res.resname in ["ASP","GLU","LYS","ARG"]:
                if np.any(d < 4.0):
                    salt[i, j] = 1

            if res.resname in ["PHE","TYR","TRP"]:
                if np.any(d < 5.0):
                    pipi[i, j] = 1

    for hb in hbond.results.hbonds:
        frame = int(hb[0])
        atom = u.atoms[int(hb[1])]
        resid = atom.resid

        for j, r in enumerate(residues):
            if r.resid == resid:
                hbonds[frame, j] = 1

    out = Path(output_dir)
    np.save(out/"sid_contacts.npy", contacts)
    np.save(out/"sid_hbonds.npy", hbonds)
    np.save(out/"sid_salt.npy", salt)
    np.save(out/"sid_pipi.npy", pipi)

    df = pd.DataFrame({
        "Residue":[f"{r.resname}{r.resid}" for r in residues],
        "Contacts (%)":contacts.mean(0)*100,
        "H-bonds (%)":hbonds.mean(0)*100,
        "Salt (%)":salt.mean(0)*100,
        "Pi-Pi (%)":pipi.mean(0)*100
    })

    df.to_csv(out/"sid_occupancy.csv", index=False)