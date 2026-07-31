from django import template

register = template.Library()


@register.filter
def group3(value):
    value = str(value)
    return " ".join([value[i:i+3] for i in range(0, len(value), 3)])