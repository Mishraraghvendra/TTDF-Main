import json
import logging
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()

KAFKA_TOPIC = 'user_events'
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']

def process_message(message):
    try:
        data = json.loads(message.value.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        return

    event_id = data.get('event_id')
    user_id = data.get('user_id')
    message_text = data.get('message')
    notification_type = data.get('notification_type', 'general')

    if not (event_id and user_id and message_text):
        logger.error("Missing required fields in message: %s", data)
        return

    if Notification.objects.filter(event_id=event_id).exists():
        logger.info("Duplicate event_id %s, skipping message", event_id)
        return
    
    try:
        recipient = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("User with id %s does not exist", user_id)
        return

    try:
        Notification.objects.create(
            event_id=event_id,
            recipient=recipient,
            message=message_text,
            notification_type=notification_type
        )
        logger.info("Notification created for user %s, event_id %s", recipient.username, event_id)
    except Exception as e:
        logger.exception("Database error creating notification for event_id %s: %s", event_id, e)



def run_consumer():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=False,  # Disable auto commit for manual control.
        group_id='notification_service_group'
    )
    logger.info("Kafka consumer started for topic: %s", KAFKA_TOPIC)
    try:
        while True:
            try:
                # Poll messages in batches with a timeout (e.g., 5 seconds) and limit to 10 records per batch.
                msg_pack = consumer.poll(timeout_ms=5000, max_records=10)
                if not msg_pack:
                    continue

                for tp, messages in msg_pack.items():
                    for message in messages:
                        process_message(message)
                # Commit offsets after processing the batch successfully.
                consumer.commit()
            except KafkaError as ke:
                logger.error("Kafka error encountered: %s", ke)
                time.sleep(5)  # Back off before retrying.
            except Exception as e:
                logger.exception("Unexpected error during message processing: %s", e)
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        consumer.close()
