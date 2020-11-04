from .locales import en
from .locales import fr


# Define here all the existing language tables.
locales = dict({
    'en': en.locale,
    'fr': fr.locale,
})

def t(key, lang, context = {}):
    """
    Given a text key and a language it returns the corresponding text for the language.

    :param key: a string that identifies the desired piece of text.
    :param lang: the ISO code for the language locale.
    :param context: context variables to be passed to the template.

    :return: the desired text in the given language.
    """
    lang = lang[0:2]
    locale = locales.get(lang)

    if not locale:
        raise Exception(f'Locale "{lang}" not found')
    return locale.get(key, '').format(**context)
