import pandas as pd
import os
import logging
from typing import Dict, Optional, Any
from models.schemas import SchemaConfig

logger = logging.getLogger(__name__)


class DataIngestionException(Exception):
    """Custom exception for data ingestion errors."""
    pass


class ExcelDataLoader:
    """
    A reusable service class to handle ingestion of Excel files dynamically.
    Handles column name normalization and header-row offsets for real-world
    Excel files that don't match the canonical schema out of the box.
    """

    # Maps raw Excel column names → canonical schema column names per file type
    COLUMN_MAPS: Dict[str, Dict[str, str]] = {
        'sales': {
            'Project: Project Name':   'Project',
            'Cluster':                 'Tower',   # Cluster acts as Tower grouping in this dataset
            'Unit Number':             'Unit',
            'SAP Customer Code':       'Customer Code',
            'Total Agreement Amount':  'Booking Value',
            'Sales Stage':             'Status',
        },
        'collections': {
            'Project Name':       'Project',
            'SAP Customer Code':  'Customer Code',
            'Milestone Linked':   'Milestone',
            'Demand Raised Date': 'Demand Raised',
            'Demand Amount':      'Demand Raised',
            'Days Overdue':       'Overdue',
            'Amount Collected':   'Amount Collected',
            'Due Date':           'Due Date',
        },
        'construction': {
            'Activity':          'Milestone',
            'Planned Start':     'Planned Date',
            'Start Date':        'Planned Date',
            'Actual Progress %': 'Actual Progress',
            'Completion %':      'Actual Progress',
            'Planned Cost INR':  'Cost Impact',
            'Remarks':           'Delay Reason',
        },
    }

    # Header row index (0-based) where actual column labels live in each file type
    HEADER_ROWS: Dict[str, int] = {
        'sales':        0,
        'construction': 1,
        'collections':  3,  # Row 0=title, 1=metadata, 2=blank, 3=column headers
        'aop':          0,
    }

    # Data sheet names to prefer (case-insensitive substring match)
    PREFERRED_SHEETS: Dict[str, str] = {
        'sales':        'sales dump',
        'construction': 'r5b - daily targets',
        'collections':  'collections tracker',
        'aop':          'summary targets',
    }

    @classmethod
    def _pick_sheet(cls, sheet_names: list, file_type: str) -> str:
        """Pick the best data sheet, skipping README / Lookup tabs."""
        preferred = cls.PREFERRED_SHEETS.get(file_type, '')
        for sn in sheet_names:
            if preferred and preferred in sn.lower():
                return sn
        # Fallback: first non-README, non-Lookup sheet
        for sn in sheet_names:
            if 'readme' not in sn.lower() and 'lookup' not in sn.lower():
                return sn
        return sheet_names[0]

    @classmethod
    def load_excel_file(cls, file_path_or_buffer: Any, file_type: str) -> Optional[pd.DataFrame]:
        """
        Reads an Excel file, applies header-row offset and column renaming,
        then validates against the schema.

        Args:
            file_path_or_buffer: A file path string OR a Streamlit UploadedFile (BytesIO).
            file_type: One of 'sales', 'construction', 'collections', 'aop'.

        Returns:
            Cleaned pd.DataFrame.

        Raises:
            DataIngestionException on any failure.
        """
        logger.info(f"Attempting to load {file_type} data...")

        def _seek(buf):
            """Reset buffer if seekable (e.g. Streamlit BytesIO objects)."""
            if hasattr(buf, 'seek'):
                buf.seek(0)

        try:
            # ── Step 1: Discover sheets ───────────────────────────────────────
            _seek(file_path_or_buffer)
            excel_data = pd.read_excel(file_path_or_buffer, sheet_name=None, engine='openpyxl')
            if not excel_data:
                raise DataIngestionException(f"The {file_type} file contains no worksheets.")

            sheet_names = list(excel_data.keys())
            target_sheet = cls._pick_sheet(sheet_names, file_type)
            logger.info(f"[{file_type}] Using sheet '{target_sheet}'. All sheets: {sheet_names}")

            # ── Step 2: Read sheet with correct header row ────────────────────
            # Must seek(0) because step 1 consumed the buffer.
            _seek(file_path_or_buffer)
            header_row = cls.HEADER_ROWS.get(file_type, 0)
            df = pd.read_excel(
                file_path_or_buffer,
                sheet_name=target_sheet,
                header=header_row,
                engine='openpyxl'
            )

            # ── Step 3: Normalise column names ────────────────────────────────
            df.columns = [str(col).strip() for col in df.columns]

            # ── Step 4: Rename raw columns → canonical schema names ───────────
            col_map = cls.COLUMN_MAPS.get(file_type, {})
            if col_map:
                df.rename(columns=col_map, inplace=True)
                logger.info(f"[{file_type}] Columns after rename: {list(df.columns)}")

            # ── Step 5: File-type specific transformations ────────────────────
            if file_type == 'construction' and 'Project' not in df.columns:
                # Single-project dataset — inject project name
                df['Project'] = 'Aster Grove Residences'

            if file_type == 'aop':
                # AOP file has a wide "Summary Targets" sheet: Month | Target1 | Target2 ...
                # We melt it into long form: Month | Target Type | Value
                _seek(file_path_or_buffer)
                df_raw = pd.read_excel(
                    file_path_or_buffer,
                    sheet_name='Summary Targets',
                    header=0,
                    engine='openpyxl'
                )
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                month_col = df_raw.columns[0]
                value_cols = df_raw.columns[1:].tolist()
                df_raw.rename(columns={month_col: 'Month'}, inplace=True)
                # Keep only rows that have valid date-like Month values
                df_raw = df_raw[pd.to_datetime(df_raw['Month'], errors='coerce').notna()]
                df = pd.melt(
                    df_raw,
                    id_vars=['Month'],
                    value_vars=value_cols,
                    var_name='Target Type',
                    value_name='Value'
                )
                logger.info(f"[aop] Melted AOP shape: {df.shape}")

            # ── Step 6: Schema validation ─────────────────────────────────────
            schema = SchemaConfig.SCHEMAS.get(file_type.lower())
            if not schema:
                logger.warning(f"No schema defined for '{file_type}'. Skipping validation.")
                df.dropna(how='all', inplace=True)
                return df

            required_cols = schema.required_columns
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                error_msg = (
                    f"Validation failed for {file_type}. "
                    f"Missing required columns: {missing_cols}. "
                    f"Found columns: {list(df.columns)}"
                )
                logger.error(error_msg)
                raise DataIngestionException(error_msg)

            # ── Step 7: Drop fully empty rows/columns ─────────────────────────
            df.dropna(how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)

            logger.info(f"[{file_type}] Successfully loaded. Shape: {df.shape}")
            return df

        except DataIngestionException:
            raise
        except FileNotFoundError:
            raise DataIngestionException("File not found. Please check the file path.")
        except ValueError as e:
            raise DataIngestionException(f"Value error parsing {file_type} file: {e}")
        except Exception as e:
            raise DataIngestionException(f"Unexpected error reading {file_type} file: {e}")


class RealEstateDataPipeline:
    """
    Manager class to handle the ingestion of all four required datasets.
    """
    def __init__(self):
        self.loader = ExcelDataLoader()
        self.data: Dict[str, pd.DataFrame] = {}

    def ingest_all(self, sales_file, construction_file, collections_file, aop_file) -> bool:
        """
        Ingest all four datasets.  Arguments can be file paths or Streamlit UploadedFile objects.
        """
        try:
            self.data['sales']        = self.loader.load_excel_file(sales_file,        'sales')
            self.data['construction'] = self.loader.load_excel_file(construction_file, 'construction')
            self.data['collections']  = self.loader.load_excel_file(collections_file,  'collections')
            self.data['aop']          = self.loader.load_excel_file(aop_file,          'aop')
            logger.info("All datasets successfully ingested.")
            return True
        except DataIngestionException as e:
            logger.error(f"Pipeline ingestion failed: {e}")
            raise e
