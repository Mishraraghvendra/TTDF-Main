from django.core.management.base import BaseCommand
from notifications.kafka_consumer import run_consumer

class Command(BaseCommand):
    help = 'Run Kafka consumer for notifications'

    def handle(self, *args, **options):
        self.stdout.write("Starting Kafka consumer...")
        run_consumer()
