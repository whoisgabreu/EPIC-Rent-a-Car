from django.core.management.base import BaseCommand
from dashboard.utils.importer import import_turo_csv
import os

class Command(BaseCommand):
    help = 'Import data from a Turo CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return

        self.stdout.write(f'Importing {csv_file}...')
        try:
            count = import_turo_csv(csv_file)
            self.stdout.write(self.style.SUCCESS(f'Success! {count} records processed.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during import: {str(e)}'))
            import traceback
            traceback.print_exc()
