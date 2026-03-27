"""
Notification System
Advanced Integration & Automation (Priority 5)

Comprehensive notification and alerting system:
- Multi-channel notification delivery
- Alert escalation and routing
- Notification templates and formatting
- Delivery confirmation and retry logic
- Integration with external systems
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class NotificationChannel(Enum):
    EMAIL = "email"
    CONSOLE = "console"
    FILE = "file"
    WEBHOOK = "webhook"

class NotificationPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class NotificationTemplate:
    """Template for notifications."""
    name: str
    subject_template: str
    body_template: str
    channels: List[NotificationChannel]
    priority: NotificationPriority

@dataclass
class NotificationMessage:
    """Represents a notification message."""
    id: str
    template_name: str
    recipient: str
    channel: NotificationChannel
    priority: NotificationPriority
    subject: str
    body: str
    context: Dict[str, Any]
    created_at: str
    delivery_attempts: int = 0
    delivered_at: Optional[str] = None
    error_message: Optional[str] = None

class NotificationSystem:
    """Advanced notification system for Parts Agent."""

    def __init__(self):
        """Initialize the notification system."""
        # Notification configuration
        self.config = {
            'email': {
                'smtp_server': 'localhost',
                'smtp_port': 587,
                'use_tls': True,
                'username': '',
                'password': '',
                'from_address': 'parts-agent@localhost'
            },
            'file': {
                'log_directory': 'logs',
                'log_filename': 'notifications.log'
            },
            'webhook': {
                'default_timeout': 30,
                'retry_attempts': 3
            },
            'delivery': {
                'max_retry_attempts': 3,
                'retry_delay_minutes': [5, 15, 60],  # Exponential backoff
                'batch_size': 10,
                'delivery_timeout': 300  # 5 minutes
            }
        }

        # Message queues
        self.pending_messages = {}  # Dict[str, NotificationMessage]
        self.sent_messages = {}  # Dict[str, NotificationMessage] (recent history)
        self.failed_messages = {}  # Dict[str, NotificationMessage]

        # Templates
        self.templates = self._initialize_templates()

        # Recipients
        self.recipients = {
            'administrators': ['admin@localhost'],
            'operators': ['operator@localhost'],
            'alerts': ['alerts@localhost']
        }

        # Channel handlers
        self.channel_handlers = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.CONSOLE: self._send_console,
            NotificationChannel.FILE: self._send_file,
            NotificationChannel.WEBHOOK: self._send_webhook
        }

        # Delivery thread
        self.delivery_thread = None
        self.delivery_active = False
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_messages': 0,
            'delivered_messages': 0,
            'failed_messages': 0,
            'messages_by_channel': {channel.value: 0 for channel in NotificationChannel},
            'messages_by_priority': {priority.value: 0 for priority in NotificationPriority},
            'start_time': datetime.now().isoformat()
        }

        # Ensure log directory exists
        log_dir = Path(self.config['file']['log_directory'])
        log_dir.mkdir(exist_ok=True)

        print("[NOTIFICATION_SYSTEM] Initialized with multi-channel delivery")

    def start_delivery_service(self):
        """Start the notification delivery service."""
        with self.lock:
            if self.delivery_active:
                print("Notification delivery service is already running")
                return

            self.delivery_active = True
            self.delivery_thread = threading.Thread(target=self._delivery_loop, daemon=True)
            self.delivery_thread.start()

            print("[NOTIFICATION_SYSTEM] Delivery service started")

    def stop_delivery_service(self):
        """Stop the notification delivery service."""
        with self.lock:
            if not self.delivery_active:
                return

            self.delivery_active = False

            if self.delivery_thread and self.delivery_thread.is_alive():
                self.delivery_thread.join(timeout=10)

            print("[NOTIFICATION_SYSTEM] Delivery service stopped")

    def send_notification(self, template_name: str, recipient: str, context: Dict[str, Any],
                         channels: Optional[List[NotificationChannel]] = None,
                         priority: Optional[NotificationPriority] = None) -> List[str]:
        """Send a notification using a template."""
        try:
            template = self.templates.get(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")

            # Use template channels and priority if not specified
            channels = channels or template.channels
            priority = priority or template.priority

            # Render template
            subject = self._render_template(template.subject_template, context)
            body = self._render_template(template.body_template, context)

            # Create messages for each channel
            message_ids = []
            for channel in channels:
                message_id = f"msg_{int(time.time() * 1000)}_{channel.value}"

                message = NotificationMessage(
                    id=message_id,
                    template_name=template_name,
                    recipient=recipient,
                    channel=channel,
                    priority=priority,
                    subject=subject,
                    body=body,
                    context=context.copy(),
                    created_at=datetime.now().isoformat()
                )

                # Add to pending queue
                with self.lock:
                    self.pending_messages[message_id] = message
                    self.stats['total_messages'] += 1
                    self.stats['messages_by_channel'][channel.value] += 1
                    self.stats['messages_by_priority'][priority.value] += 1

                message_ids.append(message_id)

            print(f"[NOTIFICATION_SYSTEM] Queued {len(message_ids)} messages for delivery")
            return message_ids

        except Exception as e:
            print(f"[NOTIFICATION_SYSTEM] Error sending notification: {e}")
            return []

    def send_alert(self, severity: str, component: str, message: str, details: Dict = None):
        """Send an alert notification."""
        context = {
            'severity': severity.upper(),
            'component': component,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Determine priority and recipients based on severity
        if severity.lower() == 'critical':
            priority = NotificationPriority.URGENT
            recipients = self.recipients['administrators'] + self.recipients['alerts']
        elif severity.lower() == 'warning':
            priority = NotificationPriority.HIGH
            recipients = self.recipients['operators'] + self.recipients['alerts']
        else:
            priority = NotificationPriority.NORMAL
            recipients = self.recipients['alerts']

        # Send to all recipients
        for recipient in recipients:
            self.send_notification('alert', recipient, context, priority=priority)

    def send_status_update(self, system: str, status: str, metrics: Dict = None):
        """Send a system status update."""
        context = {
            'system': system,
            'status': status,
            'metrics': metrics or {},
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Send to operators
        for recipient in self.recipients['operators']:
            self.send_notification('status_update', recipient, context)

    def send_processing_summary(self, summary: Dict):
        """Send a processing summary notification."""
        context = {
            'summary': summary,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Send to administrators and operators
        recipients = self.recipients['administrators'] + self.recipients['operators']
        for recipient in recipients:
            self.send_notification('processing_summary', recipient, context)

    def get_message_status(self, message_id: str) -> Optional[Dict]:
        """Get the status of a specific message."""
        with self.lock:
            # Check pending messages
            if message_id in self.pending_messages:
                message = self.pending_messages[message_id]
                return {
                    'status': 'pending',
                    'message': asdict(message),
                    'delivery_attempts': message.delivery_attempts
                }

            # Check sent messages
            if message_id in self.sent_messages:
                message = self.sent_messages[message_id]
                return {
                    'status': 'delivered',
                    'message': asdict(message),
                    'delivered_at': message.delivered_at
                }

            # Check failed messages
            if message_id in self.failed_messages:
                message = self.failed_messages[message_id]
                return {
                    'status': 'failed',
                    'message': asdict(message),
                    'error': message.error_message
                }

            return None

    def get_delivery_stats(self) -> Dict:
        """Get notification delivery statistics."""
        with self.lock:
            return {
                'delivery_service_active': self.delivery_active,
                'pending_count': len(self.pending_messages),
                'sent_count': len(self.sent_messages),
                'failed_count': len(self.failed_messages),
                'statistics': self.stats.copy(),
                'success_rate': (self.stats['delivered_messages'] /
                               max(1, self.stats['total_messages'])) if self.stats['total_messages'] > 0 else 0
            }

    def _initialize_templates(self) -> Dict[str, NotificationTemplate]:
        """Initialize notification templates."""
        templates = {}

        # Alert template
        templates['alert'] = NotificationTemplate(
            name='alert',
            subject_template='[{severity}] Parts Agent Alert: {component}',
            body_template='''
Parts Agent Alert

Severity: {severity}
Component: {component}
Message: {message}
Timestamp: {timestamp}

Details:
{details}

Please investigate and take appropriate action.
            '''.strip(),
            channels=[NotificationChannel.EMAIL, NotificationChannel.CONSOLE, NotificationChannel.FILE],
            priority=NotificationPriority.HIGH
        )

        # Status update template
        templates['status_update'] = NotificationTemplate(
            name='status_update',
            subject_template='Parts Agent Status: {system} - {status}',
            body_template='''
System Status Update

System: {system}
Status: {status}
Timestamp: {timestamp}

Metrics:
{metrics}
            '''.strip(),
            channels=[NotificationChannel.FILE, NotificationChannel.CONSOLE],
            priority=NotificationPriority.NORMAL
        )

        # Processing summary template
        templates['processing_summary'] = NotificationTemplate(
            name='processing_summary',
            subject_template='Parts Agent Processing Summary',
            body_template='''
Daily Processing Summary

Summary:
{summary}

Generated: {timestamp}

This is an automated summary of Parts Agent processing activities.
            '''.strip(),
            channels=[NotificationChannel.EMAIL, NotificationChannel.FILE],
            priority=NotificationPriority.NORMAL
        )

        # System maintenance template
        templates['maintenance'] = NotificationTemplate(
            name='maintenance',
            subject_template='Parts Agent Maintenance: {action}',
            body_template='''
System Maintenance Notification

Action: {action}
Status: {status}
Timestamp: {timestamp}

Details:
{details}
            '''.strip(),
            channels=[NotificationChannel.EMAIL, NotificationChannel.FILE],
            priority=NotificationPriority.LOW
        )

        return templates

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template with context variables."""
        try:
            # Simple template rendering (could use Jinja2 for more advanced features)
            rendered = template.format(**context)
            return rendered
        except KeyError as e:
            return f"Template error: Missing variable {e}"
        except Exception as e:
            return f"Template error: {str(e)}"

    def _delivery_loop(self):
        """Main delivery loop."""
        print("[NOTIFICATION_SYSTEM] Delivery loop started")

        while self.delivery_active:
            try:
                # Get messages to deliver
                messages_to_deliver = []

                with self.lock:
                    # Sort pending messages by priority and creation time
                    pending_list = list(self.pending_messages.values())
                    pending_list.sort(key=lambda m: (m.priority.value, m.created_at), reverse=True)

                    # Take up to batch_size messages
                    batch_size = self.config['delivery']['batch_size']
                    messages_to_deliver = pending_list[:batch_size]

                # Deliver messages
                for message in messages_to_deliver:
                    self._deliver_message(message)

                # Sleep briefly
                time.sleep(5)

            except Exception as e:
                print(f"[NOTIFICATION_SYSTEM] Error in delivery loop: {e}")
                time.sleep(30)

        print("[NOTIFICATION_SYSTEM] Delivery loop stopped")

    def _deliver_message(self, message: NotificationMessage):
        """Deliver a single message."""
        try:
            # Get channel handler
            handler = self.channel_handlers.get(message.channel)
            if not handler:
                raise ValueError(f"No handler for channel: {message.channel}")

            # Attempt delivery
            success = handler(message)

            with self.lock:
                if success:
                    # Mark as delivered
                    message.delivered_at = datetime.now().isoformat()
                    self.sent_messages[message.id] = message
                    if message.id in self.pending_messages:
                        del self.pending_messages[message.id]
                    self.stats['delivered_messages'] += 1

                else:
                    # Handle delivery failure
                    message.delivery_attempts += 1
                    max_attempts = self.config['delivery']['max_retry_attempts']

                    if message.delivery_attempts >= max_attempts:
                        # Mark as permanently failed
                        self.failed_messages[message.id] = message
                        if message.id in self.pending_messages:
                            del self.pending_messages[message.id]
                        self.stats['failed_messages'] += 1
                        print(f"[NOTIFICATION_SYSTEM] Message {message.id} failed permanently after {max_attempts} attempts")

                    else:
                        # Schedule retry
                        retry_delay = self.config['delivery']['retry_delay_minutes'][
                            min(message.delivery_attempts - 1, len(self.config['delivery']['retry_delay_minutes']) - 1)
                        ]
                        print(f"[NOTIFICATION_SYSTEM] Message {message.id} failed, will retry in {retry_delay} minutes")

        except Exception as e:
            with self.lock:
                message.error_message = str(e)
                message.delivery_attempts += 1
                print(f"[NOTIFICATION_SYSTEM] Error delivering message {message.id}: {e}")

    def _send_email(self, message: NotificationMessage) -> bool:
        """Send email notification (placeholder implementation)."""
        try:
            # This is a placeholder implementation
            # In a real implementation, you would use SMTP to send emails
            print(f"[EMAIL] To: {message.recipient}")
            print(f"[EMAIL] Subject: {message.subject}")
            print(f"[EMAIL] Body: {message.body[:100]}...")

            # Simulate email sending
            time.sleep(0.1)
            return True

        except Exception as e:
            message.error_message = f"Email delivery failed: {str(e)}"
            return False

    def _send_console(self, message: NotificationMessage) -> bool:
        """Send console notification."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            priority_indicator = "!" * message.priority.value

            print(f"[CONSOLE] {timestamp} {priority_indicator} {message.subject}")
            print(f"[CONSOLE] To: {message.recipient}")
            print(f"[CONSOLE] {message.body}")
            print(f"[CONSOLE] {'-' * 50}")

            return True

        except Exception as e:
            message.error_message = f"Console delivery failed: {str(e)}"
            return False

    def _send_file(self, message: NotificationMessage) -> bool:
        """Send file notification (write to log file)."""
        try:
            log_path = Path(self.config['file']['log_directory']) / self.config['file']['log_filename']

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"""
{timestamp} [{message.priority.value}] {message.channel.value.upper()}
To: {message.recipient}
Subject: {message.subject}
Template: {message.template_name}
Message:
{message.body}
{'=' * 80}
"""

            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            return True

        except Exception as e:
            message.error_message = f"File delivery failed: {str(e)}"
            return False

    def _send_webhook(self, message: NotificationMessage) -> bool:
        """Send webhook notification (placeholder implementation)."""
        try:
            # This is a placeholder implementation
            # In a real implementation, you would make HTTP POST requests
            webhook_data = {
                'recipient': message.recipient,
                'subject': message.subject,
                'body': message.body,
                'priority': message.priority.value,
                'timestamp': message.created_at
            }

            print(f"[WEBHOOK] Sending to: {message.recipient}")
            print(f"[WEBHOOK] Data: {json.dumps(webhook_data, indent=2)[:200]}...")

            # Simulate webhook call
            time.sleep(0.2)
            return True

        except Exception as e:
            message.error_message = f"Webhook delivery failed: {str(e)}"
            return False

    def get_notification_report(self) -> Dict:
        """Generate comprehensive notification system report."""
        with self.lock:
            current_time = datetime.now()
            start_time = datetime.fromisoformat(self.stats['start_time'])
            uptime_seconds = (current_time - start_time).total_seconds()

            # Calculate delivery rates
            total_attempted = self.stats['total_messages']
            success_rate = (self.stats['delivered_messages'] / max(1, total_attempted))

            # Channel performance
            channel_performance = {}
            for channel in NotificationChannel:
                sent_count = self.stats['messages_by_channel'][channel.value]
                channel_performance[channel.value] = {
                    'sent': sent_count,
                    'percentage': (sent_count / max(1, total_attempted)) * 100
                }

            return {
                'timestamp': current_time.isoformat(),
                'system_status': {
                    'delivery_service_active': self.delivery_active,
                    'uptime_seconds': uptime_seconds,
                    'uptime_hours': uptime_seconds / 3600
                },
                'delivery_statistics': {
                    'total_messages': total_attempted,
                    'delivered': self.stats['delivered_messages'],
                    'failed': self.stats['failed_messages'],
                    'pending': len(self.pending_messages),
                    'success_rate': success_rate
                },
                'channel_performance': channel_performance,
                'priority_distribution': dict(self.stats['messages_by_priority']),
                'queue_status': {
                    'pending_messages': len(self.pending_messages),
                    'recent_sent': len(self.sent_messages),
                    'failed_messages': len(self.failed_messages)
                },
                'configuration': {
                    'templates_configured': len(self.templates),
                    'channels_available': len(self.channel_handlers),
                    'recipients_configured': sum(len(recipients) for recipients in self.recipients.values())
                },
                'recommendations': self._generate_notification_recommendations()
            }

    def _generate_notification_recommendations(self) -> List[str]:
        """Generate notification system improvement recommendations."""
        recommendations = []

        # Check success rate
        total_attempted = self.stats['total_messages']
        if total_attempted > 0:
            success_rate = self.stats['delivered_messages'] / total_attempted

            if success_rate < 0.8:
                recommendations.append("Low delivery success rate - review channel configurations")

            if success_rate > 0.95:
                recommendations.append("Excellent delivery performance - consider expanding notification scope")

        # Check queue backlog
        if len(self.pending_messages) > 50:
            recommendations.append("Large pending message queue - consider increasing delivery capacity")

        # Check failure rate
        if self.stats['failed_messages'] > self.stats['delivered_messages'] * 0.1:
            recommendations.append("High failure rate detected - review delivery configurations")

        if not recommendations:
            recommendations.append("Notification system operating efficiently")

        return recommendations

if __name__ == "__main__":
    # Test the notification system
    print("Testing Notification System...")

    notifier = NotificationSystem()

    # Start delivery service
    notifier.start_delivery_service()

    try:
        # Test various notification types
        print("1. Sending test alert...")
        notifier.send_alert('warning', 'test_component', 'This is a test warning message')

        print("2. Sending status update...")
        notifier.send_status_update('processing_engine', 'running', {'cpu': 45.2, 'memory': 67.8})

        print("3. Sending processing summary...")
        summary = {'rows_processed': 150, 'success_rate': 0.85, 'duration': 120}
        notifier.send_processing_summary(summary)

        # Wait for delivery
        time.sleep(10)

        # Check delivery stats
        stats = notifier.get_delivery_stats()
        print(f"\nDelivery Statistics:")
        print(f"  Total messages: {stats['statistics']['total_messages']}")
        print(f"  Delivered: {stats['delivered_messages']}")
        print(f"  Pending: {stats['pending_count']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")

        # Generate report
        report = notifier.get_notification_report()
        print(f"\nNotification Report:")
        print(f"  System uptime: {report['system_status']['uptime_hours']:.1f} hours")
        print(f"  Delivery success rate: {report['delivery_statistics']['success_rate']:.1%}")

    finally:
        # Stop delivery service
        notifier.stop_delivery_service()

    print("Notification System test completed.")