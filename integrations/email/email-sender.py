#!/usr/bin/env python3
"""
LeverEdge Email Sender Utility

A command-line utility for sending emails using SendGrid with Jinja2 template rendering.
Supports all email templates in the templates/ directory.

Usage:
    python email-sender.py --to user@example.com --template welcome --data '{"user_name": "John"}'
    python email-sender.py --to user@example.com --template invoice --data-file invoice_data.json
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, Content, Attachment, FileName,
    FileContent, FileType, Disposition, Category,
    TrackingSettings, ClickTracking, OpenTracking
)
from premailer import transform
import html2text


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailSender:
    """SendGrid email sender with Jinja2 template support."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the email sender.

        Args:
            config_path: Path to config.yaml file. If not provided, uses default location.
        """
        self.base_dir = Path(__file__).parent
        self.config_path = config_path or self.base_dir / 'config.yaml'
        self.config = self._load_config()

        # Initialize SendGrid client
        api_key = os.environ.get('SENDGRID_API_KEY') or self.config.get('sendgrid', {}).get('api_key')
        if not api_key or api_key.startswith('${'):
            raise ValueError(
                "SendGrid API key not found. Set SENDGRID_API_KEY environment variable."
            )
        self.sg_client = SendGridAPIClient(api_key)

        # Initialize Jinja2 environment
        template_dir = self.base_dir / self.config.get('templates', {}).get('directory', 'templates')
        self.jinja_env = Environment(
            loader=FileSystemLoader([template_dir, self.base_dir / 'supabase-templates']),
            autoescape=True
        )

        # Default template variables
        self.default_vars = self.config.get('templates', {}).get('defaults', {})

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return {}

    def _render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given variables.

        Args:
            template_name: Name of the template file (without path)
            variables: Dictionary of variables to pass to the template

        Returns:
            Rendered HTML string
        """
        # Merge default variables with provided variables
        merged_vars = {**self.default_vars, **variables}
        merged_vars['year'] = datetime.now().year

        try:
            template = self.jinja_env.get_template(f"{template_name}.html")
            rendered_html = template.render(**merged_vars)

            # Inline CSS for email client compatibility
            return transform(rendered_html)
        except TemplateNotFound:
            raise ValueError(f"Template '{template_name}' not found")

    def _html_to_plain_text(self, html_content: str) -> str:
        """Convert HTML content to plain text for email clients that don't support HTML."""
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        return h.handle(html_content)

    def send_email(
        self,
        to_email: str,
        template_name: str,
        variables: Dict[str, Any],
        subject: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        categories: Optional[list] = None,
        attachments: Optional[list] = None,
        sandbox_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send an email using a template.

        Args:
            to_email: Recipient email address
            template_name: Name of the template to use
            variables: Variables to pass to the template
            subject: Email subject (can also be in template or variables)
            from_email: Sender email address (uses config default if not provided)
            from_name: Sender display name (uses config default if not provided)
            reply_to: Reply-to email address
            categories: SendGrid categories for analytics
            attachments: List of attachment dictionaries
            sandbox_mode: If True, email won't actually be sent (for testing)

        Returns:
            Dictionary with send status and message ID
        """
        # Render the template
        html_content = self._render_template(template_name, variables)
        plain_text = self._html_to_plain_text(html_content)

        # Determine subject
        if not subject:
            subject = variables.get('subject') or self._get_default_subject(template_name)

        # Get sender info from config
        sender_config = self.config.get('sender', {})
        from_email = from_email or sender_config.get('from_email', 'noreply@leveredge.io')
        from_name = from_name or sender_config.get('from_name', 'LeverEdge')
        reply_to = reply_to or sender_config.get('reply_to')

        # Build the email
        message = Mail(
            from_email=Email(from_email, from_name),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
            plain_text_content=Content("text/plain", plain_text)
        )

        # Add reply-to if provided
        if reply_to:
            message.reply_to = Email(reply_to)

        # Add categories
        if categories:
            for category in categories:
                message.category = Category(category)
        else:
            # Add default category based on template
            message.category = Category(template_name)

        # Configure tracking
        tracking_config = self.config.get('tracking', {})
        tracking_settings = TrackingSettings()
        tracking_settings.click_tracking = ClickTracking(
            tracking_config.get('click_tracking', True),
            tracking_config.get('click_tracking', True)
        )
        tracking_settings.open_tracking = OpenTracking(
            tracking_config.get('open_tracking', True)
        )
        message.tracking_settings = tracking_settings

        # Add attachments
        if attachments:
            for att in attachments:
                attachment = Attachment()
                attachment.file_content = FileContent(att['content'])
                attachment.file_type = FileType(att.get('type', 'application/octet-stream'))
                attachment.file_name = FileName(att['filename'])
                attachment.disposition = Disposition(att.get('disposition', 'attachment'))
                message.add_attachment(attachment)

        # Enable sandbox mode if requested or configured
        if sandbox_mode or self.config.get('sendgrid', {}).get('sandbox_mode', False):
            message.mail_settings = {
                "sandbox_mode": {"enable": True}
            }
            logger.info("Sandbox mode enabled - email will not be sent")

        # Send the email
        try:
            response = self.sg_client.send(message)

            result = {
                'success': response.status_code in [200, 201, 202],
                'status_code': response.status_code,
                'message_id': response.headers.get('X-Message-Id'),
                'to_email': to_email,
                'template': template_name,
                'subject': subject
            }

            if result['success']:
                logger.info(f"Email sent successfully to {to_email} using template '{template_name}'")
            else:
                logger.error(f"Failed to send email: {response.status_code}")
                result['error'] = response.body.decode('utf-8') if response.body else 'Unknown error'

            return result

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email,
                'template': template_name
            }

    def _get_default_subject(self, template_name: str) -> str:
        """Get default subject line based on template name."""
        subjects = {
            'welcome': 'Welcome to LeverEdge!',
            'password-reset': 'Reset Your Password',
            'invoice': 'Invoice from LeverEdge',
            'reminder': 'Reminder from LeverEdge',
            'notification': 'Notification from LeverEdge',
            'weekly-summary': 'Your Weekly Summary',
            'confirm-signup': 'Confirm Your Email - LeverEdge',
            'reset-password': 'Reset Your Password - LeverEdge',
            'magic-link': 'Your Sign-In Link - LeverEdge',
            'invite-user': 'You\'re Invited to LeverEdge'
        }
        return subjects.get(template_name, f'Message from LeverEdge')

    def list_templates(self) -> list:
        """List available email templates."""
        templates = []
        template_dirs = [
            self.base_dir / 'templates',
            self.base_dir / 'supabase-templates'
        ]
        for template_dir in template_dirs:
            if template_dir.exists():
                for template_file in template_dir.glob('*.html'):
                    templates.append(template_file.stem)
        return sorted(templates)

    def preview_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Preview a rendered template without sending.

        Args:
            template_name: Name of the template
            variables: Variables to pass to the template

        Returns:
            Rendered HTML string
        """
        return self._render_template(template_name, variables)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='LeverEdge Email Sender - Send emails using SendGrid with templates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Send welcome email:
    python email-sender.py --to user@example.com --template welcome --data '{"user_name": "John"}'

  Send invoice:
    python email-sender.py --to user@example.com --template invoice --data-file invoice.json

  Preview template:
    python email-sender.py --preview --template welcome --data '{"user_name": "John"}'

  List templates:
    python email-sender.py --list-templates
        """
    )

    parser.add_argument('--to', help='Recipient email address')
    parser.add_argument('--template', help='Template name (without .html extension)')
    parser.add_argument('--subject', help='Email subject (optional, uses default if not provided)')
    parser.add_argument('--data', help='JSON string of template variables')
    parser.add_argument('--data-file', help='Path to JSON file with template variables')
    parser.add_argument('--from-email', help='Sender email address')
    parser.add_argument('--from-name', help='Sender display name')
    parser.add_argument('--reply-to', help='Reply-to email address')
    parser.add_argument('--config', help='Path to config.yaml file')
    parser.add_argument('--sandbox', action='store_true', help='Enable sandbox mode (no email sent)')
    parser.add_argument('--preview', action='store_true', help='Preview rendered template without sending')
    parser.add_argument('--list-templates', action='store_true', help='List available templates')
    parser.add_argument('--output', help='Output file for preview (default: stdout)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize sender
    try:
        sender = EmailSender(config_path=args.config)
    except ValueError as e:
        if args.list_templates:
            # For list templates, we don't need API key
            sender = EmailSender.__new__(EmailSender)
            sender.base_dir = Path(__file__).parent
            templates = []
            for template_dir in [sender.base_dir / 'templates', sender.base_dir / 'supabase-templates']:
                if template_dir.exists():
                    for tf in template_dir.glob('*.html'):
                        templates.append(tf.stem)
            print("Available templates:")
            for t in sorted(templates):
                print(f"  - {t}")
            return 0
        else:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # List templates
    if args.list_templates:
        print("Available templates:")
        for template in sender.list_templates():
            print(f"  - {template}")
        return 0

    # Validate required arguments for sending/preview
    if not args.template:
        parser.error("--template is required")

    # Load template variables
    variables = {}
    if args.data:
        try:
            variables = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"Error parsing --data JSON: {e}", file=sys.stderr)
            return 1

    if args.data_file:
        try:
            with open(args.data_file, 'r') as f:
                file_vars = json.load(f)
                variables.update(file_vars)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading --data-file: {e}", file=sys.stderr)
            return 1

    # Preview mode
    if args.preview:
        try:
            html = sender.preview_template(args.template, variables)
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(html)
                print(f"Preview saved to {args.output}")
            else:
                print(html)
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Send email
    if not args.to:
        parser.error("--to is required when sending email")

    result = sender.send_email(
        to_email=args.to,
        template_name=args.template,
        variables=variables,
        subject=args.subject,
        from_email=args.from_email,
        from_name=args.from_name,
        reply_to=args.reply_to,
        sandbox_mode=args.sandbox
    )

    # Output result
    print(json.dumps(result, indent=2))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
