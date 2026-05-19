from django.db import transaction
from traffic.models import AccidentRecord

class SyncDatabase:
    @staticmethod
    @transaction.atomic
    def save_records(records: list[dict]) -> dict:
        created_count = 0
        skipped_count = 0
        print(f"{records = }")
        for record in records:
            _, created = AccidentRecord.objects.get_or_create(
                year=record["year"],
                month=record["month"],
                defaults={
                    "accidents_total": record["accidents_total"],
                    "accidents_pct": record["accidents_pct"],
                    "fatalities_total": record["fatalities_total"],
                    "fatalities_pct": record["fatalities_pct"],
                    "injured_total": record["injured_total"],
                    "injured_pct": record["injured_pct"],
                }
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        return {"created": created_count, "skipped": skipped_count}
