from django.core.management.base import BaseCommand
from dashboard.utils.importer import import_turo_csv
import os

class Command(BaseCommand):
    help = 'Importa dados de um arquivo CSV da Turo'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Caminho para o arquivo CSV')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {csv_file}'))
            return

        self.stdout.write(f'Importando {csv_file}...')
        try:
            count = import_turo_csv(csv_file)
            self.stdout.write(self.style.SUCCESS(f'Sucesso! {count} registros processados.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro durante a importação: {str(e)}'))
            import traceback
            traceback.print_exc()
