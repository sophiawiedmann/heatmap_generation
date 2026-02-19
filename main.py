import pandas as pd
import yaml
from extract_canonical_mapping import extract
from draw_mapped_fixations import draw
from maptrial import map_trial
import os
import argparse
import traceback
from pathlib import Path
import time


'''
This file:
1. extracts the canonical item space information, e.g. canonical item coordinates/line information
2. maps all trials of one participant to the canonical space to the canonical space
3. generates visualizations of the particpant's mapped-to-canonical fixations. a dir named 'vis' will be created where the output vis per participant will be saved.

example bash to run over 1 participant:
python3 main.py --pid P1LA1GPS

example bash to run this script over ALL particpants:
    participant_ids=(P10LC2GPS P11LC3GPS P12LC4GPS P13LD1GPS P14LD2GPS P15LD3GPS P16LD4GPS P17LE1GPS P18LE2GPS P19LE3GPS P1LA1GPS P20LE4GPS P21LF1GPS P22LF2GPS P23LF3GPS P24LF4GPS P25LG1GPS P27LG2GPS P28LG3GPS P29LG4GPS P2LA2GPS P30LH1GPS P31LH2GPS P32LH3GPS P33LH4GPS P35LI1GPS P36LI2GPS P37LI3GPS P38LI4GPS P39LJ1GPS P3LA3GPS P41LJ2GPS P42LJ3GPS P43LJ4GPS P44LK1GPS P45LK2GPS P46LK3GPS P47LK4GPS P48LL1GPS P49LL2GPS P4LA4GPS P50LL3GPS P51LL4GPS P53LA1GPS P54LA2GPS P56LA3GPS P57LA4GPS P58LB1GPS P59LB2GPS P5LB1GPS P60LB3GPS P61LB4GPS P62LC1GPS P63LC2GPS P64LC3GPS P65LC4GPS P66LD1GPS P67LD2GPS P68LD3GPS P69LD4GPS P6LB2GPS P70LE1GPS P71LE2GPS P72LE3GPS P73LE4GPS P74LF1GPS P75LF2GPS P76LF3GPS P77LF4GPS P78LG1GPS P79LG2GPS P7LB3GPS P80LG3GPS P81LG4GPS P82LH1GPS P83LH2GPS P84LH3GPS P85LH4GPS P86LI1GPS P87LI2GPS P88LI3GPS P89LI4GPS P8LB4GPS P90LJ1GPS P91LJ2GPS P92LJ3GPS P93LJ4GPS P94LK1GPS P95LK2GPS P96LK3GPS P97LK4GPS P98LL1GPS P9LC1GPS)

    for pid in "${participant_ids[@]}"
    do
        python3 main.py --pid "$pid"
    done

the pid is used in the config.yaml to extract the appopriate fr and ia files: with the current file naming convention, this should work without altering!
you need to update the load_config() function and the config accordingly if the names of the files change!

'''
def load_config(pid):
    # load config of the specified pid

    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    # Replace {pid} in all input_files
    for key, path in config["input_files"].items():
        config["input_files"][key] = path.format(pid=pid)

    return config


def main(pid):
    # Load Config info
    config = load_config(pid)

    errorfile = Path(config["output"]["error_file"])
    errorfile.touch(exist_ok=True)

    outputfile = Path(config["output"]["output_file"])
    outputfile.touch(exist_ok=True)

    canonical_item_file = config["canonical_info"]["canonical_item_file"]

    fr_file = config['input_files']['fr_file']
    ia_file = config['input_files']['ia_file']

    mapped_fr_outdir = config['output']['mapped_fr_outdir']
    Path(mapped_fr_outdir).mkdir(parents=True, exist_ok=True)

    print("------------------------------")
    print(f"PID: {pid}")
    print("------------------------------")

    out_file = os.path.join(mapped_fr_outdir, f"{pid}.csv")

    # Load canonical mapping template
    canonical_critical_word_coords, canonical_next_word_coords, canonical_last_word_coords, canonical_associate_word_coords, canonical_line_tops, canonical_line_bottoms, canonical_line_widths, canonical_line_lefts, canonical_line_rights = extract(canonical_item_file)
    #print(canonical_critical_word_coords, canonical_next_word_coords, canonical_last_word_coords, canonical_associate_word_coords, canonical_line_tops, canonical_line_bottoms, canonical_line_widths, canonical_line_lefts, canonical_line_rights)


    # Map each trial to the canonical space; save all trials for the participant in one .csv
    # New canonical x,y coordinates will be stored in cols 'x_canonical' and 'y_canonical'
    try:
        mapped_trials_df, fix_out_of_IA_bounds, formatcount = map_trial(fr_file, ia_file, canonical_critical_word_coords, canonical_next_word_coords, canonical_last_word_coords, canonical_associate_word_coords, canonical_line_tops, canonical_line_bottoms, canonical_line_widths, canonical_line_lefts, canonical_line_rights)
        mapped_trials_df.to_csv(out_file)
        print(f"Mapped PID {pid} saved to '{out_file}' ")

        with open(outputfile, "a") as file:
            file.write(f"--------{pid}--------:\n")
            file.write(f"# of fixations deleted (out of IA bounds): {fix_out_of_IA_bounds}\n")
            file.write(f"format count: {formatcount}\n")
            file.write("\n")

        # Generate visualization per trial of the mapped fixations in the canonical space
        if 'mapped_trials_df' in locals() and not mapped_trials_df.empty:
            print("Generating visualizations...")
            for trialnum in mapped_trials_df['TRIAL_INDEX'].unique():
                draw(pid, trialnum, canonical_item_file)
            print(f"Done generation visualizations for {pid}\n\n")

    except AssertionError as e:
        print(f"Mapping error of PID {pid}: {e}")
        with open(errorfile, "a") as file:
            file.write(f"{pid}: {e}")
            file.write("\n\n")

    except Exception as e:
        print(f"Mapping error of PID {pid}: {e}")
        with open(errorfile, "a") as file:
            # Write PID, exception type, message, and full traceback
            file.write(f"{pid}: {type(e).__name__} - {e}\n")
            file.write(traceback.format_exc())
            file.write("\n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", required=True)
    args = parser.parse_args()

    main(args.pid)

