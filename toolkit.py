"""Offline PDF toolkit operations: merge, split, organize, image <-> PDF, draft export.

All functions are pure (no GUI) and write to a temporary file in the destination
folder, then move it into place, so a failed or interrupted operation never leaves a
half-written output. Encrypted inputs are rejected with a clear message unless an
unlock password is supplied; this toolkit does not try to recover unknown passwords.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import sys
import tempfile
import uuid

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError, FileNotDecryptedError

SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp'}


class ToolkitError(Exception):
    """A clear, user-facing problem with an operation."""


class PasswordNeeded(ToolkitError):
    """The input is protected and no (or no correct) open password was supplied yet."""


@dataclass
class Result:
    outputs: list[Path] = field(default_factory=list)
    pages: int = 0
    note: str = ''


def _fs(path) -> str:
    text = str(path)
    if sys.platform == 'win32' and len(text) >= 240 and not text.startswith('\\\\?\\'):
        text = os.path.abspath(text)
        return '\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\') else '\\\\?\\' + text
    return text


def _atomic(target: Path, write):
    """Call write(tmp_path); then move tmp onto target without overwriting silently."""
    target = Path(target)
    if target.exists():
        raise ToolkitError(f'A file named "{target.name}" already exists in the output folder. Rename or remove it first.')
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f'{target.name}.rar-tk-{uuid.uuid4().hex[:10]}')
    try:
        write(tmp)
        if sys.platform == 'win32':
            os.rename(_fs(tmp), _fs(target))
        else:
            os.replace(tmp, target)
    finally:
        try:
            if tmp.exists():
                os.unlink(_fs(tmp))
        except OSError:
            pass
    return target


def open_reader(path: Path, password: str | None = None) -> PdfReader:
    try:
        reader = PdfReader(_fs(path))
    except (PdfReadError, OSError, ValueError) as exc:
        raise ToolkitError(f'"{Path(path).name}" could not be read as a PDF ({type(exc).__name__}).') from None
    if reader.is_encrypted:
        if not password:
            raise PasswordNeeded(f'"{Path(path).name}" is password-protected. Enter its open password to continue.')
        try:
            if reader.decrypt(password) == 0:
                raise ToolkitError(f'The supplied password did not open "{Path(path).name}".')
        except (PdfReadError, FileNotDecryptedError, NotImplementedError) as exc:
            raise ToolkitError(f'"{Path(path).name}" could not be decrypted ({type(exc).__name__}).') from None
    return reader


def _require_openable(path: Path, password: str | None):
    """Uniform protection check (via pypdf) before an engine opens the file its own way."""
    open_reader(Path(path), password)


def _strip_protection_only(writer: PdfWriter):
    # Outputs from this toolkit are never re-encrypted; make that explicit.
    writer.encrypt('', '', permissions_flag=None) if False else None


def merge_pdfs(inputs: list[Path], output: Path, passwords: dict[str, str] | None = None) -> Result:
    if len(inputs) < 2:
        raise ToolkitError('Choose at least two PDFs to merge.')
    writer = PdfWriter()
    total = 0
    passwords = passwords or {}
    for item in inputs:
        reader = open_reader(Path(item), passwords.get(str(item)) or passwords.get(Path(item).name))
        for page in reader.pages:
            writer.add_page(page)
            total += 1

    def write(tmp):
        with open(_fs(tmp), 'wb') as fh:
            writer.write(fh)
    out = _atomic(output, write)
    return Result([out], total, f'{len(inputs)} files merged into {total} pages')


def split_pdf(input: Path, output_dir: Path, ranges: list[tuple[int, int]] | None = None,
              password: str | None = None) -> Result:
    reader = open_reader(Path(input), password)
    n = len(reader.pages)
    stem = Path(input).stem
    outputs = []
    if ranges is None:  # one file per page
        width = len(str(n))
        for i in range(n):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            target = Path(output_dir) / f'{stem}-p{str(i + 1).zfill(width)}.pdf'
            outputs.append(_atomic(target, lambda tmp, w=writer: _write_pdf(w, tmp)))
        return Result(outputs, n, f'Split into {n} single-page PDFs')
    for start, end in ranges:
        if not (1 <= start <= end <= n):
            raise ToolkitError(f'Page range {start}-{end} is outside 1-{n}.')
        writer = PdfWriter()
        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])
        target = Path(output_dir) / f'{stem}-p{start}-{end}.pdf'
        outputs.append(_atomic(target, lambda tmp, w=writer: _write_pdf(w, tmp)))
    return Result(outputs, n, f'Split into {len(outputs)} files')


def parse_page_spec(spec: str, n: int) -> list[int]:
    """'1,3-5,8' -> [1,3,4,5,8] (1-based, de-duplicated, order preserved)."""
    pages: list[int] = []
    for part in spec.replace(' ', '').split(','):
        if not part:
            continue
        if '-' in part:
            a, _, b = part.partition('-')
            try:
                lo, hi = int(a), int(b)
            except ValueError:
                raise ToolkitError(f'Invalid page range: "{part}"')
            if not (1 <= lo <= hi <= n):
                raise ToolkitError(f'Range "{part}" is outside 1-{n}.')
            pages.extend(range(lo, hi + 1))
        else:
            try:
                p = int(part)
            except ValueError:
                raise ToolkitError(f'Invalid page number: "{part}"')
            if not 1 <= p <= n:
                raise ToolkitError(f'Page {p} is outside 1-{n}.')
            pages.append(p)
    seen: dict[int, None] = {}
    for p in pages:
        seen.setdefault(p, None)
    return list(seen)


def organize_pdf(input: Path, output: Path, keep: list[int] | None = None,
                 rotations: dict[int, int] | None = None, password: str | None = None) -> Result:
    """keep: 1-based page order to keep (also reorders / deletes). rotations: {page: degrees}."""
    reader = open_reader(Path(input), password)
    n = len(reader.pages)
    order = keep if keep is not None else list(range(1, n + 1))
    if not order:
        raise ToolkitError('At least one page must be kept.')
    rotations = rotations or {}
    writer = PdfWriter()
    for p in order:
        if not 1 <= p <= n:
            raise ToolkitError(f'Page {p} is outside 1-{n}.')
        page = reader.pages[p - 1]
        deg = rotations.get(p, 0) % 360
        if deg:
            page = page.rotate(deg)
        writer.add_page(page)
    out = _atomic(output, lambda tmp: _write_pdf(writer, tmp))
    return Result([out], len(order), f'{len(order)} pages written (from {n})')


def images_to_pdf(images: list[Path], output: Path, dpi: int = 150) -> Result:
    """One image per page, in order. Alpha is flattened onto white; no network use."""
    from PIL import Image
    frames = []
    try:
        for item in images:
            p = Path(item)
            if p.suffix.lower() not in SUPPORTED_IMAGES:
                raise ToolkitError(f'"{p.name}" is not a supported image type.')
            try:
                im = Image.open(_fs(p))
                im.load()
            except (OSError, ValueError) as exc:
                raise ToolkitError(f'"{p.name}" could not be read as an image ({type(exc).__name__}).') from None
            if im.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', im.size, (255, 255, 255))
                rgba = im.convert('RGBA')
                background.paste(rgba, mask=rgba.split()[-1])
                im = background
            elif im.mode != 'RGB':
                im = im.convert('RGB')
            frames.append(im)
        if not frames:
            raise ToolkitError('No images selected.')

        def write(tmp):
            frames[0].save(_fs(tmp), 'PDF', save_all=True, append_images=frames[1:], resolution=float(dpi))
        out = _atomic(output, write)
    finally:
        for f in frames:
            f.close()
    return Result([out], len(frames), f'{len(frames)} image(s) combined into one PDF')


def pdf_to_images(input: Path, output_dir: Path, fmt: str = 'png', dpi: int = 150,
                  password: str | None = None, pages: list[int] | None = None) -> Result:
    import pypdfium2 as pdfium
    fmt = fmt.lower().lstrip('.')
    if fmt not in ('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'):
        raise ToolkitError(f'Unsupported image format: {fmt}')
    if not 36 <= dpi <= 600:
        raise ToolkitError('DPI must be between 36 and 600.')
    _require_openable(Path(input), password)
    try:
        doc = pdfium.PdfDocument(_fs(Path(input)), password=password or None)
    except pdfium.PdfiumError:
        raise ToolkitError(f'Could not open "{Path(input).name}": it may be damaged.') from None
    try:
        n = len(doc)
        stem = Path(input).stem
        want = pages or list(range(1, n + 1))
        width = len(str(n))
        scale = dpi / 72
        outputs = []
        save_fmt = 'JPEG' if fmt in ('jpg', 'jpeg') else fmt.upper()
        ext = 'jpg' if fmt in ('jpg', 'jpeg') else fmt
        for p in want:
            if not 1 <= p <= n:
                raise ToolkitError(f'Page {p} is outside 1-{n}.')
            bitmap = doc[p - 1].render(scale=scale)
            image = bitmap.to_pil()
            if save_fmt == 'JPEG' and image.mode != 'RGB':
                image = image.convert('RGB')
            target = Path(output_dir) / f'{stem}-p{str(p).zfill(width)}.{ext}'
            outputs.append(_atomic(target, lambda tmp, im=image: im.save(_fs(tmp), save_fmt)))
        return Result(outputs, len(outputs), f'{len(outputs)} page(s) exported as {ext.upper()} at {dpi} DPI')
    finally:
        doc.close()


def pdf_to_docx(input: Path, output: Path, password: str | None = None) -> Result:
    """Text-only draft (no exact layout). Scanned PDFs yield little or no text."""
    import pdfplumber
    from docx import Document

    _require_openable(Path(input), password)
    document = Document()
    empty = True
    with pdfplumber.open(_fs(Path(input)), password=password or '') as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ''
            if text.strip():
                empty = False
            for line in (text.splitlines() or ['']):
                document.add_paragraph(line)
            if i < n:
                document.add_page_break()
    out = _atomic(output, lambda tmp: document.save(_fs(tmp)))
    note = 'Text draft created' if not empty else 'No selectable text found (the PDF may be scanned images; OCR is needed).'
    return Result([out], n, note)


def pdf_to_xlsx(input: Path, output: Path, password: str | None = None) -> Result:
    """Extract text-based tables to a worksheet per table. Scanned PDFs yield nothing."""
    import pdfplumber
    from openpyxl import Workbook

    _require_openable(Path(input), password)
    wb = Workbook()
    wb.remove(wb.active)
    count = 0
    # Ruled tables first; fall back to whitespace-aligned detection (common in statements).
    text_settings = {'vertical_strategy': 'text', 'horizontal_strategy': 'text'}
    with pdfplumber.open(_fs(Path(input)), password=password or '') as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables() or []
            if not tables:
                tables = page.extract_tables(table_settings=text_settings) or []
            for t, table in enumerate(tables, 1):
                count += 1
                ws = wb.create_sheet(title=f'P{i}-T{t}'[:31])
                for row in table:
                    ws.append([_safe_cell(c) for c in row])
    if count == 0:
        wb.create_sheet(title='No tables found')
    out = _atomic(output, lambda tmp: wb.save(_fs(tmp)))
    note = f'{count} table(s) extracted' if count else 'No text-based tables found (the PDF may be scanned; OCR is needed).'
    return Result([out], count, note)


# Spreadsheet formula-injection guard, same rule as the unlock report.
_FORMULA = ('=', '+', '-', '@', '\t', '\r')


def _safe_cell(value):
    if value is None:
        return ''
    text = str(value)
    return "'" + text if text[:1] in _FORMULA else text


def _write_pdf(writer: PdfWriter, tmp: Path):
    with open(_fs(tmp), 'wb') as fh:
        writer.write(fh)


def page_count(input: Path, password: str | None = None) -> int:
    return len(open_reader(Path(input), password).pages)
