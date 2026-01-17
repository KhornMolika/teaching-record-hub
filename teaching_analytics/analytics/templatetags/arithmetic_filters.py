from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplies the value with the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def div(value, arg):
    """Divides the value by the arg."""
    try:
        if float(arg) == 0:
            return ''
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def sub(value, arg):
    """Subtracts the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''
