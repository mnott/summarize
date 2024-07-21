# summarize

# summarize: Convert Screen Shots into a Readable Text and create a summary; also works with PDFs.

This script provides functionality to convert screenshots and PDFs into a readable text format,
generate summaries, and create styled PDF outputs.

# Installation

To install the required libraries, run the following command:

```bash
pip install -r requirements.txt
```

You may also need to

```bash
python -m spacy download en_core_web_sm
```


# Configuration

Before using the script, you need to configure your AI settings. You can do
this by running the following command:

```bash
./summarize.py config
```

Then you should define your default AI provider

```bash
./summarize.py config -d
```

# Usage

To get help about the script, call it with the `--help` option:

```bash
./summarize.py --help
```

## Summarize a bunch of images in the current directory

```bash
./summarize.py
```

This will take only pgn, jpg, and jpeg files in the current directory and summarize them.

## Summarize some specific files in order

```bash
./summarize.py file1.png file2.pdf
```

# Documentation

To generate the documentation for the script, run the following command:

```bash
./summarize.py doc
```

# License

This script is released under the [WTFPL License](https://en.wikipedia.org/wiki/WTFPL).

## SuppressOutput

A context manager for suppressing stdout and stderr output.

## sort_by_directory_order

Sort files to match the exact order shown in the directory listing.

Args:
    files (List): List of file paths.

Returns:
    List: Sorted list of file paths.

## crop_image

Crop an image to remove any surrounding whitespace and add padding for print borders.

Args:
    image_path (str): Path to the image file.
    padding (int): Amount of padding to add around the cropped area. Default is 10 pixels.

Returns:
    PIL.Image.Image: Cropped image with padding.

## convert_images_to_pdf

Convert a list of images to a single PDF file with proportional padding and maintained quality.

Args:
    image_paths (List): List of image file paths.
    output_path (str): Path to save the output PDF.
    padding_ratio (float): Ratio of padding to add around the cropped area of each image relative to the page width. Default is 0.05 (5% of the page width).

## apply_ocr

Apply Optical Character Recognition (OCR) to a PDF file.

Args:
    pdf_path (str): Path to the input PDF file.

Returns:
    str: Extracted text from the PDF.

## are_images_similar

Check if two images are similar using structural similarity index.

Args:
    img1_path (str): Path to the first image.
    img2_path (str): Path to the second image.
    threshold (float): Similarity threshold.

Returns:
    bool: True if images are similar, False otherwise.

## filter_similar_images

Filter out similar images from a list of image files using parallel processing.

Args:
    image_files (List): List of image file paths.
    threshold (float): Similarity threshold.
    num_workers (int, optional): Number of parallel workers to use. Default is None, which uses all available cores.

Returns:
    List: Filtered list of image file paths.

## process_image

Process a single image file.

Args:
    args (tuple): Tuple containing (png_file, temp_dir, i).

Returns:
    tuple: (pdf_path, extracted_text)

## clean_text

Clean and preprocess text by removing stop words and meaningless sentences.

Args:
    text (str): Input text to clean.

Returns:
    str: Cleaned text.

## extract_text_from_pdf

Extract text from a PDF file.

Args:
    pdf_path (str): Path to the PDF file.

Returns:
    str: Extracted text from the PDF.

## generate_summary

Generate a summary of the given text using an AI model.

Args:
    text (str): Input text to summarize.
    max_tokens (int): Maximum number of tokens for the summary.

Returns:
    str: Generated summary.

## parse_css_value

Parse CSS value and return the corresponding numeric value.

Args:
    value (str): CSS value to parse.
    default: Default value to return if parsing fails.

Returns:
    int or str: Parsed value.

## parse_color

Parse color string and return the corresponding Color object.

Args:
    color_string (str): Color string to parse.

Returns:
    reportlab.lib.colors.Color: Parsed color object.

## create_summary_pdf

Create a styled PDF summary from the given text and CSS file.

Args:
    summary     (str): Summary text in markdown format.
    output_path (str): Path to save the output PDF.
    css_path    (str): Path to the CSS file for styling.

## summarize

Generate a summary PDF from input files (PDFs or images).

This command processes input files (PDFs and images), extracts text, generates a summary,
and creates a styled PDF output with the summary and original content.

## config

Configure, update, create, delete, clone an AI provider interactively, or set the default provider.

For reference, here is a typical configuration for GPT and Claude:

```ini

name = openai
aiprovider = true
apikey = sk-proj-...
model = gpt-4o
url = https://api.openai.com/v1/chat/completions
header = {Authorization: Bearer {api_key}}
response = response.json()['choices'][0]['message']['content']


name = Claude
aiprovider = true
apikey = sk-ant-...
model = claude-3-5-sonnet-20240620
url = https://api.anthropic.com/v1/messages
header = {x-api-key: {api_key}, anthropic-version: 2023-06-01}
response = response.json()['content'][0]['text']
```

## doc

Re-create the documentation and write it to the output file.

This command generates documentation for the script, including an optional
table of contents and custom title.


