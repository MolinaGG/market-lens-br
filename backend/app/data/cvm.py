"""CVM IPE filings with document identity, revision state, and company mapping."""

import csv
import hashlib
import io
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time, timezone


CVM_CATALOG_URL = "https://dados.cvm.gov.br/dataset/cia_aberta-doc-ipe"
CVM_ZIP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{year}.zip"
# Codes checked against the 2026 official IPE extract and the original ticker universe.
CVM_CODES = {"PETR4": "9512", "VALE3": "4170", "ITUB4": "19348", "BBDC4": "906", "WEGE3": "5410", "ABEV3": "23264"}
CODE_TO_TICKER = {code: ticker for ticker, code in CVM_CODES.items()}


@dataclass(frozen=True)
class CompanyFiling:
    filing_id: str
    ticker: str
    company_code: str
    category: str
    title: str
    status: str
    published_at: datetime
    publication_time_known: bool
    reference_date: date
    protocol: str
    version: int
    source_url: str
    source_dataset_url: str
    fetched_at: datetime
    source_rights: str = "ODbL"

    @property
    def impact_eligible(self) -> bool:
        return self.status != "cancelled"


def normalize_subject(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))


def parse_cvm_ipe(zip_bytes: bytes, fetched_at: datetime) -> list[CompanyFiling]:
    selected: dict[tuple[str, str, str, str], CompanyFiling] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not members:
            raise ValueError("CVM archive has no CSV")
        for member in members:
            with archive.open(member) as stream:
                reader = csv.DictReader(io.TextIOWrapper(stream, encoding="cp1252", newline=""), delimiter=";")
                for row in reader:
                    code = (row.get("Codigo_CVM") or "").strip()
                    ticker = CODE_TO_TICKER.get(code)
                    category = (row.get("Categoria") or "").strip()
                    if ticker is None or category not in {"Fato Relevante", "Comunicado ao Mercado"}:
                        continue
                    subject = (row.get("Assunto") or "").strip() or category
                    delivery = date.fromisoformat(row["Data_Entrega"])
                    reference = date.fromisoformat(row["Data_Referencia"])
                    protocol = (row.get("Protocolo_Entrega") or "").strip()
                    url = (row.get("Link_Download") or "").strip()
                    if not protocol or not url.startswith("https://www.rad.cvm.gov.br/"):
                        continue
                    version = int(row.get("Versao") or "1")
                    presentation = (row.get("Tipo_Apresentacao") or "").upper()
                    plain_subject = normalize_subject(subject)
                    status = "cancelled" if any(term in plain_subject for term in ("cancelamento", "cancelado", "cancelada")) else "refiled" if presentation.startswith(("RE", "RC")) or version > 1 else "active"
                    filing = CompanyFiling(
                        f"CVM:{code}:{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}", ticker, code, category,
                        f"{category}: {subject}", status,
                        datetime.combine(delivery, time.min, timezone.utc), False,
                        reference, protocol, version, url, CVM_CATALOG_URL, fetched_at,
                    )
                    key = (code, category, reference.isoformat(), plain_subject)
                    prior = selected.get(key)
                    if prior is None or (filing.version, filing.published_at) > (prior.version, prior.published_at):
                        selected[key] = filing
    return sorted(selected.values(), key=lambda filing: filing.published_at, reverse=True)
