import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_sid(output_dir="output/analysis"):
    # =========================
    # LOAD DATA
    # =========================
    contacts = np.load(f"{output_dir}/sid_contacts.npy")
    hbonds   = np.load(f"{output_dir}/sid_hbonds.npy")
    salt     = np.load(f"{output_dir}/sid_salt.npy")
    pipi     = np.load(f"{output_dir}/sid_pipi.npy")

    df = pd.read_csv(f"{output_dir}/sid_occupancy.csv")

    # =========================
    # HEATMAP
    # =========================
    combined = contacts + hbonds + salt + pipi

    plt.figure(figsize=(14,6))
    plt.imshow(combined.T, aspect='auto')
    plt.xlabel("Frame")
    plt.ylabel("Residue Index")
    plt.title("Protein–Ligand Interaction Timeline (SID)")
    plt.colorbar(label="Interaction Intensity")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/sid_heatmap.png", dpi=300)
    plt.close()

    # =========================
    # FILTER INTERACTING RESIDUES
    # =========================
    df_filtered = df[(df.iloc[:, 1:] > 0).any(axis=1)]

    if df_filtered.empty:
        print("⚠️ No interacting residues found. Skipping occupancy plot.")
        return

    # =========================
    # SORT BY RESIDUE NUMBER (FIXED)
    # =========================
    df_filtered["resnum"] = df_filtered["Residue"].str.extract(r'(\d+)').astype(int)
    df_filtered = df_filtered.sort_values("resnum")
    df_filtered = df_filtered.drop(columns=["resnum"])

    # =========================
    # PLOT
    # =========================
    df_filtered = df_filtered.set_index("Residue")

    df_filtered.plot(
        kind="bar",
        stacked=True,
        figsize=(14,6)
    )

    plt.ylabel("Occupancy (%)")
    plt.title("Protein-Ligand Contacts")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/sid_occupancy.png", dpi=300)
    plt.close()

    print("SID plots generated")