# reminders/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from firebase_admin.messaging import Message, Notification
from firebase_admin import messaging
from dateutil.relativedelta import relativedelta

from .models import SmartReminder, ReminderHistory, LearningSchedule

logger = logging.getLogger(__name__)


# ==========================================
# REMINDER DELIVERY TASKS
# ==========================================
@shared_task
def check_and_send_due_reminders():
    """
    Check for due reminders and send them.
    Run every 5-10 minutes via Celery Beat.
    """
    try:
        now = timezone.now()
        
        # Get all active reminders that are due
        due_reminders = SmartReminder.objects.filter(
            status='active',
            next_reminder_at__lte=now
        ).exclude(
            end_date__lt=now  # Skip if end_date has passed
        )[:100]  # Safety limit
        
        logger.info(f"Found {due_reminders.count()} due reminders to process")
        
        for reminder in due_reminders:
            send_reminder.delay(reminder.id)
        
        return {'processed': due_reminders.count()}
    
    except Exception as e:
        logger.error(f"Error checking due reminders: {str(e)}")
        return {'error': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_reminder(self, reminder_id: str):
    """
    Send a single reminder to the user.
    Includes retry logic for failed deliveries.
    """
    try:
        reminder = SmartReminder.objects.get(id=reminder_id)
        user = reminder.user
        
        # Check if user has FCM token
        if not hasattr(user, 'preferences') or not user.preferences.fcm_token:
            logger.warning(f"No FCM token for user {user.email}, skipping reminder {reminder_id}")
            return {'status': 'skipped', 'reason': 'no_fcm_token'}

        # Prepare notification
        title = f"📬 {reminder.title}"
        body = reminder.description[:200] if reminder.description else reminder.title[:200]
        
        try:
            # Send Firebase push notification
            message = Message(
                notification=Notification(title=title, body=body),
                token=user.preferences.fcm_token,
                data={
                    'reminder_id': str(reminder.id),
                    'type': 'reminder',
                    'reminder_type': reminder.reminder_type,
                },
            )
            
            response = messaging.send(message)
            logger.info(f"✓ Reminder sent to user {user.email}: {response}")
            
            # Record delivery history
            ReminderHistory.objects.create(
                reminder=reminder,
                status='sent',
                delivery_method='push',
                content_delivered={
                    'title': reminder.title,
                    'description': reminder.description,
                    'type': reminder.reminder_type,
                }
            )
            
            # Update reminder metrics
            reminder.delivery_count += 1
            reminder.last_delivered_at = timezone.now()
            
            # Calculate next reminder time based on recurrence
            reminder.next_reminder_at = calculate_next_reminder_time(reminder)
            
            # Mark as completed if one-time and delivered
            if reminder.recurrence_pattern == 'once':
                reminder.status = 'completed'
                reminder.end_date = timezone.now()
            
            reminder.save()

            return {'status': 'sent', 'user': user.email}
        
        except Exception as e:
            logger.error(f"FCM send failed for reminder {reminder_id}: {str(e)}")
            
            # Record failed delivery
            ReminderHistory.objects.create(
                reminder=reminder,
                status='failed',
                delivery_method='push'
            )
            
            # Retry
            raise self.retry(exc=e)
    
    except SmartReminder.DoesNotExist:
        logger.error(f"Reminder {reminder_id} not found")
        return {'error': 'not_found'}
    
    except Exception as e:
        logger.error(f"send_reminder error for {reminder_id}: {str(e)}")
        return {'error': str(e)}


def calculate_next_reminder_time(reminder: SmartReminder) -> timezone.datetime:
    """
    Calculate the next reminder time based on recurrence pattern.
    """
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    
    now = timezone.now()
    last_sent = reminder.last_delivered_at or reminder.first_reminder_at
    
    if reminder.recurrence_pattern == 'once':
        return now + timedelta(days=365)  # Far future (won't trigger again)
    
    elif reminder.recurrence_pattern == 'daily':
        return last_sent + timedelta(days=1)
    
    elif reminder.recurrence_pattern == 'weekly':
        return last_sent + timedelta(weeks=1)
    
    elif reminder.recurrence_pattern == 'biweekly':
        return last_sent + timedelta(weeks=2)
    
    elif reminder.recurrence_pattern == 'monthly':
        return last_sent + relativedelta(months=1)
    
    elif reminder.recurrence_pattern == 'yearly':
        return last_sent + relativedelta(years=1)
    
    elif reminder.recurrence_pattern == 'custom':
        # Custom schedule defined in custom_schedule field
        schedule = reminder.custom_schedule
        if schedule and 'next_time' in schedule:
            try:
                from dateutil.parser import isoparse
                return isoparse(schedule['next_time'])
            except:
                pass
        return last_sent + timedelta(days=1)
    
    return last_sent + timedelta(days=1)


# ==========================================
# LEARNING SCHEDULE TASKS
# ==========================================
@shared_task
def check_learning_sessions():
    """
    Check for due learning sessions and send them.
    Run every hour via Celery Beat.
    """
    try:
        now = timezone.now()
        
        # Get all active learning schedules
        schedules = LearningSchedule.objects.filter(
            status='active'
        )
        
        sent_count = 0
        
        for schedule in schedules:
            sessions = schedule.sessions
            
            for session in sessions:
                if session.get('completed'):
                    continue
                
                # Check if session is due
                try:
                    from dateutil.parser import isoparse
                    scheduled_for = isoparse(session['scheduled_for'])
                    
                    if scheduled_for <= now:
                        send_learning_session.delay(
                            schedule.id,
                            session['session_number']
                        )
                        sent_count += 1
                except:
                    pass
        
        logger.info(f"Sent {sent_count} learning session reminders")
        return {'sent': sent_count}
    
    except Exception as e:
        logger.error(f"Error checking learning sessions: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_learning_session(schedule_id: str, session_number: int):
    """
    Send a learning session reminder to the user.
    """
    try:
        schedule = LearningSchedule.objects.get(id=schedule_id)
        user = schedule.user
        
        if not hasattr(user, 'preferences') or not user.preferences.fcm_token:
            logger.warning(f"No FCM token for user {user.email}")
            return
        
        # Prepare notification
        title = f"📚 Learning: {schedule.title}"
        body = f"Session {session_number} of {schedule.total_sessions}"
        
        try:
            message = Message(
                notification=Notification(title=title, body=body),
                token=user.preferences.fcm_token,
                data={
                    'schedule_id': str(schedule.id),
                    'type': 'learning_session',
                    'session_number': str(session_number),
                },
            )
            
            response = messaging.send(message)
            logger.info(f"✓ Learning session sent to user {user.email}: {response}")
        
        except Exception as e:
            logger.error(f"Failed to send learning session: {str(e)}")
    
    except LearningSchedule.DoesNotExist:
        logger.error(f"Learning schedule {schedule_id} not found")
    
    except Exception as e:
        logger.error(f"send_learning_session error: {str(e)}")


# ==========================================
# BIRTHDAY REMINDER TASKS
# ==========================================
@shared_task
def check_upcoming_birthdays():
    """
    Check for upcoming birthdays (1 week and 1 day before).
    Run daily via Celery Beat.
    """
    try:
        now = timezone.now()
        week_from_now = now + timedelta(days=7)
        
        # Get birthday reminders due within a week
        upcoming_birthdays = SmartReminder.objects.filter(
            reminder_type='personal',
            status='active',
            next_reminder_at__gte=now,
            next_reminder_at__lte=week_from_now
        )
        
        logger.info(f"Found {upcoming_birthdays.count()} upcoming birthdays")
        
        for reminder in upcoming_birthdays:
            send_reminder.delay(reminder.id)
        
        return {'processed': upcoming_birthdays.count()}
    
    except Exception as e:
        logger.error(f"Error checking upcoming birthdays: {str(e)}")
        return {'error': str(e)}


# ==========================================
# CLEANUP AND MAINTENANCE TASKS
# ==========================================
@shared_task
def cleanup_old_completed_reminders():
    """
    Archive completed reminders older than 90 days.
    Run weekly via Celery Beat.
    """
    try:
        cutoff = timezone.now() - timedelta(days=90)
        
        archived = SmartReminder.objects.filter(
            status='completed',
            last_delivered_at__lt=cutoff
        ).update(status='archived')
        
        logger.info(f"Archived {archived} completed reminders")
        return {'archived': archived}
    
    except Exception as e:
        logger.error(f"Error cleaning up reminders: {str(e)}")
        return {'error': str(e)}


from datetime import timedelta
