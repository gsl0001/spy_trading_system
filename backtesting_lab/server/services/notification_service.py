"""
Notification Service — Sends alerts via Discord webhook and email.
"""
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from loguru import logger

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import requests
    HAS_HTTPX = False


class NotificationService:
    """Multi-channel notification service for trade alerts and system events."""

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._enabled = self._config.get("enabled", False)
        self._channels = self._config.get("channels", {})
        self._events = self._config.get("events", {})

    def update_config(self, config: dict):
        """Hot-reload notification config."""
        self._config = config
        self._enabled = config.get("enabled", False)
        self._channels = config.get("channels", {})
        self._events = config.get("events", {})

    # ── Public Alert Methods ──

    def notify_trade_entry(self, trade: dict):
        """Alert on trade entry."""
        if not self._should_notify("trade_entry"):
            return
        
        msg = self._format_trade_entry(trade)
        self._send_all(msg, title="🟢 TRADE ENTRY")

    def notify_trade_exit(self, trade: dict):
        """Alert on trade exit."""
        if not self._should_notify("trade_exit"):
            return
        
        pnl = trade.get("pnl", 0)
        emoji = "🟢" if pnl > 0 else "🔴"
        msg = self._format_trade_exit(trade)
        self._send_all(msg, title=f"{emoji} TRADE EXIT")

    def notify_daily_summary(self, summary: dict):
        """Send end-of-day summary."""
        if not self._should_notify("daily_summary"):
            return
        
        msg = self._format_daily_summary(summary)
        self._send_all(msg, title="📊 DAILY SUMMARY")

    def notify_error(self, error: str, context: str = ""):
        """Alert on system error."""
        if not self._should_notify("error_alert"):
            return
        
        msg = f"**Error**: {error}\n**Context**: {context}\n**Time**: {datetime.now().strftime('%H:%M:%S')}"
        self._send_all(msg, title="⚠️ SYSTEM ERROR")

    def notify_system_event(self, event: str, details: str = ""):
        """Alert on system start/stop."""
        event_key = "system_start" if "start" in event.lower() else "system_stop"
        if not self._should_notify(event_key):
            return
        
        msg = f"**Event**: {event}\n**Details**: {details}\n**Time**: {datetime.now().strftime('%H:%M:%S')}"
        emoji = "🚀" if "start" in event.lower() else "🛑"
        self._send_all(msg, title=f"{emoji} {event.upper()}")

    # ── Private Methods ──

    def _should_notify(self, event_type: str) -> bool:
        """Check if notifications are enabled for this event type."""
        if not self._enabled:
            return False
        return self._events.get(event_type, False)

    def _send_all(self, message: str, title: str = ""):
        """Send to all enabled channels."""
        discord_cfg = self._channels.get("discord", {})
        if discord_cfg.get("enabled") and discord_cfg.get("webhook_url"):
            self._send_discord(discord_cfg["webhook_url"], message, title)

        email_cfg = self._channels.get("email", {})
        if email_cfg.get("enabled") and email_cfg.get("to_address"):
            self._send_email(email_cfg, message, title)

    def _send_discord(self, webhook_url: str, message: str, title: str = ""):
        """Send a message to Discord via webhook."""
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": 3066993,  # Green
                "footer": {"text": f"QuantOS • {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
            }]
        }
        
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=10) as client:
                    resp = client.post(webhook_url, json=payload)
            else:
                resp = requests.post(webhook_url, json=payload, timeout=10)
            
            if resp.status_code not in (200, 204):
                logger.warning(f"Discord webhook returned {resp.status_code}")
            else:
                logger.debug(f"Discord notification sent: {title}")
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")

    def _send_email(self, config: dict, message: str, title: str = ""):
        """Send an email alert."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[QuantOS] {title}"
            msg["From"] = config.get("username", "quantos@system.local")
            msg["To"] = config["to_address"]
            
            # Plain text
            msg.attach(MIMEText(message, "plain"))
            
            # HTML version
            html_body = f"<h2>{title}</h2><pre>{message}</pre>"
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(config["smtp_host"], config.get("smtp_port", 587)) as server:
                server.starttls()
                if config.get("username") and config.get("password"):
                    server.login(config["username"], config["password"])
                server.sendmail(msg["From"], [config["to_address"]], msg.as_string())
            
            logger.debug(f"Email notification sent: {title}")
        except Exception as e:
            logger.error(f"Email notification failed: {e}")

    # ── Message Formatters ──

    def _format_trade_entry(self, trade: dict) -> str:
        return (
            f"**Strategy**: {trade.get('strategy', 'N/A')}\n"
            f"**Direction**: {trade.get('trade_type', trade.get('Type', 'Long'))}\n"
            f"**Entry Price**: ${trade.get('entry_price', trade.get('Entry Price', 0)):.2f}\n"
            f"**ML Confidence**: {trade.get('ml_confidence', 'N/A')}\n"
            f"**Time**: {datetime.now().strftime('%H:%M:%S')}"
        )

    def _format_trade_exit(self, trade: dict) -> str:
        pnl = trade.get("pnl", trade.get("PnL", 0))
        return (
            f"**Strategy**: {trade.get('strategy', 'N/A')}\n"
            f"**Entry**: ${trade.get('entry_price', trade.get('Entry Price', 0)):.2f}\n"
            f"**Exit**: ${trade.get('exit_price', trade.get('Exit Price', 0)):.2f}\n"
            f"**PnL**: ${pnl:+.2f} ({trade.get('pnl_pct', trade.get('PnL %', 0)):+.1f}%)\n"
            f"**Duration**: {trade.get('duration', 'N/A')} bars"
        )

    def _format_daily_summary(self, summary: dict) -> str:
        return (
            f"**Date**: {summary.get('date', 'N/A')}\n"
            f"**Trades**: {summary.get('total_trades', 0)}\n"
            f"**Wins/Losses**: {summary.get('wins', 0)}/{summary.get('losses', 0)}\n"
            f"**Total PnL**: ${summary.get('total_pnl', 0):+.2f}\n"
            f"**Win Rate**: {summary.get('win_rate', 0):.1f}%\n"
            f"**Best Trade**: ${summary.get('best_trade', 0):+.2f}\n"
            f"**Worst Trade**: ${summary.get('worst_trade', 0):+.2f}"
        )
