from decimal import Decimal

from django import template

register = template.Library()


def _group_thousands_with_space(s: str) -> str:
    """Insert a space as thousands separator into integer string s."""
    # handle optional sign outside
    sign = ''
    if s.startswith('-'):
        sign = '-'
        s = s[1:]
    # Reverse grouping every 3 chars
    parts = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    return sign + ' '.join(reversed(parts))


@register.filter(name='money')
def money(value):
    """Format a numeric value using spaces for thousands and omit trailing .00.

    Examples:
    - 90000.00 -> "90 000"
    - 1234.50 -> "1 234.5"
    - None -> ''
    """
    if value is None:
        return ''
    try:
        d = Decimal(value)
    except Exception:
        return value

    # Normalize decimal to plain string without exponent
    s = format(d.normalize(), 'f')
    if s.startswith('-'):
        sign = '-'
        s = s[1:]
    else:
        sign = ''

    if '.' in s:
        whole, frac = s.split('.', 1)
        # remove trailing zeros in fractional part
        frac = frac.rstrip('0')
        whole_fmt = _group_thousands_with_space(whole)
        if frac == '' or frac == '0':
            return f"{sign}{whole_fmt}"
        return f"{sign}{whole_fmt}.{frac}"
    else:
        whole_fmt = _group_thousands_with_space(s)
        return f"{sign}{whole_fmt}"
