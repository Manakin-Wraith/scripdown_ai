"""
SlateOne Email Template System

Centralized email template management with reusable components
and consistent design system.
"""

from .registry import EmailTemplateRegistry
from .base_template import BaseEmailTemplate

__all__ = ['EmailTemplateRegistry', 'BaseEmailTemplate']
