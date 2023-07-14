# Post acquisition super resoution Python implementation
# If useful in your work, please cite the following:
#
# Burton-Smith, R. N. & Murata, K. (2023) "Post acquisition super resolution for cryo-electron microscopy." bioRxiv. doi: https://doi.org/10.1101/2023.06.09.544325
#
# If it doesn't work, make sure 2023 imagecodecs are installed (anaconda has an ancient version by default, hence the pip install)
#
# Recommended install:
# conda create env --name pasr python=3.11
# conda activate pasr
# pip install termcolor mrcfile tifffile imagecodecs pillow
# python3 pasr_v2b.py -h
#
# Version 1 Python implementation
# - specify favoured output format
# - scaling from 2- to 5-fold (more than 3 is excessive)
#
#
#
#!/usr/bin/env python3

import mrcfile
import numpy as np
import argparse
import os
from tifffile import imread, imwrite

def scale_image(image, scale):
    return np.repeat(np.repeat(image, scale, axis=1), scale, axis=0)

def process_stack(input_file, output_file, scale):
    if input_file.endswith('.mrc') or input_file.endswith('.mrcs'):
        # Open the MRC stack file
        with mrcfile.open(input_file) as mrc:
            original_data = mrc.data
    elif input_file.endswith('.tif') or input_file.endswith('.tiff'):
        # Read the TIFF stack file
        original_data = imread(input_file)
    else:
        raise ValueError('Unsupported file format')

    # PASR pre-process each frame
    processed_data = np.empty((original_data.shape[0], original_data.shape[1]*scale, original_data.shape[2]*scale), dtype=original_data.dtype)

    for i in range(original_data.shape[0]):
        processed_data[i] = scale_image(original_data[i], scale)

    # Write the data to a new file
    if output_file.endswith('.mrc') or output_file.endswith('.mrcs'):
        # Write the MRC stack file
        with mrcfile.new(output_file, overwrite=True) as mrc:
            mrc.set_data(processed_data)
    elif output_file.endswith('.tif') or output_file.endswith('.tiff'):
        # Write the TIFF stack file
        imwrite(output_file, processed_data, compression='lzw')
    else:
        raise ValueError('Unsupported file format')

    print('PASR pre-processed data written to', output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PASR Pre-process MRC and TIFF frame stacks")
    parser.add_argument("input", type=str, help="Input MRC, MRCS, TIF, or TIFF file")
    parser.add_argument("-s", "--scale", type=int, choices=range(2, 5), default=2, help="Scaling factor (number of times to duplicate each pixel)")
    parser.add_argument("-o", "--output", type=str, help="Output MRC or TIFF file")
    parser.add_argument("--force_tif", action="store_true", help="Force the output file extension to be .tif. This is useful because .tif output uses LZW compression.")
    parser.add_argument("--force_mrc", action="store_true", help="Force the output file extension to be .mrc. This exists just for completion.")


    args = parser.parse_args()

    # If output file is not given, create one with the same name as the input file, but ending in _PASR before the file extension
    if args.output is None:
        base_name, ext = os.path.splitext(args.input)
        args.output = f"{base_name}_PASR_{args.scale}x{ext}"
    if args.force_tif:
        base_name, ext = os.path.splitext(args.output)
        args.output = f"{base_name}.tif"
    if args.force_mrc:
        base_name, ext = os.path.splitext(args.output)
        args.output = f"{base_name}.mrc"
	
    process_stack(args.input, args.output, args.scale)
