from .locales import en
from .locales import fr


# Define here all the existing language tables.
locales = dict({
    'en_US': en.locale,
    'fr_FR': fr.locale,
})

def t(key, lang):
    """
    Given a text key and a language it returns the corresponding text for the language.

    :param key: a string that identifies the desired piece of text.
    :param lang: the ISO code for the language locale.

    :return: the desired text in the given language.
    """
    locale = locales.get(lang)

    if not locale:
        raise Exception(f'Locale "{lang}" not found')
    return locale.get(key, '')
