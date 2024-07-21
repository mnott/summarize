#!/usr/bin/env python3
# encoding: utf-8

r"""
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
"""

# Standard library imports
import contextlib
import glob
import io
import logging
import multiprocessing
import os
import re
import sys
import tempfile
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Third-party imports
import cssutils
import fitz
import img2pdf
import markdown
import nltk
import numpy as np
import pytesseract
import spacy
import typer
from bs4 import BeautifulSoup
from InquirerPy import inquirer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from pdf2image import convert_from_path
from PIL import Image, ImageChops, UnidentifiedImageError
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor, Color, black, white
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak, Table, TableStyle
from rich import print
from rich.console import Console
from rich.progress import Progress
from skimage.metrics import structural_similarity as ssim
from transformers import pipeline

# Local imports
from client import AIClient, GitConfig, DocGenerator

# Suppress warnings
warnings.filterwarnings("ignore")

# Initialize console
console = Console()

# Initialize Typer app
app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
    help="summarize: Convert Screen Shots into a Readable Text and create a summary; also works with PDFs.",
    epilog="To get help about the script, call it with the --help option."
)


class SuppressOutput:
    """
    A context manager for suppressing stdout and stderr output.
    """
    def __enter__(self):
        self.stdout = os.dup(1)
        self.stderr = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
        logging.disable(logging.CRITICAL)
        return self

    def __exit__(self, *args):
        os.dup2(self.stdout, 1)
        os.dup2(self.stderr, 2)
        os.close(self.stdout)
        os.close(self.stderr)
        logging.disable(logging.NOTSET)

# Suppress specific library logging
transformers_logger = logging.getLogger('transformers')
transformers_logger.setLevel(logging.CRITICAL)

# Download necessary NLTK data
with SuppressOutput():
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)


def sort_by_creation_time(files):
    """
    Sort files by their creation time.

    Args:
        files (List[str]): List of file paths.

    Returns:
        List[str]: Sorted list of file paths.
    """
    return sorted(files, key=lambda x: os.path.getctime(x))


def crop_image(image_path, padding=10):
    """
    Crop an image to remove any surrounding whitespace and add padding for print borders.

    Args:
        image_path (str): Path to the image file.
        padding (int): Amount of padding to add around the cropped area. Default is 10 pixels.

    Returns:
        PIL.Image.Image: Cropped image with padding.
    """
    img = Image.open(image_path)
    bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()

    if bbox:
        left, upper, right, lower = bbox
        cropped_img = img.crop((left, upper, right, lower))

        # Create a new image with horizontal padding
        padded_img = Image.new(img.mode, (cropped_img.width + 2 * padding, cropped_img.height), img.getpixel((0, 0)))
        padded_img.paste(cropped_img, (padding, 0))
        return padded_img
    else:
        return img


def convert_images_to_pdf(image_paths, output_path, padding_ratio=0.02):
    """
    Convert a list of images to a single PDF file with proportional padding and maintained quality.

    Args:
        image_paths (List[str]): List of image file paths.
        output_path (str): Path to save the output PDF.
        padding_ratio (float): Ratio of padding to add around the cropped area of each image relative to the page width. Default is 0.05 (5% of the page width).
    """
    page_width, page_height = landscape(A4)
    padding = int(page_width * padding_ratio)  # Calculate padding based on page width
    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

    for image_path in image_paths:
        img = crop_image(image_path, padding)
        img_width, img_height = img.size

        # Calculate scaling factor to fit the image within the page with padding
        max_width = page_width - 2 * padding
        max_height = page_height #  - 2 * padding
        scale = min(max_width / img_width, max_height / img_height)

        scaled_width = int(img_width * scale)
        scaled_height = int(img_height * scale)

        x_position = (page_width - scaled_width) / 2
        y_position = (page_height - scaled_height) / 2

        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        c.drawImage(ImageReader(img_buffer), x_position, y_position, width=scaled_width, height=scaled_height)
        c.showPage()

    c.save()


def apply_ocr(pdf_path):
    """
    Apply Optical Character Recognition (OCR) to a PDF file.

    Args:
        pdf_path (str): Path to the input PDF file.

    Returns:
        str: Extracted text from the PDF.
    """
    with SuppressOutput():
        images = convert_from_path(pdf_path)

    writer = PdfWriter()
    extracted_text = ""

    for image in images:
        with SuppressOutput():
            text = pytesseract.image_to_string(image)
            extracted_text += text + "\n"
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(image, extension='pdf')
        new_pdf = PdfReader(io.BytesIO(pdf_bytes))
        writer.add_page(new_pdf.pages[0])

    with open(pdf_path, 'wb') as f:
        writer.write(f)

    return extracted_text


def are_images_similar(img1_path, img2_path, threshold=0.95):
    """
    Check if two images are similar using structural similarity index.

    Args:
        img1_path (str): Path to the first image.
        img2_path (str): Path to the second image.
        threshold (float): Similarity threshold.

    Returns:
        bool: True if images are similar, False otherwise.
    """
    img1 = Image.open(img1_path).convert('L')
    img2 = Image.open(img2_path).convert('L')
    img2 = img2.resize(img1.size)
    img1_array = np.array(img1)
    img2_array = np.array(img2)
    similarity = ssim(img1_array, img2_array)
    return similarity > threshold


def check_similarity(args):
    img, image, threshold = args
    return are_images_similar(img, image, threshold)

def filter_similar_images(image_files, threshold=0.95, num_workers=None, progress=None, filter_task=None):
    """
    Filter out similar images from a list of image files using parallel processing.

    Args:
        image_files (List[str]): List of image file paths.
        threshold (float): Similarity threshold.
        num_workers (int, optional): Number of parallel workers to use. Default is None, which uses all available cores.

    Returns:
        List[str]: Filtered list of image file paths.
    """
    if not image_files:
        return []

    filtered_images = [image_files[0]]
    remaining_images = image_files[1:]

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for image in remaining_images:
            tasks = [(img, image, threshold) for img in filtered_images]
            similarities = list(executor.map(check_similarity, tasks))
            if not any(similarities):
                filtered_images.append(image)
            if progress:
                progress.advance(filter_task)

    return filtered_images


def process_image(args):
    """
    Process a single image file.

    Args:
        args (tuple): Tuple containing (png_file, temp_dir, i).

    Returns:
        tuple: (pdf_path, extracted_text)
    """
    png_file, temp_dir, i = args
    pdf_path = os.path.join(temp_dir, f"temp_{i}.pdf")
    with SuppressOutput():
        convert_images_to_pdf([png_file], pdf_path)
        extracted_text = apply_ocr(pdf_path)
    return pdf_path, extracted_text


def clean_text(text):
    """
    Clean and preprocess text by removing stop words and meaningless sentences.

    Args:
        text (str): Input text to clean.

    Returns:
        str: Cleaned text.
    """
    nlp = spacy.load("en_core_web_sm")
    stop_words = set(stopwords.words('english'))
    sentences = sent_tokenize(text)
    meaningful_sentences = []
    for sentence in sentences:
        words = word_tokenize(sentence)
        filtered_words = [word for word in words if word.isalpha() and word.lower() not in stop_words]
        filtered_sentence = ' '.join(filtered_words)
        doc = nlp(filtered_sentence)
        if any(token.pos_ in ['NOUN', 'VERB', 'ADJ', 'ADV'] for token in doc):
            meaningful_sentences.append(filtered_sentence)
    cleaned_text = ' '.join(meaningful_sentences)
    return cleaned_text.strip()


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text from the PDF.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def generate_summary(text, max_tokens=1000):
    """
    Generate a summary of the given text using an AI model.

    Args:
        text (str): Input text to summarize.
        max_tokens (int): Maximum number of tokens for the summary.

    Returns:
        str: Generated summary.
    """
    text = clean_text(text)

    ai_client = AIClient(config_provider=GitConfig())
    console.print(f"[blue]Using {ai_client.name} to generate a summary...[/blue]")
    prompt = f"""
    Please provide a concise summary of the following text, followed by a bulleted list
    of the main topics and their explanations. Format the output exactly as follows,
    using markdown formatting:

    # Summary:
    [Your concise summary here]

    # Main Topics:

    ## [Topic 1]:

    [Your Summary of Topic 1: you can be quite a bit more detailed here and use
    multiple sentences if necessary and give context]

    - [Explanation point 1]
    - [Explanation point 2]

    ## [Topic 2]:

    [Your Summary of Topic 2: you can be quite a bit more detailed here and use
    multiple sentences if necessary and give context]

    - [Explanation point 1]
    - [Explanation point 2]

    [and so on...]

    Important: Start your response directly with the summary. Do not use
    any introductory phrases like "Sure," "Here's," or "Certainly."

    You don't need to specially mention things like "Multilingual elements
    suggesting the document may be available in multiple languages".

    Here's the text to summarize:

    {text}
    """

    try:
        response = ai_client.prompt(prompt, tokens=max_tokens)
        return response
    except Exception as e:
        console.print(f"[red]Error getting response from AI: {str(e)}[/red]")
        console.print(f"[yellow]Prompt:[/yellow] {prompt}")
        return None


def parse_css_value(value, default):
    """
    Parse CSS value and return the corresponding numeric value.

    Args:
        value (str): CSS value to parse.
        default: Default value to return if parsing fails.

    Returns:
        int or str: Parsed value.
    """
    if isinstance(value, str):
        if value.endswith('%'):
            return value
        match = re.match(r'(\d+)(?:px)?', value)
        if match:
            return int(match.group(1))
    return default


def parse_color(color_string):
    """
    Parse color string and return the corresponding Color object.

    Args:
        color_string (str): Color string to parse.

    Returns:
        reportlab.lib.colors.Color: Parsed color object.
    """
    if not color_string:
        return black

    color_string = color_string.strip()
    if color_string.startswith('#'):
        if len(color_string) == 4:
            r = int(color_string[1] * 2, 16) / 255.0
            g = int(color_string[2] * 2, 16) / 255.0
            b = int(color_string[3] * 2, 16) / 255.0
            return Color(r, g, b)
        elif len(color_string) == 7:
            try:
                r = int(color_string[1:3], 16) / 255.0
                g = int(color_string[3:5], 16) / 255.0
                b = int(color_string[5:7], 16) / 255.0
                return Color(r, g, b)
            except ValueError:
                print(f"Invalid hex color: {color_string}")
                return black
        else:
            print(f"Invalid hex color format: {color_string}")
            return black
    else:
        try:
            return Color(color_string)
        except:
            print(f"Invalid color name: {color_string}")
            return black


def create_summary_pdf(summary, output_path, css_path):
    """
    Create a styled PDF summary from the given text and CSS file.

    Args:
        summary     (str): Summary text in markdown format.
        output_path (str): Path to save the output PDF.
        css_path    (str): Path to the CSS file for styling.
    """
    if not summary:
        raise ValueError("Summary content is empty")

    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)

    # Get sample stylesheet as a fallback
    sample_styles = getSampleStyleSheet()

    # Parse CSS file
    with open(css_path, 'r') as css_file:
        css = cssutils.parseString(css_file.read())

    # Create styles based on CSS
    styles = {}
    for rule in css:
        if rule.type == rule.STYLE_RULE:
            selector = rule.selectorText.strip('.')
            style_dict = {p.name: p.value for p in rule.style}

            # Use sample style as a base, then override with CSS values
            base_style = sample_styles['BodyText']
            new_style = ParagraphStyle(
                selector,
                parent=base_style,
                fontSize       = parse_css_value(style_dict.get('font-size'),     base_style.fontSize),
                leading        = parse_css_value(style_dict.get('line-height'),   base_style.leading),
                spaceBefore    = parse_css_value(style_dict.get('margin-top'),    base_style.spaceBefore),
                spaceAfter     = parse_css_value(style_dict.get('margin-bottom'), base_style.spaceAfter),
                leftIndent     = parse_css_value(style_dict.get('padding-left'),  base_style.leftIndent),
                rightIndent    = parse_css_value(style_dict.get('padding-right'), base_style.rightIndent),
                firstLineIndent= parse_css_value(style_dict.get('text-indent'),   base_style.firstLineIndent),
                textColor      = parse_color    (style_dict.get('color',            '#000000')),
                backColor      = parse_color    (style_dict.get('background-color', '#FFFFFF')),
            )

            # Handle text alignment
            text_align = style_dict.get('text-align', '').lower()
            if text_align == 'justify':
                new_style.alignment = TA_JUSTIFY
            elif text_align == 'center':
                new_style.alignment = TA_CENTER
            elif text_align == 'right':
                new_style.alignment = TA_RIGHT
            else:
                new_style.alignment = TA_LEFT

            # Handle text transformation
            if style_dict.get('text-transform') == 'uppercase':
                new_style.textTransform = 'uppercase'

            styles[selector] = new_style

            # print(f"Selector: {selector}")
            # print(f"Text Color: {new_style.textColor}")
            # print(f"Background Color: {new_style.backColor}")

    story = []

    # Convert Markdown to HTML
    html = markdown.markdown(summary)
    soup = BeautifulSoup(html, 'html.parser')

    # Get the available width for content
    available_width = A4[0] - 2*inch  # Subtracting left and right margins

    # Parse HTML and create paragraphs or tables for styled elements
    for element in soup.descendants:
        if element.name in ['h1', 'h2']:
            style_name = 'heading1' if element.name == 'h1' else 'heading2'
            text = element.get_text().strip()
            style = styles.get(style_name, sample_styles['Heading1'])

            # Apply text transformation if specified in CSS
            if hasattr(style, 'textTransform') and style.textTransform == 'uppercase':
                text = text.upper()

            # Create a table for both heading1 and heading2 with background color and border
            t = Table([[text]], colWidths=[available_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), style.backColor),
                ('TEXTCOLOR', (0,0), (-1,-1), style.textColor),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,-1), style.fontName),
                ('FONTSIZE', (0,0), (-1,-1), style.fontSize),
                ('BOTTOMPADDING', (0,0), (-1,-1), parse_css_value(style_dict.get('padding-bottom', '5'), 5)),
                ('TOPPADDING', (0,0), (-1,-1), parse_css_value(style_dict.get('padding-top', '5'), 5)),
                ('LEFTPADDING', (0,0), (-1,-1), parse_css_value(style_dict.get('padding-left', '10'), 10)),
                ('RIGHTPADDING', (0,0), (-1,-1), parse_css_value(style_dict.get('padding-right', '10'), 10)),
                ('LEADING', (0,0), (-1,-1), style.leading),
            ]))
            story.append(t)

            story.append(Spacer(1, parse_css_value(style.spaceAfter, 12)))
        elif element.name == 'p':
            story.append(Paragraph(element.get_text(), styles.get('bodytext', sample_styles['BodyText'])))
            story.append(Spacer(1, 12))
        elif element.name == 'ul':
            for li in element.find_all('li'):
                story.append(Paragraph(f'• {li.get_text()}', styles.get('bullet', sample_styles['BodyText'])))
                story.append(Spacer(1, 12))

    # Add a page break for multi-page support
    story.append(PageBreak())

    # Build PDF
    doc.build(story)


@app.command()
def summarize(
    input_files:     List[str] = typer.Argument(None,                               help="Paths to input files (PDFs or images)"),
    output_file:           str = typer.Option("summary.pdf", "-o", "--output-file", help="Path to the output summary PDF file"),
    css_file:    Optional[str] = typer.Option(None,          "-c", "--css-file",    help="Path to the CSS file for styling"),
    max_tokens:            int = typer.Option(1000,          "-m", "--max-tokens",  help="Maximum number of tokens for summary generation", show_default=True)
):
    """
    Generate a summary PDF from input files (PDFs or images).

    This command processes input files (PDFs and images), extracts text, generates a summary,
    and creates a styled PDF output with the summary and original content.
    """
    console.print("[blue]Starting summarize command...[/blue]")

    if input_files is None or len(input_files) == 0:
        console.print("[blue]No input files provided. Using all PNG, JPG, and JPEG files in the current directory.[/blue]")
        input_files = glob.glob("*.png") + glob.glob("*.jpg") + glob.glob("*.jpeg")

    if not input_files:
        console.print("[red]No input files found.[/red]")
        return

    # Use default CSS file if no CSS file is provided
    if css_file is None:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        css_file = os.path.join(script_dir, "styles.css")

    pdf_files = [f for f in input_files if f.lower().endswith('.pdf')]
    image_files = [f for f in input_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    all_text = ""

    with Progress() as progress:
        try:
            merger = PdfMerger()

            if pdf_files:
                pdf_task = progress.add_task("[green]Processing PDFs...", total=len(pdf_files))
                for pdf in pdf_files:
                    merger.append(pdf)
                    text = extract_text_from_pdf(pdf)
                    all_text += text + "\n"
                    progress.advance(pdf_task)

            if image_files:
                valid_images = []
                for image in image_files:
                    try:
                        with Image.open(image) as img:
                            valid_images.append(image)
                    except UnidentifiedImageError:
                        console.print(f"[red]Skipping invalid image file: {image}[/red]")

                sorted_files = sort_by_creation_time(valid_images)

                # Filter similar images with progress update
                filter_task = progress.add_task("[blue]Filtering  images...", total=len(sorted_files))
                filtered_files = filter_similar_images(sorted_files, num_workers=multiprocessing.cpu_count(), progress=progress, filter_task=filter_task)
                progress.update(filter_task, advance=len(sorted_files) - len(filtered_files))

                image_task = progress.add_task("[blue]Processing images...", total=len(filtered_files))
                with tempfile.TemporaryDirectory() as temp_dir:
                    num_cores = multiprocessing.cpu_count()
                    with ProcessPoolExecutor(max_workers=num_cores) as executor:
                        futures = [executor.submit(process_image, (png, temp_dir, i)) for i, png in enumerate(filtered_files)]
                        for future in as_completed(futures):
                            try:
                                pdf_path, extracted_text = future.result()
                                merger.append(pdf_path)
                                all_text += extracted_text + "\n"
                                progress.advance(image_task)
                            except Exception as e:
                                console.print(f"[red]Error processing image: {e}[/red]")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output_file:
                temp_output_pdf_path = temp_output_file.name

            merger.write(temp_output_pdf_path)
            merger.close()

        except Exception as e:
            console.print(f"[red]Error creating the final PDF: {str(e)}[/red]")
            return

        progress.stop()

        summary = generate_summary(all_text, max_tokens)

        if summary is None:
            console.print("[red]Failed to generate summary. Please check your AI configuration and try again.[/red]")
            return

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                summary_pdf_path = os.path.join(temp_dir, "summary.pdf")
                create_summary_pdf(summary, summary_pdf_path, css_file)

                # Get the modification time of the first file used
                if filtered_files:
                    first_file_modification_time = datetime.fromtimestamp(os.path.getmtime(filtered_files[0]))
                else:
                    first_file_modification_time = datetime.now()  # Fallback to current time if no files are sorted

                date_time_str = first_file_modification_time.strftime("%Y%m%d_%H%M")
                output_base_name = os.path.splitext(output_file)[0]
                final_output_filename = f"{output_base_name}_{date_time_str}.pdf"
                final_output_path = os.path.abspath(final_output_filename)

                final_merger = PdfMerger()
                final_merger.append(summary_pdf_path)
                final_merger.append(temp_output_pdf_path)

                final_merger.write(final_output_path)
                final_merger.close()
                console.print(f"[green]Summary PDF created at {final_output_path}[/green]")
        except Exception as e:
            console.print(f"[red]Error creating summary PDF: {str(e)}[/red]")
        finally:
            if 'temp_output_pdf_path' in locals() and os.path.exists(temp_output_pdf_path):
                os.remove(temp_output_pdf_path)


@app.command()
def config(
    provider:     Optional[str] = typer.Argument(None,                          help="The AI provider to configure"),
    set_default:           bool = typer  .Option(False,  "-d", "--set-default", help="Set the specified provider as default")
):
    """
    Configure, update, create, delete, clone an AI provider interactively, or set the default provider.

    For reference, here is a typical configuration for GPT and Claude:

    ```ini
    [openai]
    name = openai
    aiprovider = true
    apikey = sk-proj-...
    model = gpt-4o
    url = https://api.openai.com/v1/chat/completions
    header = {Authorization: Bearer {api_key}}
    response = response.json()['choices'][0]['message']['content']

    [claude]
    name = Claude
    aiprovider = true
    apikey = sk-ant-...
    model = claude-3-5-sonnet-20240620
    url = https://api.anthropic.com/v1/messages
    header = {x-api-key: {api_key}, anthropic-version: 2023-06-01}
    response = response.json()['content'][0]['text']
    ```

    """
    git_config = GitConfig()
    available_providers = git_config.get_available_providers()

    if set_default:
        if provider:
            if provider in available_providers:
                git_config.set_default_provider(provider)
                console.print(f"[green]Set {provider} as the default AI provider.[/green]")
            else:
                console.print(f"[red]Provider '{provider}' not found. Cannot set as default.[/red]")
        else:
            if available_providers:
                default_provider = inquirer.select(
                    message="Select the default AI provider:",
                    choices=available_providers
                ).execute()
                git_config.set_default_provider(default_provider)
                console.print(f"[green]Set {default_provider} as the default AI provider.[/green]")
            else:
                console.print("[red]No AI providers found. Cannot set a default provider.[/red]")
        return

    if not available_providers and provider is None:
        console.print("[yellow]No AI providers found. Let's create one.[/yellow]")
        provider = inquirer.text(message="Enter a name for the new provider:").execute()

    if provider is None:
        choices = available_providers + ["Create new provider", "Clone existing provider", "Set default provider"]

        selected = inquirer.select(
            message="Select an action:",
            choices=choices
        ).execute()

        if selected == "Create new provider":
            provider = inquirer.text(message="Enter the name for the new provider:").execute()
        elif selected == "Clone existing provider":
            source_provider = inquirer.select(
                message="Select a provider to clone:",
                choices=available_providers
            ).execute()
            target_provider = inquirer.text(message="Enter the name for the cloned provider:").execute()
            if git_config.clone_provider(source_provider, target_provider):
                provider = target_provider
            else:
                return
        elif selected == "Set default provider":
            default_provider = inquirer.select(
                message="Select the default AI provider:",
                choices=available_providers
            ).execute()
            git_config.set_default_provider(default_provider)
            console.print(f"[green]Set {default_provider} as the default AI provider.[/green]")
            return
        else:
            provider = selected

    git_config.configure_provider(provider)

    # Ask if the user wants to set this provider as default
    if inquirer.confirm(message=f"Do you want to set {provider} as the default AI provider?", default=False).execute():
        git_config.set_default_provider(provider)
        console.print(f"[green]Set {provider} as the default AI provider.[/green]")


@app.command()
def doc(
    ctx: typer.Context,
    title: str = typer.Option(None,  help="The title of the document"),
    toc:  bool = typer.Option(False, help="Whether to create a table of contents"),
) -> None:
    """
    Re-create the documentation and write it to the output file.

    This command generates documentation for the script, including an optional
    table of contents and custom title.
    """
    result = DocGenerator.generate_doc(__file__, title, toc)
    print(result)


#
# Main function
#
if __name__ == "__main__":
    import sys
    from typer.main import get_command,get_command_name
    if len(sys.argv) == 1 or sys.argv[1] not in [get_command_name(key) for key in get_command(app).commands.keys()]:
        sys.argv.insert(1, "summarize")
    app()
