import pandas as pd
import glob 
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import multivariate_normal
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches



def load_and_split_by_condition(csv_path_pattern, conditions=None):

    """
    Loads multiple CSVs and splits their rows into separate DataFrames
    based on the 'condition' column.

    Parameters:
        csv_path_pattern (str): Glob pattern for CSV files, e.g. 'output/*.csv'
        conditions (list of str, optional): List of condition names to split by.
            Default: ["scientific_pseudo", "everyday_pseudo", "scientific_real", "everyday_real"]

    Returns:
        dict: key: condition name  value: concatenated DataFrame of all rows from csvs which match the condition
    """
    if conditions is None:
        conditions = ["scientific_pseudo", "everyday_pseudo", "scientific_real", "everyday_real"]

    # Find all matching CSV files
    csv_files = glob.glob(csv_path_pattern)

    # Initialize empty DataFrames for each condition
    condition_to_df = {cond: pd.DataFrame() for cond in conditions}

    for file in csv_files:
        df = pd.read_csv(file)
        assigned_count = 0

        for condition in conditions:
            mask = df["condition"] == condition
            rows_to_add = df[mask]

            if not rows_to_add.empty:
                condition_to_df[condition] = pd.concat(
                    [condition_to_df[condition], rows_to_add], ignore_index=True
                )
                assigned_count += len(rows_to_add)

        # Ensure every row was assigned to exactly one condition
        total_rows = len(df)
        assert assigned_count == total_rows, f"Some rows in {file} did not map to any condition!"

    return condition_to_df

########################################################

def prepare_grid(aois, padding=50):
    """
    aois: list of (x, y, widht, height) in canonical coords
    padding: extra space around AOIs (pixels), to ensure grid cover some space around the stimuli

    creates a 2D pixel grid, which will be used for heatmap generation in matplotlib.
    defines the extent, i.e. height and width of the heatmap in pixels

    """
    lefts   = [x for x, _, _, _ in aois]
    rights  = [x + w for x, _, w, _ in aois]
    tops    = [y for _, y, _, _ in aois]
    bottoms = [y + h for _, y, _, h in aois]

    min_x = min(lefts)   - padding
    max_x = max(rights)  + padding
    min_y = min(tops)    - padding
    max_y = max(bottoms) + padding

    X, Y = np.meshgrid(
        np.arange(min_x, max_x + 1),
        np.arange(min_y, max_y + 1)
    ) # matrix of coordinates for the heatmap

    extent = (min_x, max_x, max_y, min_y)

    return X, Y, extent 

########################################################

def fixation_gaussian(x0, y0, duration, sigma, X, Y):
    dx = X - x0
    dy = Y - y0
    gaussian = np.exp(-(dx**2 + dy**2) / (2 * sigma**2))
    gaussian *= duration

    # optional: remove outer 10% probability mass
    mask = dx**2 + dy**2 <= (2.146 * sigma)**2
    gaussian *= mask

    return gaussian


def average_heatmap(df, sigma, X, Y):
    '''
    computes the average heatmap across participants.
    df: full df containing all participants, with PIDs labeled by col 'RECORDING_SESSION_LABEL'

    '''
    participant_maps = []
    pidnum = 1
    for pid, df_p in df.groupby('RECORDING_SESSION_LABEL'):
        hm = participant_heatmap(df_p, sigma, X, Y)
        participant_maps.append(hm)
        pidnum+=1

        if pidnum % 10 == 0: # for every 10th participant:
            print(f"{pidnum} participants completed.")
    

    return np.mean(participant_maps, axis=0)



def participant_heatmap(df_participant, sigma, X, Y):

    '''creates heatmap (2D array) for a single participant, by summing gaussian blobs for all fixations.'''
    
    heatmap = np.zeros(X.shape)

    for _, row in df_participant.iterrows():
        g = fixation_gaussian(
            row['x_canonical'],
            row['y_canonical'],
            row['CURRENT_FIX_DURATION'],
            sigma,
            X,
            Y
        )
        heatmap += g


    return heatmap


import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors

def plot_heatmap(heatmap, aois, extent,condition_name,s):
    """
    Plots a heatmap over AOIs with:
    - AOI bounding boxes
    - Heatmap (white -> green -> yellow -> red)
    - Colorbar scaled to the vertical extent of AOIs
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # --- 1. Draw AOI bounding boxes ---
    for (x, y, w, h) in aois:
        rect = patches.Rectangle(
            (x, y),
            w, h,
            linewidth=1,
            edgecolor='grey',
            facecolor='none'
        )
        ax.add_patch(rect)

    # --- 2. Heatmap colormap ---
    colors = [(1,1,1), (0,1,0), (1,1,0), (1,0,0)]  # white -> green -> yellow -> red
    cmap = mcolors.LinearSegmentedColormap.from_list('white_green_yellow_red', colors, N=256)

    # --- 3. Draw heatmap ---
    im = ax.imshow(
        heatmap,
        cmap=cmap,
        alpha=0.75,
        origin='upper',
        extent=extent
    )

    # --- 4. Compute IA vertical bounds for colorbar ---
    y_coords = [y for _, y, _, _ in aois] + [y + h for _, y, _, h in aois]
    y_min, y_max = min(y_coords), max(y_coords)

    margin = 0.1 * (y_max - y_min)
    y_min_plot = y_min - margin
    y_max_plot = y_max + margin


    ax_pos = ax.get_position()
    y0 = (y_min_plot - extent[3]) / (extent[2] - extent[3]) * (ax_pos.y1 - ax_pos.y0) + ax_pos.y0
    y1 = (y_max_plot - extent[3]) / (extent[2] - extent[3]) * (ax_pos.y1 - ax_pos.y0) + ax_pos.y0

    # --- 5. Add colorbar next to heatmap, aligned to IAs ---
    cbar_width = 0.02  # fraction of figure width
    cax = fig.add_axes([ax_pos.x1 + 0.01, y0, cbar_width, y1 - y0])
    cbar = plt.colorbar(im, cax=cax)
    cbar.set_label('Relative gaze duration')

    # --- 6. Final touches ---
    ax.axis('off')
    os.makedirs(f"heatmaps/vis", exist_ok=True)
    os.makedirs(f"heatmaps/vis/{s}", exist_ok=True)
    plt.savefig(f"heatmaps/vis/{s}/{condition_name}.png", dpi=500, bbox_inches='tight')
