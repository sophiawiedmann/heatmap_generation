This repository contains code to generate an average heatmap per condition (sci_real, sci_pseudo, everyday_real, everyday_pseudo)
The workflow below shows how to run this code yourself.
The results are already generated and included in this repository (if you run the workflow from the beginning, the  output files will overwrite)



**WORKFLOW:**

Important Assumptions! (current data follows these)
-- There is one word per IA and one IA per word.
-- IAs are continuous vertically and horizontally (i.e. right-x-coordinate of an IA == left x-coordinate of the following IA of the same line. Similarily, there are no vertical gaps btw lines).
-- the critical/target word and the associatedword appears only once in the text!
-- we generate 4 average heatmaps, 1 per condition: the conditions end in _filler, _real, or _pseudo


----------  (1) Extract/Organize Data --------- 
(This step is already completed for the current experiment)
1a. generate the fixation reports and IA reports .txt files for participants (existing files in `/data`)
	1a.1 FR necessary columns for heatmap creation: CURRENT_FIX_X, CURRENT_FIX_Y, CURRENT_FIX_DURATION, RECORDING_SESSION_LABEL, TRIAL_INDEX, condition 
	1b.2 IA necessary columns for heatmap creation: IA_TOP, IA_BOTTOM, IA_LEFT, IA_RIGHT, TRIAL_INDEX, targetword, IA_LABEL, associatedword, condition
1b. create the canonical item .csv (existing file:`data/canonical_item_file.csv`)
	1b.1 this is just a subset of an existing IA report for one trial of one participant.
1c. update the `config.yaml` as needed (specifies input/output files/dirs)


--------- (2) Map the unmapped fixation coordinates to the canonical space --------- 
Run `main.py`: **see the file docstring on how to run this in the command line with proper arguments.**

main.py executes the following per participant:
-- extracts the canonical item space information (canonical item coordinates/line information). file: `extract_canonical_mapping.py`
-- maps all trials of one participant to the canonical space to the canonical space & saves .csvs per participant with the new mapped fixation coordinates to dir `out`. file: `maptrial.py`
-- generates visualizations of the participant's mapped-to-canonical fixations overlaid on the canonical template. the visualisation .png will be saved to `vis/mapped_vis`. file: `draw_mapped_fixations.py`

approx. run time for all 93 participants: 15 min
(generating the visualizations takes the bulk of the time)

 --------- (3) Generate the average heatmaps per condition --------- 
3a. **in `generate_heatmaps.py`, update the scalars list as desired:**
	3a.1. each s value in the scalar list is a parameter which determines the 'blurriness' or spread of each fixation heat point.
	3a.2. i.e. if you want to generate a set of heatmaps for just one value of s, update the list to contain only 1 value.
	3a.3. the default setting is one scalar value of s=0.1

3b. Run `generate_heatmaps.py`

`generate_heatmaps.py` executes the following:
-- splits the generated canonical mappings csvs from (2) into 4 condition groups. file:`heatmap_funcs.py`
-- generates the average heatmap per condition and saves the raw heatmap data into dir `heatmaps/saved_heatmap_data`
^ this is the bottleneck and takes quite some time. bc for each fixation, a single 2D Gaussian is computed and evaluated at every pixel in the heatmap. most of these pixels have values near zero, so a faster approach would be to compute the Gaussian only in a local patch around each fixation coordinate.
-- plots the average heatmap per condition and saves the vis .png into dir `heatmaps/vis`

approx. run times:
- 1 participant: 13s
- 3 participants: 42s
- 10 participants: 129s
- all 93 participants: 20min 

**Notes on heatmap generation algorithm**
The heatmaps are generated based on fixation duration, following how Dataviewer implements it.
 
This is how it was implemented:
1. Model each fixation as a Gaussian.
each fixation point at coordinates (x,y) is modeled as a 2D gaussian:
	a. peak at (x,y) -- the 'hottest' point of the fixation
	b. standard deviation scaled by parameter 's' -- controls the spatial spread of the Gaussian. larger s --> broader spread/the 'heat spot' is more blurred.
	c. gaussian values scaled by the fixation duration -- longer fixations have higher peak values/are 'hotter'.

2. Summing fixations per item
For each stimulus/item, all fixations are combined by summing their Gaussians.
Overlapping Gaussians sum, so regions with multiple or longer fixations appear hotter.
 
3. Averaging & normalization (0 to 1) across participants per condition