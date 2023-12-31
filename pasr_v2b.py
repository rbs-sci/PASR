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
# Version history:
# Version 2 Python implementation
# - fix single frame processing crash
# - remove 5x upscaling option (overkill)
# - add JPG output
# - add TIFF flip output
#
# Version 1 Python implementation
# - specify favoured output format
# - scaling from 2- to 5-fold (more than 3 is excessive)
#
#
#
#!/usr/bin/env python3

import os
import glob
import mrcfile
import argparse
import numpy as np
from PIL import Image
from termcolor import colored
from tifffile import imread, imwrite
from multiprocessing import Pool

# Function to scale image
def scale_image(image, scale):
    """Scales an image by duplicating each pixel.

    Args:
    image : numpy array representing the image
    scale : int, scale factor

    Returns:
    numpy array, the scaled image
    """
    return np.repeat(np.repeat(image, scale, axis=1), scale, axis=0)

# Function to process each file
def process_file(input_file, output_file, scale, compression, flip_tif):
    """Processes a file: reads, scales and writes it.

    Args:
    input_file : str, path to the input file
    output_file : str, path to the output file
    scale : int, scale factor
    compression : str, compression method
    flip_tif : bool, whether to flip the image

    Returns:
    None
    """
    # Reading the file
    if input_file.endswith('.mrc') or input_file.endswith('.mrcs'):
        with mrcfile.open(input_file) as mrc:
            original_data = mrc.data
    elif input_file.endswith('.tif') or input_file.endswith('.tiff') or input_file.endswith('.jpg'):
        original_data = imread(input_file)
    else:
        raise ValueError(colored('Unsupported input file format. Only MRC, TIF and JPG files are supported.', 'red'))

    # Scaling the image
    if original_data.ndim == 3:
        processed_data = np.empty((original_data.shape[0], original_data.shape[1]*scale, original_data.shape[2]*scale), dtype=original_data.dtype)
        for i in range(original_data.shape[0]):
            processed_data[i] = scale_image(original_data[i], scale)
    elif original_data.ndim == 2:
        processed_data = scale_image(original_data, scale)
    else:
        raise ValueError(colored('Unsupported data dimensions. Only 2D images and 2D frame stacks are supported.', 'red'))

    # Writing the output
    if output_file.endswith('.mrc') or output_file.endswith('.mrcs'):
        with mrcfile.new(output_file, overwrite=True) as mrc:
            mrc.set_data(processed_data)
        print(colored(f'PASR pre-processed data written to {output_file}. No compression applied for MRC format (use TIF for compression).\n', 'green'))
    elif output_file.endswith('.tif') or output_file.endswith('.tiff'):
        if flip_tif:
            processed_data = np.flip(processed_data, axis=0)
            flip_status = "Flipping applied."
        else:
            flip_status = "No flipping applied."
        imwrite(output_file, processed_data, compression=compression)
        print(colored(f'PASR pre-processed data written to {output_file} with {compression} compression. {flip_status}\n', 'green'))
    elif output_file.endswith('.jpg'):
        if original_data.ndim == 3:
            print(colored('Error: Cannot save 2D frame stack as JPG.', 'red'))
            return
        processed_data = processed_data.astype(np.uint8)
        im = Image.fromarray(processed_data)
        im.save(output_file)
        print(colored(f'PASR pre-processed data written to {output_file}\n', 'green'))
    else:
        raise ValueError(colored('Unsupported output file format. Only MRC, TIF, and JPG for 2D images are supported.', 'red'))

# Function to process a directory
def process_directory(input_dir, output_dir, scale, compression, flip_tif, force_tif, force_mrc, force_jpg, n_cores, keep_basename):
    """Processes a directory: lists all files and processes each of them.

    Args:
    input_dir : str, path to the input directory
    output_dir : str, path to the output directory
    scale : int, scale factor
    compression : str, compression method
    flip_tif : bool, whether to flip the image
    force_tif : bool, whether to force TIF output
    force_mrc : bool, whether to force MRC output
    force_jpg : bool, whether to force JPG output
    n_cores : int, number of CPU cores to use
    keep_basename : bool, whether to keep the original file basename

    Returns:
    None
    """
    # Listing all files in the directory
    file_list = glob.glob(os.path.join(input_dir, "*"))
    # Creating the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Creating a list of arguments for multiprocessing
    arguments = []
    for input_file in file_list:
        base_name, ext = os.path.splitext(os.path.basename(input_file))
        if keep_basename:
            output_file = os.path.join(output_dir, f"{base_name}{ext}")
        elif force_tif:
            output_file = os.path.join(output_dir, f"{base_name}_PASR_{scale}x.tif")
        elif force_mrc:
            output_file = os.path.join(output_dir, f"{base_name}_PASR_{scale}x.mrc")
        elif force_jpg:
            output_file = os.path.join(output_dir, f"{base_name}_PASR_{scale}x.jpg")
        else:
            output_file = os.path.join(output_dir, f"{base_name}_PASR_{scale}x{ext}")
        if flip_tif is None:
            flip_tif = input_file.lower().endswith(('.mrc', '.mrcs')) and output_file.lower().endswith(('.tif', '.tiff'))
        arguments.append((input_file, output_file, scale, compression, flip_tif))

    # Using a multiprocessing pool to process all files in parallel
    with Pool(n_cores) as p:
        p.starmap(process_file, arguments)

if __name__ == "__main__":
    # Parsing command line arguments
    parser = argparse.ArgumentParser(description="PASR Pre-process MRC and TIF frame stacks and MRC, TIF, and JPG images.")
    parser.add_argument("input", type=str, help="Input MRC, MRCS, TIF, TIFF, or JPG file, or directory containing such files.")
    parser.add_argument("-s", "--scale", type=int, choices=range(2, 5), default=2, help="Scaling factor (number of times to duplicate each pixel)")
    parser.add_argument("-o", "--output", type=str, help="Output MRC, TIF, or TIFF file, or directory to store processed files.")
    parser.add_argument("-c", "--compression", type=str, choices=['zlib', 'lzw'], default='lzw', help="Compression algorithm for TIF output.")
    parser.add_argument("-n", "--n_cores", type=int, default=os.cpu_count(), help="Number of CPU cores to use for parallel processing.")
    parser.add_argument("-k", "--keep_basename", action="store_true", help="Keep the original basename for the output file(s); do not append _PASR_{scale}x.")
    parser.add_argument("--flip_tif", default=None, action='store_true', help="Option to flip TIF output across the x-axis. Default is True for MRC/MRCS input and TIF/TIFF output, False otherwise, unless specified.")
    parser.add_argument("--force_tif", action="store_true", help="Force the output file extension to be .tif. This is useful because .tif output uses ZLIB or LZW compression.")
    parser.add_argument("--force_mrc", action="store_true", help="Force the output file extension to be .mrc. This exists just for completion.")
    parser.add_argument("--force_jpg", action="store_true", help="Force the output file extension to be .jpg for 2D images. This exists just for fun.")
    args = parser.parse_args()

    # Checking if the input is a directory
    if os.path.isdir(args.input):
        # If the output path is not specified or it's a file, raise an error
        if args.output is None or not os.path.isdir(args.output):
            raise ValueError(colored('If input is a directory, output must also be a directory.', 'red'))

        # Adding user confirmation for potential file overwriting
        if os.path.normpath(args.input) == os.path.normpath(args.output):
            confirm = input(colored('Warning: Your input and output directories are the same. This will overwrite your files. Continue? [y/N]', 'yellow'))
            if confirm.lower() != 'y':
                exit()

        process_directory(args.input, args.output, args.scale, args.compression, args.flip_tif, args.force_tif, args.force_mrc, args.force_jpg, args.n_cores, args.keep_basename)
    else:
        # If the output file is not specified, we create one with the same name as the input, but append "_PASR" before the extension
        if args.output is None:
            base_name, ext = os.path.splitext(args.input)
            if args.keep_basename:
                args.output = f"{base_name}{ext}"
            else:
                args.output = f"{base_name}_PASR_{args.scale}x{ext}"

        # Overwriting file extension if necessary
        if args.force_tif:
            base_name, ext = os.path.splitext(args.output)
            args.output = f"{base_name}.tif"
        if args.force_mrc:
            base_name, ext = os.path.splitext(args.output)
            args.output = f"{base_name}.mrc"
        if args.force_jpg:
            base_name, ext = os.path.splitext(args.output)
            args.output = f"{base_name}.jpg"

        # Determine if the output should be flipped
        if args.flip_tif is None:
            args.flip_tif = args.input.lower().endswith(('.mrc', '.mrcs')) and args.output.lower().endswith(('.tif', '.tiff'))

        # Adding user confirmation for potential file overwriting
        if os.path.normpath(args.input) == os.path.normpath(args.output):
            confirm = input(colored('Warning: Your input and output files are the same. This will overwrite your file. Continue? [y/N]', 'yellow'))
            if confirm.lower() != 'y':
                exit()

        process_file(args.input, args.output, args.scale, args.compression, args.flip_tif)

