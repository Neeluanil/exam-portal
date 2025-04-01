from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key))  # Convert key to string to match answers dict