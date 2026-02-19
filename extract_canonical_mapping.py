def extract(canonical_item_file):
    import pandas as pd
    # ------------------------------------
    # Get canonical information of the example item.
    # ------------------------------------
    canonical_item_df = pd.read_csv(canonical_item_file)

    # Extract Per-Line Info: Width, Height, and words within that line.
    line_groups = canonical_item_df.groupby(['IA_TOP', 'IA_BOTTOM']) # assumes each region belong to the same line has the same top and bottom y coordinates
    lines_info = []
    for (top, bottom), group in line_groups:
        group_sorted = group.sort_values('IA_LEFT') # Sort words in the line by IA_LEFT 
        line_left = group_sorted['IA_LEFT'].min()
        line_right = group_sorted['IA_RIGHT'].max()
        line_width = line_right - line_left
        line_height = bottom - top
        words_in_line = list(group_sorted['IA_LABEL'])

        lines_info.append({
            'top': top,
            'bottom': bottom,
            'left': line_left,
            'right': line_right,
            'line_height': line_height,
            'line_width': line_width,
            'words': words_in_line
        })

        lines_info = sorted(lines_info, key=lambda x: x['top']) # sort lines info top-to-bottom

    

    # Extract Anchor Regions Coordinates

    ## 1. Critical Word
    canon_word_str = canonical_item_df['targetword'].iloc[0] # get the crit. word from the df
    canon_word = canonical_item_df[canonical_item_df['IA_LABEL'] == canon_word_str] # extract the row of the df which contains the crit. word
    crit_index = canon_word.index # index of its row in the df.

    # get the line the canon word belongs to
    for i, line in enumerate(lines_info):
        if canon_word_str in line['words']:
            canonical_crit_word_line_number = i   # the actual line number - 1 (bc 0-based indexing)
            crit_line_info = line 
            break

    if not canon_word.empty:
        # Extract coordinates of the crit word
        left = canon_word['IA_LEFT'].values[0]
        top = canon_word['IA_TOP'].values[0]
        right = canon_word['IA_RIGHT'].values[0]
        bottom = canon_word['IA_BOTTOM'].values[0]

        crit_word_topleft = (left, top)
        crit_word_topright = (right, top)
        crit_word_bottomleft = (left, bottom)
        crit_word_bottomright = (right, bottom)

        canonical_critical_word_coords = (crit_word_topleft, crit_word_topright, crit_word_bottomleft, crit_word_bottomright)

    ## 2. Critical Word +1 (next word)
    next_word = canonical_item_df.loc[crit_index + 1]

    next_word_label = next_word['IA_LABEL'].iloc[0]
    assert type(next_word_label) == str 

    if not canon_word.empty:
        next_word_topleft = (next_word['IA_LEFT'].values[0], next_word['IA_TOP'].values[0])
        next_word_topright = (next_word['IA_RIGHT'].values[0], next_word['IA_TOP'].values[0])
        next_word_bottomleft = (next_word['IA_LEFT'].values[0], next_word['IA_BOTTOM'].values[0])
        next_word_bottomright = (next_word['IA_RIGHT'].values[0], next_word['IA_BOTTOM'].values[0])

        canonical_next_word_coords = (next_word_topleft, next_word_topright, next_word_bottomleft, next_word_bottomright)
        
    ## 3. Last Word of Critical Line

    # Find the last word in the critical line (the word which has max-x coordinate)

    last_word_label = max(
        crit_line_info['words'], 
        key=lambda w: canonical_item_df[canonical_item_df['IA_LABEL'] == w]['IA_RIGHT'].values[0]
    )
    assert type(last_word_label) == str 

    last_word = canonical_item_df[canonical_item_df['IA_LABEL'] == last_word_label]
    if not last_word.empty:
        last_word_topleft = (last_word['IA_LEFT'].values[0], last_word['IA_TOP'].values[0])
        last_word_topright = (last_word['IA_RIGHT'].values[0], last_word['IA_TOP'].values[0])
        last_word_bottomleft = (last_word['IA_LEFT'].values[0], last_word['IA_BOTTOM'].values[0])
        last_word_bottomright = (last_word['IA_RIGHT'].values[0], last_word['IA_BOTTOM'].values[0])

        canonical_last_word_coords = (last_word_topleft, last_word_topright, last_word_bottomleft, last_word_bottomright)

    ## 4. Associated Word
    assoc_word_str = canonical_item_df['associatedword'].iloc[0]
    assoc_word = canonical_item_df[canonical_item_df['IA_LABEL'] == assoc_word_str]

    if not assoc_word.empty:
        assoc_word_topleft = (assoc_word['IA_LEFT'].values[0], assoc_word['IA_TOP'].values[0])
        assoc_word_topright = (assoc_word['IA_RIGHT'].values[0], assoc_word['IA_TOP'].values[0])
        assoc_word_bottomleft = (assoc_word['IA_LEFT'].values[0], assoc_word['IA_BOTTOM'].values[0])
        assoc_word_bottomright = (assoc_word['IA_RIGHT'].values[0], assoc_word['IA_BOTTOM'].values[0])

        canonical_associate_word_coords = (assoc_word_topleft, assoc_word_topright, assoc_word_bottomleft, assoc_word_bottomright)
    else:
        AssertionError

    # sanity check: crit word, crit word +1, last word are all in same line and are 1 line before the associate word.
    crit_line_idx = canonical_crit_word_line_number 
    next_line_idx = crit_line_idx + 1
    crit_words = set(lines_info[crit_line_idx]['words']) 

    assoc_words = set(lines_info[next_line_idx]['words'])


    sanity_ok = (
        canon_word_str in crit_words and
        next_word_label in crit_words and
        last_word_label in crit_words and
        assoc_word_str in assoc_words
    )

    if sanity_ok:
        print("canonical mapping extraction: sanity check passed")
    else:
        print("canonical mapping extraction: sanity check DID NOT PASS")

    # ------------------------
    # Add canonical line tops and bottoms (for scaling other non-anchor regions later)
    # ------------------------

    canonical_line_tops = {}
    canonical_line_bottoms = {}

    canonical_line_lefts = {}
    canonical_line_rights = {}

    for idx, line in enumerate(lines_info, start=1):
        canonical_line_tops[idx] = line['top']
        canonical_line_bottoms[idx] = line['bottom']
        canonical_line_lefts[idx] = line['left']
        canonical_line_rights[idx] = line['right']

    canonical_line_widths = {
        idx: line['line_width']
        for idx, line in enumerate(lines_info, start=1)
    
    }

    return canonical_critical_word_coords, canonical_next_word_coords, canonical_last_word_coords, canonical_associate_word_coords, canonical_line_tops, canonical_line_bottoms, canonical_line_widths, canonical_line_lefts, canonical_line_rights
