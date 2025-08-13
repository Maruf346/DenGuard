import csv
from django.core.management.base import BaseCommand
from planner.models import DengueStat

class Command(BaseCommand):
    help = "Import Dengue statistics from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']

        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                DengueStat.objects.create(
                    location_name=row['location_name'],
                    longitude=float(row['longitude']),
                    latitude=float(row['latitude']),
                    total=int(row['total']),
                    dead=int(row['dead']),
                    male=int(row['male']),
                    female=int(row['female']),
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully imported {count} records."))
