import csv
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from html import unescape
from io import BytesIO, StringIO
from pathlib import Path
from xml.etree import ElementTree


MAX_STORED_CHARS = 200_000
BUNDLED_BIN_DIR = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin"
BUNDLED_PYTHON = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".log",
    ".csv",
    ".json",
    ".html",
    ".htm",
    ".xml",
    ".rtf",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}


def clean_text(value):
    value = unescape(value or "")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def decode_bytes(data):
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def strip_markup(text):
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text(text)


def parse_csv_text(text):
    rows = []
    reader = csv.reader(StringIO(text))
    for row in reader:
        rows.append(" | ".join(cell.strip() for cell in row if cell.strip()))
    return clean_text("\n".join(row for row in rows if row))


def parse_json_text(text):
    parsed = json.loads(text)
    return clean_text(json.dumps(parsed, indent=2, ensure_ascii=False))


def xml_text_from_zip(data, members):
    chunks = []
    with zipfile.ZipFile(BytesIO(data)) as archive:
        for name in members:
            try:
                xml_data = archive.read(name)
            except KeyError:
                continue
            root = ElementTree.fromstring(xml_data)
            text_nodes = [node.text for node in root.iter() if node.text and node.text.strip()]
            if text_nodes:
                chunks.append(" ".join(text_nodes))
    return clean_text("\n\n".join(chunks))


def parse_docx(data):
    return xml_text_from_zip(data, ["word/document.xml"])


def parse_pptx(data):
    with zipfile.ZipFile(BytesIO(data)) as archive:
        slide_names = sorted(name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
    return xml_text_from_zip(data, slide_names)


def parse_xlsx(data):
    chunks = []
    with zipfile.ZipFile(BytesIO(data)) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [" ".join(node.itertext()).strip() for node in root]

        sheet_names = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        for sheet_name in sheet_names:
            root = ElementTree.fromstring(archive.read(sheet_name))
            for row in root.iter():
                if not row.tag.endswith("row"):
                    continue
                cells = []
                for cell in row:
                    if not cell.tag.endswith("c"):
                        continue
                    value_node = next((child for child in cell if child.tag.endswith("v")), None)
                    inline_node = next((child for child in cell.iter() if child.tag.endswith("t")), None)
                    if value_node is not None and value_node.text is not None:
                        value = value_node.text
                    elif inline_node is not None and inline_node.text is not None:
                        value = inline_node.text
                    else:
                        continue
                    if cell.attrib.get("t") == "s" and value.isdigit() and int(value) < len(shared_strings):
                        value = shared_strings[int(value)]
                    cells.append(value)
                if cells:
                    chunks.append(" | ".join(cells))
    return clean_text("\n".join(chunks))


def parse_pdf(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            PdfReader = None

    if PdfReader is None:
        binary = find_binary("pdftotext")
        if binary:
            command = [binary, "-layout", "-", "-"]
        elif BUNDLED_PYTHON.exists():
            script = (
                "import io,sys;"
                "from pypdf import PdfReader;"
                "reader=PdfReader(io.BytesIO(sys.stdin.buffer.read()));"
                "sys.stdout.write('\\n\\n'.join((page.extract_text() or '') for page in reader.pages))"
            )
            command = [str(BUNDLED_PYTHON), "-c", script]
        else:
            raise ValueError("PDF reader is not available on this server. Install pypdf.")

        result = subprocess.run(command, input=data, capture_output=True, check=False, timeout=60)
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(error or "Could not extract text from PDF.")
        return clean_text(decode_bytes(result.stdout))

    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return clean_text("\n\n".join(pages))


def find_binary(name):
    system_binary = shutil.which(name)
    if system_binary:
        return system_binary
    bundled_binary = BUNDLED_BIN_DIR / name
    if bundled_binary.exists():
        return str(bundled_binary)
    return None


def parse_legacy_office(filename, data):
    binary = find_binary("soffice")
    if not binary:
        raise ValueError(f"{Path(filename).suffix.upper()} conversion requires LibreOffice.")

    with tempfile.TemporaryDirectory(prefix="pingpilot-doc-") as temp_dir:
        input_path = Path(temp_dir) / Path(filename).name
        input_path.write_bytes(data)
        result = subprocess.run(
            [binary, "--headless", "--convert-to", "txt:Text", "--outdir", temp_dir, str(input_path)],
            capture_output=True,
            check=False,
            timeout=90,
        )
        output_path = input_path.with_suffix(".txt")
        if result.returncode != 0 or not output_path.exists():
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(error or f"Could not convert {Path(filename).suffix.upper()} document.")
        return clean_text(decode_bytes(output_path.read_bytes()))


def parse_rtf(text):
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return clean_text(text)


def extract_document_text(filename, data):
    suffix = Path(filename).suffix.lower()
    text = ""

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
    if not data:
        raise ValueError("Document is empty.")

    if suffix in {".txt", ".md", ".markdown", ".log"}:
        text = decode_bytes(data)
    elif suffix == ".csv":
        text = parse_csv_text(decode_bytes(data))
    elif suffix == ".json":
        text = parse_json_text(decode_bytes(data))
    elif suffix in {".html", ".htm", ".xml"}:
        text = strip_markup(decode_bytes(data))
    elif suffix == ".rtf":
        text = parse_rtf(decode_bytes(data))
    elif suffix == ".docx":
        text = parse_docx(data)
    elif suffix == ".doc":
        text = parse_legacy_office(filename, data)
    elif suffix == ".pptx":
        text = parse_pptx(data)
    elif suffix == ".ppt":
        text = parse_legacy_office(filename, data)
    elif suffix == ".xlsx":
        text = parse_xlsx(data)
    elif suffix == ".xls":
        text = parse_legacy_office(filename, data)
    elif suffix == ".pdf":
        text = parse_pdf(data)

    text = clean_text(text)
    if not text:
        raise ValueError("No readable text found in document.")
    return text[:MAX_STORED_CHARS]
