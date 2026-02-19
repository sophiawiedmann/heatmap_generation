import cv2
import numpy as np
import pandas as pd
import os

def draw_ia(ia):
    # read in IA file
    ia_df = pd.read_csv(ia)


    top =  ia_df['IA_TOP']
    bottom = ia_df['IA_BOTTOM']
    left =  ia_df['IA_LEFT']
    right =  ia_df['IA_RIGHT']

 
    # Create a blank image
    height = max(bottom) + min(top)
    width = max(right) + min(left)
    img = np.ones((height, width, 3), dtype=np.uint8) * 255  

    # draw boxes: (top, bottom, left, right)
    for t, b, l, r in zip(top, bottom, left, right):
        cv2.rectangle(img, (l, t), (r, b), (255, 200, 100), 2) 
    
    # fill in the box where the critical word is
    
    critical_words_coords = ((534, 390), (662, 390), (534, 454), (662, 454))
    a_word_coords = ((502, 454), (614, 454), (502, 518), (614, 518))

   
    
    crit_top_left = critical_words_coords[0]
    crit_bottom_right = critical_words_coords[3]

    cv2.rectangle(
        img,
        crit_top_left,
        crit_bottom_right,
        color=(255, 0, 0),  # Blue
        thickness=-1        # Fill the rectangle
    )

    a_top_left = a_word_coords[0]
    a_bottom_right = a_word_coords[3]

    cv2.rectangle(
        img,
        a_top_left,
        a_bottom_right,
        color=(100, 100, 0), # green
        thickness=-1
    )
    
    return img

def draw_fix(ia,fr, trialnum, pid):
    ia_boxes = draw_ia(ia)
    os.makedirs(f'vis/mapped_vis/{pid}', exist_ok=True)
    if fr.endswith(".txt"):
        fr_df = pd.read_csv(fr, sep="\t")
    elif fr.endswith(".csv"):
        fr_df = pd.read_csv(fr)
    
    fr_df = fr_df[fr_df['TRIAL_INDEX'] == trialnum]

    for x, y in zip(fr_df['x_canonical'],fr_df['y_canonical']):       
        cv2.circle(ia_boxes, (round(x), round(y)), radius=8, color=(0, 0, 255), thickness=2)
        filename = f'MappedFixations_{trialnum}.png'
        cv2.imwrite(f'vis/mapped_vis/{pid}/{filename}', ia_boxes)


def draw(pid, trialnum, ia_canonical):
    fr = f'out/{pid}.csv' # the mapped fr of the participant
    ia = ia_canonical

    return draw_fix(ia, fr, trialnum, pid)

