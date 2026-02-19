from heatmap_funcs import * 
import glob
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import time

# **********************  update scalars list as desired. *********** **************

scalars = [0.1] 
# each value 's' in the scalar list is a parameter which determines the 'blurriness' or spread of each fixation heat point.
# i.e. if you want to generate a set of heatmaps for just one value of s, update the list to contain only 1 value.

# ********************  ^ update scalars list as desired. *********** **************

# Load config data
with open("config.yaml") as f:
        config = yaml.safe_load(f)
canonical_item_file = config["canonical_info"]["canonical_item_file"]

csv_files = glob.glob("out/*.csv") # where canonical mappings are stored
#############################################
# STEP 0:  Split the generated mapped-to-canonical-fixation-report csvs by condition

# Create 4 dfs: 1 for each condition:
    # A) 'scientific-pseudo'
    # B) 'everyday-pseudo'
    # C) 'scientiic-real'
    # D) 'scientif-pseudo'
#############################################

csv_pattern = "out/*.csv" # this is where the csvs are stored if previous steps were followed
condition_dfs = load_and_split_by_condition(csv_pattern)

#############################################

canon_ia_df = pd.read_csv(canonical_item_file)
AOI_xy_wh = list(zip(canon_ia_df['IA_LEFT'], canon_ia_df['IA_TOP'], canon_ia_df['IA_RIGHT'] - canon_ia_df['IA_LEFT'],canon_ia_df['IA_BOTTOM'] - canon_ia_df['IA_TOP']  ))
AOI_x_bounds = list(zip(canon_ia_df['IA_LEFT'], canon_ia_df['IA_RIGHT']))

# Extract word with info: this guides the gaussian modeling of each fixation pt's heat spot.
word_widths = [x_max - x_min for x_min, x_max in AOI_x_bounds]
avg_word_width = np.mean(word_widths)
max_word_width = np.max(word_widths)

# For each value of s, we create an average heatmap per condition.
for s in scalars:
    print(f"-------- Generating heatmaps for s={s} ----------\n")
    start = time.time()
    conditions = {
        "scientific_pseudo": condition_dfs["scientific_pseudo"],
        "everyday_pseudo": condition_dfs["everyday_pseudo"],
        "scientific_real": condition_dfs["scientific_real"],
        "everyday_real": condition_dfs["everyday_real"]
    }
    
    # create the average heatmap per condition
    for condition_name, df in conditions.items():
        print(f"Generating average heatmap for condition '{condition_name}'")
        # Make sure the pid col exists
        assert 'RECORDING_SESSION_LABEL' in df.columns, "no RECORDING_SESSION_LABEL col in df"
        
        ''' 
        
        # for testing on a subset
        # just update df below to df_subset

        # Get first n unique participants
        num_participants = 10
        unique_participants = df['RECORDING_SESSION_LABEL'].unique()[:num_participants]
        df_subset = df[df['RECORDING_SESSION_LABEL'].isin(unique_participants)]'''


        unique_trials_total = df.groupby('RECORDING_SESSION_LABEL')['TRIAL_INDEX'].nunique().sum()
        print(f"Total number of trials to generate heatmaps for in this condition (num. participants x 2 per participant): {unique_trials_total}")

        # Prepare grid
        X, Y, extent = prepare_grid(AOI_xy_wh)
        
        # Generate average heatmap across all participants in the codnition
        SIGMA = s * avg_word_width # standard distribution of the gaussian
        heatmap = average_heatmap(df, SIGMA, X, Y) # creates indiv. heatmaps per trial, then averages across all items in the condition
        heatmap /= np.max(heatmap) # normalize the average heatmap per condition
        print(f"Done generating average heatmap for condition '{condition_name}'.\n")

        # Save heat map raw data (for e.g. wanting to re-do plotting later w/o having to re-generate heatmaps)
        outdirheatmaps = Path("heatmaps")
        outdirheatmaps.mkdir(exist_ok=True)

        saved_maps = Path("heatmaps/saved_heatmap_data")
        saved_maps.mkdir(exist_ok=True)

        np.savez(
            saved_maps / f"{condition_name}_{s}_heatmap.npz",
            heatmap=heatmap,
            extent=extent,
            AOI_xy_wh=AOI_xy_wh,
            sigma=SIGMA
        )

        # Plot
        plot_heatmap(heatmap, AOI_xy_wh, extent,condition_name,s)

    end = time.time()
    print(f"Time took to generate average heatmaps for 4 conditions, num. participants = {num_participants}: {end-start}s")


