"""
SlateOne Email Template System

Centralized email template management with reusable components
and consistent design system.
"""

from .registry import EmailTemplateRegistry
from .base_template import BaseEmailTemplate

# Import templates to register them
from . import feature_announcement

__all__ = ['EmailTemplateRegistry', 'BaseEmailTemplate']
