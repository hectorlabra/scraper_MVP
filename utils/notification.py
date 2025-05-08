#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notification System for ScraperMVP

This module provides notification capabilities for alerting about critical errors,
scraping failures, and system status. It supports multiple notification channels:
- Email notifications
- Slack messages
- Simple SMS notifications (via email-to-SMS gateways)
- Custom webhooks

The notification system can be configured to send alerts based on severity,
and includes rate limiting to prevent notification fatigue.
"""

import os
import logging
import json
import time
import threading
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum, auto

# Configure logger
logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """
    Notification severity levels.
    """
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

class NotificationChannel(Enum):
    """
    Available notification channels.
    """
    EMAIL = auto()
    SLACK = auto()
    SMS = auto()
    WEBHOOK = auto()

class RateLimiter:
    """
    Rate limiter for notifications to prevent alert fatigue.
    """
    def __init__(self, max_count: int = 5, time_window: int = 3600):
        """
        Initialize the rate limiter.
        
        Args:
            max_count: Maximum number of notifications in the time window
            time_window: Time window in seconds
        """
        self.max_count = max_count
        self.time_window = time_window
        self.notifications = {}
        self.lock = threading.Lock()
    
    def should_notify(self, notification_key: str) -> bool:
        """
        Check if a notification should be sent based on rate limits.
        
        Args:
            notification_key: Unique identifier for the notification
            
        Returns:
            True if the notification should be sent, False otherwise
        """
        with self.lock:
            now = time.time()
            
            # Remove old notifications outside the time window
            cutoff = now - self.time_window
            self.notifications = {k: v for k, v in self.notifications.items() if v[-1] >= cutoff}
            
            # Get timestamps for this notification
            timestamps = self.notifications.get(notification_key, [])
            
            # Filter to timestamps within time window
            recent_timestamps = [t for t in timestamps if t >= cutoff]
            
            # If under the limit, add current timestamp and allow notification
            if len(recent_timestamps) < self.max_count:
                self.notifications[notification_key] = recent_timestamps + [now]
                return True
            
            return False
    
    def reset(self, notification_key: Optional[str] = None) -> None:
        """
        Reset rate limiting for a specific notification or all notifications.
        
        Args:
            notification_key: Key to reset, or None to reset all
        """
        with self.lock:
            if notification_key:
                if notification_key in self.notifications:
                    del self.notifications[notification_key]
            else:
                self.notifications.clear()

class NotificationManager:
    """
    Manager for sending notifications across multiple channels.
    """
    def __init__(self, app_name: str = "ScraperMVP"):
        """
        Initialize the notification manager.
        
        Args:
            app_name: Name of the application for notification subjects
        """
        self.app_name = app_name
        self.email_config = None
        self.slack_config = None
        self.sms_config = None
        self.webhook_config = None
        self.min_level = NotificationLevel.WARNING
        self.channels = []
        
        # Message templates
        self.templates = {
            NotificationLevel.DEBUG: "[DEBUG] {app_name}: {subject}",
            NotificationLevel.INFO: "[INFO] {app_name}: {subject}",
            NotificationLevel.WARNING: "[WARNING] {app_name}: {subject}",
            NotificationLevel.ERROR: "[ERROR] {app_name}: {subject}",
            NotificationLevel.CRITICAL: "[CRITICAL] {app_name}: {subject}"
        }
        
        # Rate limiter for notifications
        self.rate_limiter = RateLimiter()
    
    def configure_email(self, 
                        smtp_server: str, 
                        smtp_port: int, 
                        username: str, 
                        password: str,
                        from_address: str,
                        to_addresses: List[str],
                        use_tls: bool = True) -> None:
        """
        Configure email notifications.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_address: Sender email address
            to_addresses: List of recipient email addresses
            use_tls: Whether to use TLS for SMTP
        """
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_address": from_address,
            "to_addresses": to_addresses,
            "use_tls": use_tls
        }
        
        if NotificationChannel.EMAIL not in self.channels:
            self.channels.append(NotificationChannel.EMAIL)
        
        logger.info("Email notifications configured")
    
    def configure_slack(self, webhook_url: str, channel: str = None, username: str = None) -> None:
        """
        Configure Slack notifications.
        
        Args:
            webhook_url: Slack webhook URL
            channel: Slack channel to send messages to
            username: Username to use for messages
        """
        self.slack_config = {
            "webhook_url": webhook_url,
            "channel": channel,
            "username": username or f"{self.app_name} Bot"
        }
        
        if NotificationChannel.SLACK not in self.channels:
            self.channels.append(NotificationChannel.SLACK)
        
        logger.info("Slack notifications configured")
    
    def configure_sms(self, 
                     smtp_server: str, 
                     smtp_port: int, 
                     username: str, 
                     password: str,
                     from_address: str,
                     phone_numbers: List[str],
                     gateway_domain: str = "txt.att.net",
                     use_tls: bool = True) -> None:
        """
        Configure SMS notifications via email-to-SMS gateway.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_address: Sender email address
            phone_numbers: List of phone numbers (without gateway domain)
            gateway_domain: SMS gateway domain (default: txt.att.net for AT&T)
            use_tls: Whether to use TLS for SMTP
        """
        # Convert phone numbers to email addresses using the gateway domain
        to_addresses = [f"{phone}@{gateway_domain}" for phone in phone_numbers]
        
        self.sms_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_address": from_address,
            "to_addresses": to_addresses,
            "use_tls": use_tls
        }
        
        if NotificationChannel.SMS not in self.channels:
            self.channels.append(NotificationChannel.SMS)
        
        logger.info("SMS notifications configured")
    
    def configure_webhook(self, url: str, headers: Dict[str, str] = None, method: str = "POST") -> None:
        """
        Configure webhook notifications.
        
        Args:
            url: Webhook URL
            headers: HTTP headers for webhook requests
            method: HTTP method for webhook requests
        """
        self.webhook_config = {
            "url": url,
            "headers": headers or {"Content-Type": "application/json"},
            "method": method
        }
        
        if NotificationChannel.WEBHOOK not in self.channels:
            self.channels.append(NotificationChannel.WEBHOOK)
        
        logger.info("Webhook notifications configured")
    
    def set_minimum_level(self, level: NotificationLevel) -> None:
        """
        Set the minimum notification level.
        
        Args:
            level: Minimum level to send notifications for
        """
        self.min_level = level
        logger.info(f"Minimum notification level set to {level.name}")
    
    def notify(self, 
              subject: str, 
              message: str, 
              level: NotificationLevel = NotificationLevel.INFO,
              notification_key: str = None,
              channels: List[NotificationChannel] = None,
              include_timestamp: bool = True,
              additional_data: Dict[str, Any] = None) -> bool:
        """
        Send a notification through configured channels.
        
        Args:
            subject: Notification subject
            message: Notification message
            level: Notification level
            notification_key: Key for rate limiting (defaults to subject)
            channels: Specific channels to use (defaults to all configured)
            include_timestamp: Whether to include timestamp in message
            additional_data: Additional data to include in webhook payloads
            
        Returns:
            True if at least one notification was sent successfully
        """
        # Check minimum level
        if level.value < self.min_level.value:
            logger.debug(f"Notification level {level.name} below minimum {self.min_level.name}, skipping")
            return False
        
        # Check rate limiting
        key = notification_key or subject
        if not self.rate_limiter.should_notify(key):
            logger.info(f"Notification '{key}' rate limited")
            return False
        
        # Add timestamp if requested
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_message = f"[{timestamp}] {message}"
        else:
            full_message = message
        
        # Format subject with template
        formatted_subject = self.templates[level].format(
            app_name=self.app_name,
            subject=subject
        )
        
        # Determine channels to use
        use_channels = channels if channels is not None else self.channels
        
        # Send notifications through each channel
        success = False
        
        for channel in use_channels:
            try:
                if channel == NotificationChannel.EMAIL and self.email_config:
                    success |= self._send_email(formatted_subject, full_message)
                
                elif channel == NotificationChannel.SLACK and self.slack_config:
                    success |= self._send_slack(formatted_subject, full_message, level)
                
                elif channel == NotificationChannel.SMS and self.sms_config:
                    # SMS messages should be shorter
                    sms_message = f"{formatted_subject}: {message[:100]}..."
                    success |= self._send_sms(sms_message)
                
                elif channel == NotificationChannel.WEBHOOK and self.webhook_config:
                    success |= self._send_webhook(formatted_subject, full_message, level, additional_data)
            
            except Exception as e:
                logger.error(f"Error sending notification via {channel.name}: {str(e)}")
        
        if success:
            logger.info(f"Notification '{formatted_subject}' sent successfully")
        else:
            logger.warning(f"Failed to send notification '{formatted_subject}'")
        
        return success
    
    def _send_email(self, subject: str, message: str) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject
            message: Email message
            
        Returns:
            True if successful, False otherwise
        """
        config = self.email_config
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = config["from_address"]
        msg["To"] = ", ".join(config["to_addresses"])
        msg["Subject"] = subject
        
        # Add message body
        msg.attach(MIMEText(message, "plain"))
        
        try:
            # Connect to SMTP server
            if config["use_tls"]:
                server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
                server.starttls()
            else:
                server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            
            # Login if credentials provided
            if config["username"] and config["password"]:
                server.login(config["username"], config["password"])
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _send_slack(self, subject: str, message: str, level: NotificationLevel) -> bool:
        """
        Send a Slack notification.
        
        Args:
            subject: Message subject
            message: Message content
            level: Notification level
            
        Returns:
            True if successful, False otherwise
        """
        config = self.slack_config
        
        # Set color based on level
        color_map = {
            NotificationLevel.DEBUG: "#808080",    # Gray
            NotificationLevel.INFO: "#2196F3",     # Blue
            NotificationLevel.WARNING: "#FF9800",  # Orange
            NotificationLevel.ERROR: "#F44336",    # Red
            NotificationLevel.CRITICAL: "#9C27B0"  # Purple
        }
        
        # Create payload
        payload = {
            "username": config["username"],
            "text": subject,
            "attachments": [{
                "color": color_map.get(level, "#2196F3"),
                "text": message,
                "ts": int(time.time())
            }]
        }
        
        if config["channel"]:
            payload["channel"] = config["channel"]
        
        try:
            # Send to webhook
            response = requests.post(
                config["webhook_url"],
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200 and response.text == "ok":
                return True
            else:
                logger.error(f"Error sending Slack notification: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return False
    
    def _send_sms(self, message: str) -> bool:
        """
        Send an SMS notification via email-to-SMS gateway.
        
        Args:
            message: SMS message
            
        Returns:
            True if successful, False otherwise
        """
        config = self.sms_config
        
        # Create message (SMS should be short)
        msg = MIMEText(message[:160])
        msg["From"] = config["from_address"]
        msg["To"] = ", ".join(config["to_addresses"])
        msg["Subject"] = ""  # No subject for SMS
        
        try:
            # Connect to SMTP server
            if config["use_tls"]:
                server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
                server.starttls()
            else:
                server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            
            # Login if credentials provided
            if config["username"] and config["password"]:
                server.login(config["username"], config["password"])
            
            # Send SMS
            server.send_message(msg)
            server.quit()
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    def _send_webhook(self, subject: str, message: str, level: NotificationLevel, additional_data: Dict[str, Any] = None) -> bool:
        """
        Send a webhook notification.
        
        Args:
            subject: Notification subject
            message: Notification message
            level: Notification level
            additional_data: Additional data to include in payload
            
        Returns:
            True if successful, False otherwise
        """
        config = self.webhook_config
        
        # Create payload
        payload = {
            "subject": subject,
            "message": message,
            "level": level.name,
            "timestamp": datetime.now().isoformat(),
            "application": self.app_name
        }
        
        if additional_data:
            payload["data"] = additional_data
        
        try:
            # Send webhook request
            response = requests.request(
                method=config["method"],
                url=config["url"],
                headers=config["headers"],
                json=payload
            )
            
            if 200 <= response.status_code < 300:
                return True
            else:
                logger.error(f"Error sending webhook: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")
            return False

# Create global notification manager instance
notification_manager = NotificationManager()

def configure_notifications_from_env() -> NotificationManager:
    """
    Configure the notification manager from environment variables.
    
    Returns:
        Configured NotificationManager instance
    """
    # Configure minimum level
    min_level_str = os.environ.get("NOTIFICATION_MIN_LEVEL", "WARNING")
    min_level = getattr(NotificationLevel, min_level_str, NotificationLevel.WARNING)
    notification_manager.set_minimum_level(min_level)
    
    # Configure email if enabled
    if os.environ.get("ENABLE_EMAIL_NOTIFICATIONS", "").lower() == "true":
        notification_manager.configure_email(
            smtp_server=os.environ.get("EMAIL_SMTP_SERVER", ""),
            smtp_port=int(os.environ.get("EMAIL_SMTP_PORT", "587")),
            username=os.environ.get("EMAIL_USERNAME", ""),
            password=os.environ.get("EMAIL_PASSWORD", ""),
            from_address=os.environ.get("EMAIL_FROM", ""),
            to_addresses=os.environ.get("EMAIL_TO", "").split(","),
            use_tls=os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
        )
    
    # Configure Slack if enabled
    if os.environ.get("ENABLE_SLACK_NOTIFICATIONS", "").lower() == "true":
        notification_manager.configure_slack(
            webhook_url=os.environ.get("SLACK_WEBHOOK_URL", ""),
            channel=os.environ.get("SLACK_CHANNEL", ""),
            username=os.environ.get("SLACK_USERNAME", "")
        )
    
    # Configure SMS if enabled
    if os.environ.get("ENABLE_SMS_NOTIFICATIONS", "").lower() == "true":
        notification_manager.configure_sms(
            smtp_server=os.environ.get("SMS_SMTP_SERVER", ""),
            smtp_port=int(os.environ.get("SMS_SMTP_PORT", "587")),
            username=os.environ.get("SMS_USERNAME", ""),
            password=os.environ.get("SMS_PASSWORD", ""),
            from_address=os.environ.get("SMS_FROM", ""),
            phone_numbers=os.environ.get("SMS_PHONE_NUMBERS", "").split(","),
            gateway_domain=os.environ.get("SMS_GATEWAY_DOMAIN", "txt.att.net"),
            use_tls=os.environ.get("SMS_USE_TLS", "true").lower() == "true"
        )
    
    # Configure webhook if enabled
    if os.environ.get("ENABLE_WEBHOOK_NOTIFICATIONS", "").lower() == "true":
        notification_manager.configure_webhook(
            url=os.environ.get("WEBHOOK_URL", ""),
            headers=json.loads(os.environ.get("WEBHOOK_HEADERS", "{}")),
            method=os.environ.get("WEBHOOK_METHOD", "POST")
        )
    
    return notification_manager

def notify(subject: str, 
          message: str, 
          level: str = "INFO",
          notification_key: str = None,
          additional_data: Dict[str, Any] = None) -> bool:
    """
    Convenience function to send a notification through the global manager.
    
    Args:
        subject: Notification subject
        message: Notification message
        level: Notification level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        notification_key: Key for rate limiting
        additional_data: Additional data to include in webhook payloads
        
    Returns:
        True if at least one notification was sent successfully
    """
    # Convert string level to enum
    level_enum = getattr(NotificationLevel, level, NotificationLevel.INFO)
    
    return notification_manager.notify(
        subject=subject,
        message=message,
        level=level_enum,
        notification_key=notification_key,
        additional_data=additional_data
    )
