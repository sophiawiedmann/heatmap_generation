import pandas as pd
import yaml
import numpy as np
import numbers


def map_trial(fr_file, ia_file, canonical_critical_word_coords, canonical_next_word_coords, canonical_last_word_coords, canonical_associate_word_coords, canonical_line_tops, canonical_line_bottoms, canonical_line_widths, canonical_line_lefts, canonical_line_rights):
    ''' maps all trials of 1 participant '''

    # ------------------------
    # STEP 0: Load + Extract information per non-filler trial:
    # ------------------------

    # Load IA report and FR files for this participant
    IA_df = pd.read_csv(ia_file, sep="\t") # reads a .txt file with tab separation: if you have data stored in .csv, you may have to change these two lines
    FR_df = pd.read_csv(fr_file, sep="\t")


    # Convert x-coordinate to int. Some files have them as strings, others as floats.
    if FR_df['CURRENT_FIX_X'].dtype == object or isinstance(FR_df['CURRENT_FIX_X'].iloc[0], str):
        FR_df['CURRENT_FIX_X'] = FR_df['CURRENT_FIX_X'].str.replace(',', '.').astype(float)
    
    FR_df['CURRENT_FIX_X'] = FR_df['CURRENT_FIX_X'].astype(int)

    # Convert y-coordinate to int. Some files have them as strings, others as floats.
    if FR_df['CURRENT_FIX_Y'].dtype == object or isinstance(FR_df['CURRENT_FIX_Y'].iloc[0], str):
        FR_df['CURRENT_FIX_Y'] = FR_df['CURRENT_FIX_Y'].str.replace(',', '.').astype(float)

    FR_df['CURRENT_FIX_Y'] = FR_df['CURRENT_FIX_Y'].astype(int)

    assert pd.api.types.is_integer_dtype(FR_df['CURRENT_FIX_X'].iloc[0]), f"CURRENT_FIX_X is not int! type: {type(FR_df['CURRENT_FIX_X'].iloc[0])}"
    assert pd.api.types.is_integer_dtype(FR_df['CURRENT_FIX_Y'].iloc[0]), "CURRENT_FIX_Y is not int!"

    # Keep only non-filler trials (condition does NOT end with '_filler')
    IA_df = IA_df[~IA_df["condition"].str.endswith("_filler", na=False)]
    FR_df = FR_df[~FR_df["condition"].str.endswith("_filler", na=False)]

    # Sanity check: exactly 8 trials per participant remain
    assert IA_df["TRIAL_INDEX"].nunique() == 8, f"IA_df has {IA_df['TRIAL_INDEX'].nunique()} trials instead of 8"
    assert FR_df["TRIAL_INDEX"].nunique() == 8, f"FR_df has {FR_df['TRIAL_INDEX'].nunique()} trials instead of 8"

    all_trials = []
    formatcount = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "canon": 0} 

    for trial_id in FR_df["TRIAL_INDEX"].unique():
        # Load the respective IA and FR subsets for this trial.
        print(f"---------- trial num: {trial_id} ----------")
        
        trial_fix_df = FR_df[FR_df['TRIAL_INDEX'] == trial_id].copy()
        trial_IA_df = IA_df[IA_df['TRIAL_INDEX'] == trial_id].copy()

        # Group lines by IA bounding box coordinates
        line_groups = trial_IA_df.groupby(['IA_TOP', 'IA_BOTTOM']) # assumes each region belonging to the same line has the same top and bottom y coordinates
        lines_info = []

        for (top, bottom), group in line_groups: # For each line
            group_sorted = group.sort_values('IA_LEFT') # Sort words in the line by IA_LEFT 
            line_width = group_sorted['IA_RIGHT'].max() - group_sorted['IA_LEFT'].min() # = max right - min left
            line_height = bottom - top

            lines_info.append({
                'top': top, 
                'bottom': bottom, 
                'line_height': line_height,
                'line_width': line_width,
                'IA_indices': group_sorted.index.tolist() # original indices of the rows (IAs) which belong to this line
            })

        lines_info = sorted(lines_info, key=lambda x: x['top']) # sort lines info top-to-bottom
        for i, line in enumerate(lines_info, start=1): # assign each group a line number 
            line['line_number'] = i


        # Sort words/IAs per line
        trial_IA_df['word_index_in_line'] = None
        for line in lines_info:
            for idx in line['IA_indices']:
                trial_IA_df.at[idx, 'line_number'] = line['line_number'] # Assign line numbers to each IA

            # Sort words in this line left-to-right
            line_words = (
                trial_IA_df.loc[line['IA_indices']] # Select all IA rows belonging to this line
                .sort_values('IA_LEFT') # Sort them left-to-right by left boundary
            )

            # Store order of words in the line in 'word_index_in_line' (starting at 1)
            for i, (row_idx, _) in enumerate(line_words.iterrows(), start=1):
                trial_IA_df.at[row_idx, 'word_index_in_line'] = i

        # ------------------------
        # STEP 1: Assign each fixation to its respective word
        # and then assign its IA_ROLE: whether it belongs to an anchor region (if so, which) or not
        # -----------------------

        # Extract for this trial:
            # the corresponding anchor region labels (the actual words)
            # indices in the df, 
            # and bounding-box coordinates
        trial_critical_word_label = trial_IA_df['targetword'].iloc[0] 
        assert type(trial_critical_word_label) == str

        trial_critical_row = trial_IA_df[trial_IA_df['IA_LABEL'] == trial_critical_word_label].iloc[0]

        trial_critical_word_index = trial_critical_row['word_index_in_line']
        item_critical_word_coords = (
            (trial_critical_row['IA_LEFT'],  trial_critical_row['IA_TOP']),
            (trial_critical_row['IA_RIGHT'], trial_critical_row['IA_TOP']),
            (trial_critical_row['IA_RIGHT'], trial_critical_row['IA_BOTTOM']),
            (trial_critical_row['IA_LEFT'],  trial_critical_row['IA_BOTTOM']),
        )

        #print(item_critical_word_coords)

        trial_critical_line = trial_critical_row['line_number']
        #print(trial_critical_line)
        assert isinstance(trial_critical_line, numbers.Number), f"type of trial_critical_line ({type(trial_critical_line)}) is not numerical"
        trial_critical_line = int(trial_critical_line)
        assert isinstance(trial_critical_line, int), "type of trial_critical_line != int"

        trial_critical_line_subset = trial_IA_df[trial_IA_df['line_number'] == trial_critical_line]
        trial_next_word_row = trial_critical_line_subset[trial_critical_line_subset['word_index_in_line'] == trial_critical_row['word_index_in_line'] + 1]
        trial_next_word_label = trial_next_word_row['IA_LABEL'].iloc[0] if not trial_next_word_row.empty else None
        assert isinstance(trial_next_word_label, str), "type of trial_next_word_label != str "

        next_row = trial_next_word_row.iloc[0]
        item_next_word_coords = (
            (next_row['IA_LEFT'],  next_row['IA_TOP']),
            (next_row['IA_RIGHT'], next_row['IA_TOP']),
            (next_row['IA_RIGHT'], next_row['IA_BOTTOM']),
            (next_row['IA_LEFT'],  next_row['IA_BOTTOM']),
        )

        #print(item_next_word_coords)

        trial_next_word_index = trial_next_word_row['word_index_in_line'].iloc[0]

        trial_last_word_row = trial_critical_line_subset.iloc[-1]
        trial_last_word_label = trial_last_word_row['IA_LABEL']
        assert isinstance(trial_last_word_label, str), "type of trial_last_word_label != str "
        trial_last_word_index = trial_last_word_row['word_index_in_line']

        item_last_word_coords = (
            (trial_last_word_row ['IA_LEFT'],  trial_last_word_row ['IA_TOP']),
            (trial_last_word_row ['IA_RIGHT'], trial_last_word_row ['IA_TOP']),
            (trial_last_word_row ['IA_RIGHT'], trial_last_word_row ['IA_BOTTOM']),
            (trial_last_word_row ['IA_LEFT'],  trial_last_word_row ['IA_BOTTOM']),
        )
        #print(item_last_word_coords)

        trial_associate_word_label = trial_IA_df['associatedword'].iloc[0]
        assert isinstance(trial_associate_word_label, str), "type of trial_associate_word_label != str "
        trial_associate_word_index = trial_IA_df[trial_IA_df['IA_LABEL'] == trial_associate_word_label].iloc[0]['word_index_in_line']

        assoc_row = trial_IA_df[trial_IA_df['IA_LABEL'] == trial_associate_word_label].iloc[0]
        item_associate_word_coords = (
            (assoc_row['IA_LEFT'],  assoc_row['IA_TOP']),
            (assoc_row['IA_RIGHT'], assoc_row['IA_TOP']),
            (assoc_row['IA_RIGHT'], assoc_row['IA_BOTTOM']),
            (assoc_row['IA_LEFT'],  assoc_row['IA_BOTTOM']),
        )

        #print(item_associate_word_coords)

        assert item_critical_word_coords is not None
        assert item_last_word_coords is not None
        assert item_associate_word_coords is not None

        # Initialize new columns in the fixation dataframe (per-fixation information)
        trial_fix_df['IA_LABEL'] = None # the word it belongs to
        trial_fix_df['IA_ID'] = None # the ID of the IA it belongs to
        trial_fix_df['IA_ROLE'] = None # the role of the IA it belongs to: 'critical', 'next', 'last', 'associate', or None
        trial_fix_df['x_offset'] = None  # relative horizontal landing (0 = left edge, 1 = right edge)
        trial_fix_df['y_offset'] = None  # relative vertical landing (0 = top, 1 = bottom)
        trial_fix_df['line_number'] = None # the line it belongs to (0 indexing)
        trial_fix_df['word_index_in_line'] = None 

        # Loop over each fixation
        fix_out_of_IA_bounds = 0
        drop_OOB_rows = []

        for i in trial_fix_df.index:
            x_fix = trial_fix_df.at[i, 'CURRENT_FIX_X']
            assert isinstance(x_fix, numbers.Number), f"x_fix is of type {type(x_fix)}, not numeric)"

            y_fix = trial_fix_df.at[i, 'CURRENT_FIX_Y']
            assert isinstance(y_fix, numbers.Number), f"x_fix is of type {type(y_fix)}, not numeric)"

            assigned = False
            role = None

            # 01. Map each fixation to its respective IA
            for _, IA in trial_IA_df.iterrows():
                
                if IA['IA_LEFT'] <= x_fix <= IA['IA_RIGHT'] and IA['IA_TOP'] <= y_fix <= IA['IA_BOTTOM']:

                    # Map fixation to this IA
                    trial_fix_df.at[i, 'IA_LABEL'] = IA['IA_LABEL']
                    trial_fix_df.at[i, 'IA_ID'] = IA['IA_ID']
                    trial_fix_df.at[i, 'line_number'] = IA['line_number']
                    trial_fix_df.at[i, 'word_index_in_line'] = IA['word_index_in_line']
                
                    # Compute relative offsets within the word from the left boundary of the IA
                    # i.e. if the fixation is in the middle of the IA, will have 'x_offset' of 0.5
                    width = IA['IA_RIGHT'] - IA['IA_LEFT']
                    height = IA['IA_BOTTOM'] - IA['IA_TOP']
                    trial_fix_df.at[i, 'x_offset'] = (x_fix - IA['IA_LEFT']) / width
                    trial_fix_df.at[i, 'y_offset'] = (y_fix - IA['IA_TOP']) / height

                    assigned = True

                    break  # Found the IA it belongs to, no need to check further
            

            if not assigned: # fix did not fall in any IA
                assigned = "OOB"
                # delete this fix from the df.
                fix_out_of_IA_bounds+=1
                drop_OOB_rows.append(i)

            assert assigned is True or assigned == "OOB", (
                f"Trial {trial_id}: fixation at ({x_fix}, {y_fix}) was neither assigned to an IA nor marked as out of IA bounds"
                )
            
            # 02. Map each fixation to its IA_ROLE, i.e. if it falls into a anchor-region and which one.
            fix_row = trial_fix_df.loc[i]
            line = fix_row['line_number']
            word_idx = fix_row['word_index_in_line']

            if line == trial_critical_line:
                if word_idx == trial_critical_word_index:
                    role = 'critical'
                
                elif trial_next_word_index is not None and word_idx == trial_next_word_index:
                    role = 'next'

                elif word_idx == trial_last_word_index:
                    role = 'last'

            elif fix_row['IA_LABEL'] == trial_associate_word_label:
                role = 'associate'

            trial_fix_df.at[i, 'IA_ROLE'] = role
        
        trial_fix_df = trial_fix_df.drop(drop_OOB_rows) 

        
        # ------------------------ #
        # STEP 2: handle items which do not have canonical format: 10 total lines --> 4 pre-critical lines, 4 post-associate
        
        # Possible other formats:
            # 11 liners:
                # A) 5 pre-critical, 4 post-associate --> delete 1 pre-critical line
                # B) 4 pre-critical, 5 post-associate --> delete 1 post-associate line

            # 9 liners:
                # C) 4 pre-critical, 3 post-associate --> duplicate one post-associate line
            
            # 10 liners:
                # CANONICAL: 4 pre-critical, 4 post-associate --> do nothing
                # D) 5 pre-critical, 3 post-associate -->  delete 1 pre-critical, duplicate 1 post-associate
            
            # 12 liners:
                # E) 4 pre-critical, 6 post-associate --> delete 2 post-associate

        # ------------------------ # 
        
        if len(lines_info) == 11: # if there are 11 total lines
    
            if trial_critical_line == 6: # FORMAT A: 5 pre-critical lines, 4 post-associate lines
                # delete any fixations from line 3
                formatcount["A"] +=1
                # this compresses 5 pre-critical lines to the canonical 4 pre-critical lines
                trial_fix_df = trial_fix_df[trial_fix_df['line_number'] != 3].copy()
                # then renumber lines
                # line numbers > 3 shift by -1
                # i.e. line 6, which is the critical line, will now map to line 5, which matches canonical
                trial_fix_df.loc[trial_fix_df['line_number'] > 3, 'line_number'] -= 1
    
                # rename trial critical line: it is now the same as the canonical critical line
                trial_critical_line = 5

                # also update line numbers in the line info list
                lines_info = [l for l in lines_info if l.get('line_number') != 3]
                for l in lines_info:
                    if l.get('line_number', 0) > 3:
                        l['line_number'] -= 1

            elif trial_critical_line == 5:       # FORMAT B: 4 pre-critical lines, 5 post-associate lines
                # delete one post associate line: last row 
                # (bc this line may be shorter than other items and have less fixations)
                # and this format is found only in very few items
                formatcount["B"] +=1
                trial_fix_df = trial_fix_df[trial_fix_df['line_number'] != 11].copy()
                lines_info = [l for l in lines_info if l.get('line_number') != 11]

        elif len(lines_info) == 9:     # FORMAT C: 4 pre-critical, 3 post-associate
            # duplicate one post-associate line (line 8)

            formatcount["C"] +=1
            trial_fix_df.loc[trial_fix_df['line_number'] == 9, 'line_number'] = 10 # shift original line 9 to line 10

            duplicate_line_fix = trial_fix_df[trial_fix_df['line_number'] == 8].copy() # make copy of subset of fix in line 8
            duplicate_line_fix['line_number'] = 9 # rename these fixations to line 9 
            trial_fix_df = pd.concat([trial_fix_df, duplicate_line_fix], ignore_index=True) # append new line 9, the duplicated fixations
            
            # update line numbers in the line info list
            for l in lines_info:
                if l.get('line_number') == 9: # line number 9 shifts to line 10
                    l['line_number'] = 10

            # duplicate line 8 info as new line 9
            line_8_info = next(l for l in lines_info if l.get('line_number') == 8)
            line_9_info = line_8_info.copy()
            line_9_info['line_number'] = 9
            lines_info.append(line_9_info)
        
        elif len(lines_info) == 10: 
            # do nothing if it's the canon pattern, i.e. 4 pre-critical, 4 post-associate
            if trial_critical_line == 5:
                formatcount["canon"] +=1

            if trial_critical_line == 6: # FORMAT D: 5 pre-critical, 3-post associate
                # remove line 3, duplicate line 8. so we end with 4 pre-crit, 4 post-associate.
                formatcount["D"] +=1
                # remove line 3
                trial_fix_df = trial_fix_df[trial_fix_df['line_number'] != 3].copy()
                # then renumber lines
                # line numbers > 3 shift by -1
                # i.e. line 6, which is the critical line, will now map to line 5, which matches canonical
                trial_fix_df.loc[trial_fix_df['line_number'] > 3, 'line_number'] -= 1
                # rename trial critical line: it is now the same as the canonical critical line
                trial_critical_line = 5
                # also update line numbers in the line info list
                lines_info = [l for l in lines_info if l.get('line_number') != 3]
                for l in lines_info:
                    if l.get('line_number', 0) > 3:
                        l['line_number'] -= 1

                # duplicate line 8 
                trial_fix_df.loc[trial_fix_df['line_number'] == 9, 'line_number'] = 10 # shift original line 9 to line 10

                duplicate_line_fix = trial_fix_df[trial_fix_df['line_number'] == 8].copy() # make copy of subset of fix in line 8
                duplicate_line_fix['line_number'] = 9 # rename these fixations to line 9 
                trial_fix_df = pd.concat([trial_fix_df, duplicate_line_fix], ignore_index=True) # append new line 9, the duplicated fixations
                
                # update line numbers in the line info list
                for l in lines_info:
                    if l.get('line_number') == 9: # line number 9 shifts to line 10
                        l['line_number'] = 10

                # duplicate line 8 info as new line 9
                line_8_info = next(l for l in lines_info if l.get('line_number') == 8)
                line_9_info = line_8_info.copy()
                line_9_info['line_number'] = 9
                lines_info.append(line_9_info)

        elif len(lines_info) == 12: # formatE: 4 pre-critical, 6 post-associate
            # delete last 2 lines. 
            formatcount["E"] +=1
           
            trial_fix_df = trial_fix_df[trial_fix_df['line_number'] != 12].copy()
            trial_fix_df = trial_fix_df[trial_fix_df['line_number'] != 11].copy()
            lines_info = [l for l in lines_info if l.get('line_number') != 12]
            lines_info = [l for l in lines_info if l.get('line_number') != 11]

            

        # ------------------------
        # STEP 2: Assign all fixations within anchor regions to their respective canonical anchor regions
        # ------------------------
        trial_fix_df['x_canonical'] = None
        trial_fix_df['y_canonical'] = None

        for i, fix_row in trial_fix_df.iterrows(): # for each fixation in the trial
            role = fix_row['IA_ROLE']
            x_fix = fix_row['CURRENT_FIX_X'] # x-coordinate before mapping
            y_fix = fix_row['CURRENT_FIX_Y'] # y-coordinate before mapping

            # Skip fixations that are not in anchor regions
            if role is None:
                continue

            # Choose the canonical anchor coordinates based on the role
            if role == 'critical':
                canon_coords = canonical_critical_word_coords
            elif role == 'next':
                canon_coords = canonical_next_word_coords
            elif role == 'last':
                canon_coords = canonical_last_word_coords
            elif role == 'associate':
                canon_coords = canonical_associate_word_coords
            else:
                continue  # should not happen

            (left, top), (right, _), (_, _), (_, bottom) = canon_coords 
            canon_width = right - left
            canon_height = bottom - top

            # Compute new fixation coordinates in the canonical anchor region space
            x_new = left + fix_row['x_offset'] * canon_width # takes into consideration the relative position in original word
            y_new = top + fix_row['y_offset'] * canon_height

            trial_fix_df.at[i, 'x_canonical'] = x_new
            trial_fix_df.at[i, 'y_canonical'] = y_new



        # ------------------------
        # STEP 3: Map all non-anchor fixations (IA_ROLE is None) to canonical lines
        # fixations in non-anchor segments are scaled accordingly to the non-anchor segment length/width
        # ------------------------

        for i, fix_row in trial_fix_df[trial_fix_df['IA_ROLE'].isna()].iterrows():
        
            item_line = fix_row['line_number']
            x_fix = fix_row['CURRENT_FIX_X']
            y_fix = fix_row['CURRENT_FIX_Y']

            # Determine which canonical line to map to
            if item_line < trial_critical_line:  # pre-critical lines
                canon_line = item_line 

            elif item_line == trial_critical_line:
                canon_line = trial_critical_line  # critical line
            elif item_line == trial_critical_line + 1:
                canon_line = trial_critical_line + 1  # associate line
            elif item_line > trial_critical_line + 1: # post-associate lines
                canon_line = item_line

            # Canonical line width and bounds
            canon_line_left = canonical_line_lefts[canon_line]
            canon_line_right = canonical_line_rights[canon_line]
            canon_line_width = canonical_line_widths[canon_line]
            canon_line_top = canonical_line_tops[canon_line]
            canon_line_bottom = canonical_line_bottoms[canon_line]
            canon_line_height = canon_line_bottom - canon_line_top

            # Original item line bounds
            item_line_info = next(line for line in lines_info if line['line_number'] == item_line)
            item_line_left = min(trial_IA_df.loc[item_line_info['IA_indices'], 'IA_LEFT'])
            item_line_right = max(trial_IA_df.loc[item_line_info['IA_indices'], 'IA_RIGHT'])
            
            item_line_width = item_line_right - item_line_left
            item_line_top = item_line_info['top']
            item_line_bottom = item_line_info['bottom']
            item_line_height = item_line_bottom - item_line_top

            # ------------------------
            # Y mapping -- global line center mapping 
            # ------------------------
            fix_x = fix_row['CURRENT_FIX_X']
            fix_y = fix_row['CURRENT_FIX_Y']

            item_center_y = item_line_top + item_line_height / 2
            canon_center_y = canon_line_top + canon_line_height / 2
            scale_y = canon_line_height / item_line_height
            y_new = canon_center_y + (fix_y - item_center_y) * scale_y

            # ------------------------
            # X mapping -- piecewise mapping on anchor region lines 
            # otherwise global center mapping for the whole line
            # ------------------------
    
    
            if item_line == trial_critical_line: # Only do piecewise mapping on lines that contain anchors

                # Collect anchor x-interval spans for anchor regions of this line
                item_anchor_spans = []
                canon_anchor_spans = []

                for role, item_coords, canon_coords in [
                    ('critical', item_critical_word_coords, canonical_critical_word_coords),
                    ('next', item_next_word_coords, canonical_next_word_coords),
                    ('last', item_last_word_coords, canonical_last_word_coords),
                ]:
                    if item_coords is None:
                        continue

                    (i_left, _), (i_right, _), _, _ = item_coords # extract x-spans of the item anchor region
                    (c_left, _), (c_right, _), _, _ = canon_coords 

                    item_anchor_spans.append((i_left, i_right))
                    canon_anchor_spans.append((c_left, c_right))
                

                # Sort anchor regions left to right
                paired = sorted(zip(item_anchor_spans, canon_anchor_spans), key=lambda x: x[0][0])
                item_anchor_spans, canon_anchor_spans = zip(*paired)

                #print("-----")
                #print(item_anchor_spans)
                #print(canon_anchor_spans)

                # Build non-anchor segments (i.e. x-interval spans which fall between/before/after anchor regions)
                item_segments = []
                canon_segments = []

                prev_i = item_line_left # start at the left edge of the line of the item (i.e. minimum x-coord of the line)
                prev_c = canon_line_left # start at the left edge of the line of the canonical item (i.e. minimum x-coord of the line)

                for (i_left, i_right), (c_left, c_right) in zip(item_anchor_spans, canon_anchor_spans): # for each anchor
                    if i_left > prev_i: # the anchor region is laying to the right of where we currently are, i.e. this is is a non-anchor region
                        item_segments.append((prev_i, i_left)) # append this non-anchor segment
                        canon_segments.append((prev_c, c_left)) # # append this non-anchor segment
                    prev_i = i_right # move to next non-anchor region: where the first anchor region ends (i_right)
                    prev_c = c_right

                if prev_i < item_line_right: # capture the right-most non-anchor region of the line
                    item_segments.append((prev_i, item_line_right))
                    canon_segments.append((prev_c, canon_line_right))

                # Find the segment the fixation belongs to
                x_new = None
                for (i_left, i_right), (c_left, c_right) in zip(item_segments, canon_segments):
                    if i_left <= fix_x <= i_right: 
                        if i_right > i_left:
                            x_norm = (fix_x - i_left) / (i_right - i_left) # relative position in the segment 0-1
                            assert x_norm 
                        else:
                            x_norm = 0.0
                        
                        x_new = c_left + x_norm * (c_right - c_left) # map to canonical space


                        break

            elif item_line == trial_critical_line + 1: # associated-word line
                # Collect anchor x-interval spans for anchor regions of this line
                item_anchor_spans = []
                canon_anchor_spans = []

                for role, item_coords, canon_coords in [
                    ('associate', item_associate_word_coords, canonical_associate_word_coords),
                ]:
                    if item_coords is None:
                        continue

                    (i_left, _), (i_right, _), _, _ = item_coords # extract x-spans
                    (c_left, _), (c_right, _), _, _ = canon_coords # extract x-spans

                    item_anchor_spans.append((i_left, i_right))
                    canon_anchor_spans.append((c_left, c_right))

                # Sort anchors left to right
                paired = sorted(zip(item_anchor_spans, canon_anchor_spans), key=lambda x: x[0][0])
                item_anchor_spans, canon_anchor_spans = zip(*paired)

                # Build non-anchor segments (i.e. x-interval spans which fall between/before/after anchor regions)
                item_segments = []
                canon_segments = []

                prev_i = item_line_left # start at the left edge of the line of the item (i.e. minimum x-coord of the line)
                prev_c = canon_line_left # start at the left edge of the line of the canonical item (i.e. minimum x-coord of the line)

                for (i_left, i_right), (c_left, c_right) in zip(item_anchor_spans, canon_anchor_spans): # for each anchor
                    if i_left > prev_i: # the anchor region is to the right of where we currently are, i.e. this is is a non-anchor region
                        item_segments.append((prev_i, i_left)) # append this non-anchor segment
                        canon_segments.append((prev_c, c_left)) # # append this non-anchor segment
                    prev_i = i_right # move to next non-anchor region: where the first anchor region ends (i_right)
                    prev_c = c_right

                if prev_i < item_line_right: # capture the right-most non-anchor region
                    item_segments.append((prev_i, item_line_right))
                    canon_segments.append((prev_c, canon_line_right))
                
                x_new = None

                for (i_left, i_right), (c_left, c_right) in zip(item_segments, canon_segments):

                    if i_left <= fix_x <= i_right: # find the segment the fixation belongs to
                        if i_right > i_left:
  
                            x_norm = (fix_x - i_left) / (i_right - i_left) # relative position in the segment 0-1

                        else:
        
                            x_norm = 0.0
                        x_new = c_left + x_norm * (c_right - c_left) # mapping to canonical space
          

                        break


            else:
                # ------------------------
                # for lines which do NOT have any anchor regions ('Non-anchor lines': use center-aligned mapping;
                # this scales fixations in these lines to the canonical line length
                # ------------------------
                item_line_width = item_line_right - item_line_left
                canon_line_width = canon_line_right - canon_line_left

                item_center_x = item_line_left + item_line_width / 2
                canon_center_x = canon_line_left + canon_line_width / 2
                scale_x = canon_line_width / item_line_width

                x_new = canon_center_x + (fix_x - item_center_x) * scale_x

            # Assign canonical coordinates
            trial_fix_df.at[i, 'x_canonical'] = x_new
            trial_fix_df.at[i, 'y_canonical'] = y_new

        # make sure all fixations got new coordinates in the canonical space
        # new coordinates saved in col 'x_canonical' and 'y_canonical'
        assert (
            trial_fix_df['x_canonical'].notna().all()
            and trial_fix_df['y_canonical'].notna().all()
        ), "NA values found in canonical fixation coordinates"

        all_trials.append(trial_fix_df)
        print("Mapped")

    final_df = pd.concat(all_trials, ignore_index=True) # save all trials in one df
    
    assert final_df['TRIAL_INDEX'].nunique() == 8


    return final_df, fix_out_of_IA_bounds, formatcount
