from django import template

register = template.Library()

@register.filter(name='split')
def split(value, key):
    """
    Splits a string by a given key (delimiter) and returns a list.
    """
    return value.split(key)