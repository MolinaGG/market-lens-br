import json
from datetime import datetime, time, timezone

from app.data.models import MarketEvent


COMUNICADOS_URL = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=100"


def parse_comunicados(data: bytes, fetched_at: datetime) -> list[MarketEvent]:
    payload = json.loads(data)
    rows = payload["conteudo"]
    if not isinstance(rows, list):
        raise ValueError("Copom response must contain a list")
    events = []
    for row in rows:
        meeting = int(row["nro_reuniao"])
        publication_date = datetime.strptime(row["dataReferencia"], "%Y-%m-%d").date()
        events.append(
            MarketEvent(
                f"COPOM:{meeting}",
                "copom",
                row["titulo"],
                datetime.combine(publication_date, time.min, timezone.utc),
                False,
                f"https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao={meeting}",
                fetched_at,
            )
        )
    return events
