import json

from django.core.management.base import BaseCommand

from main.models import DiscountCardReport


class Command(BaseCommand):
    help = "DiscountCardReport va unga bog'langan tranzaksiyalarni cart.json fayliga yozadi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="cart.json",
            help="Chiqish fayli nomi (default: cart.json)",
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        reports = DiscountCardReport.objects.prefetch_related("transactions").all()

        result = []
        for report in reports:
            result.append({
                "uid1c": str(report.uid1c),
                "code": report.code,
                "fullName": report.full_name,
                "discountPercent": float(report.discount_percent),
                "periodFrom": report.period_from.isoformat() if report.period_from else None,
                "periodTo": report.period_to.isoformat() if report.period_to else None,
                "openingBalance": float(report.opening_balance),
                "totalIncome": float(report.total_income),
                "totalExpense": float(report.total_expense),
                "closingBalance": float(report.closing_balance),
                "transactions": [
                    {
                        "docPresentation": t.doc_presentation,
                        "docNumber": t.doc_number,
                        "docDate": t.doc_date.isoformat() if t.doc_date else None,
                        "openingBalance": float(t.opening_balance),
                        "income": float(t.income),
                        "expense": float(t.expense),
                        "closingBalance": float(t.closing_balance),
                        "rowNumber": t.row_number,
                    }
                    for t in report.transactions.all()
                ],
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Tugadi: {len(result)} ta report '{output_path}' fayliga yozildi")
        )