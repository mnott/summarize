# summarize

# summarize: Convert Screen Shots into a Readable Text and create a summary; also works with PDFs.

This script provides functionality to convert screenshots and PDFs into a readable text format,
generate summaries, and create styled PDF outputs. It can operate in two modes:

1. **Image Mode**: Process PNG/JPG/JPEG screenshots in the current directory
2. **PDF Mode**: Recursively analyze PDFs in subdirectories with financial summary

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

## Automatic Mode Detection

The script automatically detects which mode to use:

```bash
./summarize.py
```

- If PNG/JPG/JPEG files are found in the current directory → Image mode
- If PDFs are found in subdirectories → PDF recursive analysis mode

## Image Mode: Summarize screenshots

```bash
./summarize.py
```

This will process PNG, JPG, and JPEG files in the current directory and create a styled PDF summary.

## PDF Mode: Recursive financial analysis

```bash
./summarize.py
```

When PDFs are detected in subdirectories, the script will:
- Recursively scan all subdirectories for PDF files
- Extract text and amounts from each PDF
- Generate AI summaries for each directory
- Create aggregate summaries for parent directories
- Output three files at the root level:
  - `summary_TIMESTAMP.json` - Complete analysis data
  - `summary_TIMESTAMP.xlsx` - Excel workbook with financial summary
  - `summary_TIMESTAMP.pdf` - Formatted PDF report

### Features:
- **Multi-currency support**: Automatically detects and tracks any valid ISO currency
- **Smart amount extraction**: Finds total amounts in receipts across multiple languages
- **Parallel processing**: Uses multiple threads for faster analysis
- **Rate limit handling**: Gracefully handles API rate limiting
- **Non-receipt PDFs**: Processes all PDFs, even non-financial documents

### Output Format:
The Excel summary includes:
- Directory path
- Document type (PDFs or Aggregate)
- Number of documents
- Processing date
- Separate columns for each currency found
- Total row with sums (using SUBTOTAL for filtering support)

## Summarize specific files

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

## find_pdfs_recursively

Find all PDF files recursively in a directory and group them by parent directory.
Excludes generated summary PDFs to avoid double processing.

Args:
    directory: Root directory to search
    
Returns:
    Dictionary mapping directory paths to lists of PDF files in that directory

## extract_text_from_pdf_simple

Extract all text from a PDF file (without OCR - assumes text is already embedded).

Args:
    pdf_path: Path to the PDF file
    
Returns:
    Dictionary containing extracted text and metadata

## extract_amounts_from_text

Extract monetary amounts and their currencies from text.
Focus on total amounts in summaries.

Returns:
    List of (amount, currency) tuples

## create_pdf_summary

Create a summary of extracted PDF texts using AI.

Args:
    texts: List of extracted text dictionaries
    directory: Directory being processed
    
Returns:
    Summary text

## process_pdf_directory

Process all PDFs in a directory and create a summary file.

Args:
    directory: Directory to process
    output_format: Output format ('txt' or 'json')
    show_progress: Whether to show progress messages
    
Returns:
    Processing results

## create_aggregate_summary

Create an aggregate summary for a parent directory based on subdirectory results.
Returns both the summary text and structured data.

## cleanup_intermediate_files

Remove all intermediate summary files recursively, optionally keeping root files.

Args:
    directory: Root directory
    timestamp: Run timestamp to identify files from this run
    keep_root: If True, keep files in the root directory

## create_master_json

Create a master JSON file with all data from the analysis.

Args:
    directory: Root directory for the analysis
    all_data: Complete in-memory data structure
    timestamp: Run timestamp
    
Returns:
    Path to the created master JSON file

## create_summary_pdf_from_data

Create a styled PDF summary from the analysis data.

Args:
    all_data: Complete in-memory data structure
    output_path: Path for the output PDF
    css_file: Optional CSS file for styling

## create_excel_summary

Create an Excel file with structured summary data.

Args:
    directory: Root directory for the analysis
    all_data: Complete in-memory data structure
    timestamp: Run timestamp
    
Returns:
    Path to the created Excel file

## display_summary_table

Display a rich table with summary data in the console.

Args:
    all_data: Complete in-memory data structure

## analyze_pdfs_recursively

Recursively analyze PDFs in directories and create hierarchical summaries.

## detect_processing_mode

Detect whether to use image processing or PDF recursive processing.

Returns:
    'images' for image processing (PNG/JPG/JPEG in current dir)
    'pdfs' for recursive PDF processing (PDFs in subdirectories)
    'none' if no processable files found

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
    args (tuple): Tuple containing (png_file, temp_dir, i, use_original_resolution).

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

Generate a summary from input files (PDFs or images).

This command automatically detects the type of processing needed:
- If PNG/JPG/JPEG files are found in the current directory: Creates a styled PDF summary
- If PDFs are found in subdirectories: Creates recursive text summaries with totals

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


