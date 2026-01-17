from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value with the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter(name='split')
def split(value, key):
    """
    Splits a string by a given key (delimiter) and returns a list.
    """
    return value.split(key)