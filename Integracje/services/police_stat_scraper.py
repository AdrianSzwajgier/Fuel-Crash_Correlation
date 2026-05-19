import requests

from bs4 import BeautifulSoup
from django.conf import settings
from pathlib import Path


class PoliceStatScraper:
    BASE_URL = "https://statystyka.policja.pl"
    REPORTS_URL = f"{BASE_URL}/st/ruch-drogowy/76562,wypadki-drogowe-raporty-roczne.html"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        settings.configure()

    def get_page(self, url: str) -> BeautifulSoup:
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def get_reports_page(self) -> BeautifulSoup:
        return self.get_page(self.REPORTS_URL)

    def get_pdf_urls(self, year_from: int, year_to: int) -> list[dict]:
        soup = self.get_reports_page()
        attachments = soup.find("div", class_="zalaczniki")
        links = attachments.find_all("a", href=lambda h: h and h.endswith(".pdf"))

        pdf_urls = []
        for link in links:
            href = link["href"]
            year = next(
                (int(w) for w in link.text.split() if w.isdigit() and len(w) == 4),
                None
            )
            if year and year_from <= year <= year_to:
                pdf_urls.append({
                    "year": year,
                    "url": f"{self.BASE_URL}{href}",
                    "label": link.text.strip(),
                })

        return sorted(pdf_urls, key=lambda x: x["year"])

    def download_pdfs(self, pdf_list: list[dict], save_dir: Path) -> list[dict]:
        save_dir.mkdir(parents=True, exist_ok=True)

        download_results = []
        for entry in pdf_list:
            filename = f"accident_report_{entry['year']}.pdf"
            filepath = save_dir / filename

            if filepath.exists():
                print(f"[SKIP] {filename} already exists.")
                download_results.append({**entry, "filepath": filepath, "downloaded": False})
                continue

            response = self.session.get(entry["url"], timeout=30)
            response.raise_for_status()

            filepath.write_bytes(response.content)
            print(f"[OK]   {filename} downloaded.")
            download_results.append({**entry, "filepath": filepath, "downloaded": True})

        return download_results


def main():
    year_from, year_to = 2010, 2025
    save_dir = Path(__file__).parent.parent / "media" / "police-reports"

    scraper = PoliceStatScraper()

    print(f"[INFO] Fetching PDF URLs for years {year_from}–{year_to}...")
    pdf_list = scraper.get_pdf_urls(year_from, year_to)
    print(f"[INFO] Found {len(pdf_list)} reports.")

    print("[INFO] Starting download...")
    results = scraper.download_pdfs(pdf_list, save_dir)

    downloaded = sum(1 for r in results if r["downloaded"])
    skipped = len(results) - downloaded
    print(f"[DONE] Downloaded: {downloaded}, skipped: {skipped}.")


main()
