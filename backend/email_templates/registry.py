"""
Email Template Registry

Central registry for all email templates in the system.
Provides easy discovery, testing, and management.
"""

from typing import Dict, Type, List
from .base_template import BaseEmailTemplate


class EmailTemplateRegistry:
    """
    Central registry for all email templates.
    
    Usage:
        # Register a template
        @EmailTemplateRegistry.register('welcome')
        class WelcomeEmail(BaseEmailTemplate):
            ...
        
        # Get a template
        template_class = EmailTemplateRegistry.get('welcome')
        email = template_class(user_name='John', email='john@example.com')
        subject, html = email.build()
    """
    
    _templates: Dict[str, Type[BaseEmailTemplate]] = {}
    _metadata: Dict[str, Dict] = {}
    
    @classmethod
    def register(cls, name: str, category: str = 'general', description: str = ''):
        """
        Decorator to register an email template.
        
        Args:
            name: Unique template identifier
            category: Template category (transactional, engagement, operational)
            description: Template description
        """
        def decorator(template_class: Type[BaseEmailTemplate]):
            cls._templates[name] = template_class
            cls._metadata[name] = {
                'name': name,
                'category': category,
                'description': description,
                'class': template_class.__name__,
            }
            return template_class
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Type[BaseEmailTemplate]:
        """Get a template class by name"""
        if name not in cls._templates:
            raise ValueError(f"Template '{name}' not found. Available: {list(cls._templates.keys())}")
        return cls._templates[name]
    
    @classmethod
    def list_all(cls) -> List[Dict]:
        """List all registered templates with metadata"""
        return list(cls._metadata.values())
    
    @classmethod
    def list_by_category(cls, category: str) -> List[Dict]:
        """List templates by category"""
        return [t for t in cls._metadata.values() if t['category'] == category]
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all template categories"""
        return list(set(t['category'] for t in cls._metadata.values()))
