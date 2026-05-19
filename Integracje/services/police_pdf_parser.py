import pdfplumber
import re

from pathlib import Path

MONTHS_PL = {
    "styczeń": 1, "luty": 2, "marzec": 3, "kwiecień": 4,
    "maj": 5, "czerwiec": 6, "lipiec": 7, "sierpień": 8,
    "wrzesień": 9, "październik": 10, "listopad": 11, "grudzień": 12
}

TABLE_TITLE_PATTERN = re.compile(r"wypadki drogowe i ich skutki\s+wg\.?\s+miesięcy|według miesięcy", re.IGNORECASE)


class PolicePDFParser:
    def parse_pdf(self, filepath: Path, year: int) -> list[dict]:
        records = []

        with pdfplumber.open(filepath) as pdf:
            target_page = self._find_table_page(pdf)
            if target_page is None:
                print(f"[WARN] Table not found in {filepath.name}")
                return records

            table = target_page.extract_table()
            if not table:
                print(f"[WARN] Could not extract table from {filepath.name}")
                return records

            print(f"[INFO] Parsing {filepath.name}, page {target_page.page_number}...")
            records = self._parse_table_rows(table, year)

        return records

    def _find_table_page(self, pdf: pdfplumber.PDF):
        for page in pdf.pages[12:16]:
            if TABLE_TITLE_PATTERN.search(page.extract_text() or ""):
                return page
        return None

    def _parse_table_rows(self, table: list, year: int) -> list[dict]:
        records = []

        for row in table:
            if not row or not row[0]:
                continue

            month_name = row[0].strip().lower()
            month_num = MONTHS_PL.get(month_name)
            if month_num is None:
                continue

            try:
                records.append({
                    "year": year,
                    "month": month_num,
                    "accidents_total": self._parse_int(row[1]),
                    "accidents_pct": self._parse_float(row[2]),
                    "fatalities_total": self._parse_int(row[3]),
                    "fatalities_pct": self._parse_float(row[4]),
                    "injured_total": self._parse_int(row[5]),
                    "injured_pct": self._parse_float(row[6]),
                })
            except (IndexError, ValueError) as e:
                print(f"[WARN] Skipping row {row}: {e}")

        return records

    @staticmethod
    def _parse_int(value: str) -> int:
        return int(re.sub(r"\s+", "", value or "").replace(",", ""))

    @staticmethod
    def _parse_float(value: str) -> float:
        return float((value or "").strip().replace(",", "."))


def main():
    save_dir = Path(__file__).parent.parent / "media" / "police-reports"
    pdf_files = list(save_dir.glob("*.pdf"))

    if not pdf_files:
        print("[WARN] No PDF files found in directory.")
        return

    print(f"[INFO] Found {len(pdf_files)} PDF files. Parsing...")
    parser = PolicePDFParser()
    all_records = []

    for filepath in sorted(pdf_files):
        year_match = re.search(r"(\d{4})", filepath.stem)
        if not year_match:
            print(f"[WARN] Could not extract year from filename: {filepath.name}, skipping.")
            continue

        year = int(year_match.group(1))
        records = parser.parse_pdf(filepath, year)
        all_records.extend(records)
        print(f"[OK]   {year}: {len(records)} rows parsed.")

    print(f"[DONE] Total records: {len(all_records)}")
    print(all_records[:3])


main()
