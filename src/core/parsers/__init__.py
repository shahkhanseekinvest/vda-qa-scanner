"""File-type specific parsers for text extraction and searching."""

from .pdf import search_in_pdf
from .word import search_in_word_doc
from .excel import search_in_excel
from .csv_parser import search_in_csv
from .powerpoint import search_in_powerpoint
from .text import search_in_text_file

__all__ = [
    "search_in_pdf",
    "search_in_word_doc",
    "search_in_excel",
    "search_in_csv",
    "search_in_powerpoint",
    "search_in_text_file",
]
