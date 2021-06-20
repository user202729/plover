"""
In many steno theories, there may be multiple ways to stroke a certain word.
By providing the user with suggestions while they are writing, this may help
them learn briefs or otherwise shorter outlines for the same input, which leads
to faster, more fluent writing. This module handles providing suggestions.
"""

import collections

from plover.steno import sort_steno_strokes


Suggestion = collections.namedtuple('Suggestion', 'text steno_list')
"""
An object representing a possible suggestion.

Attributes:
    text (str): The translation to get possible suggestion strokes for.
    steno_list (List[Tuple[str, ...]]):
        The list of outlines that translate to :attr:`text`, provided in order
        of the number of strokes.
"""


class Suggestions:
    """
    An object that handles finding suggestions using the given dictionary.

    Attributes:
        dictionary (plover.steno_dictionary.StenoDictionaryCollection):
            A :class:`~plover.steno_dictionary.StenoDictionaryCollection`
            containing all of the dictionaries to look up translations from.
    """

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def find(self, translation):
        # type: (str) -> List[Suggestion]
        """
        Returns the list of suggestions for the word provided in `translation`,
        and other words similar to it. Each item in the list is a
        :class:`Suggestion` containing possible outlines for a single word.
        """
        suggestions = []

        mods = [
            '%s',  # Same
            '{^%s}',  # Prefix
            '{^}%s',
            '{^%s^}',  # Infix
            '{^}%s{^}',
            '{%s^}',  # Suffix
            '%s{^}',
            '{&%s}',  # Fingerspell
            '{#%s}',  # Command
        ]

        possible_translations = {translation}

        # Only strip spaces, so patterns with \n or \t are correctly handled.
        stripped_translation = translation.strip(' ')
        if stripped_translation and stripped_translation != translation:
            possible_translations.add(stripped_translation)

        lowercase_translation = translation.lower()
        if lowercase_translation != translation:
            possible_translations.add(lowercase_translation)

        similar_words = self.dictionary.casereverse_lookup(translation.lower())
        if similar_words:
            possible_translations |= set(similar_words)

        for t in possible_translations:
            for modded_translation in [mod % t for mod in mods]:
                strokes_list = self.dictionary.reverse_lookup(modded_translation)
                if not strokes_list:
                    continue
                strokes_list = sort_steno_strokes(strokes_list)
                suggestion = Suggestion(modded_translation, strokes_list)
                suggestions.append(suggestion)

        return suggestions
