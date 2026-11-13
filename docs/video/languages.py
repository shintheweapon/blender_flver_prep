"""
What differs between the video's languages: the paper it is read from, how
fast it is spoken before audio exists, and its fonts.

A language is added here, by its code as in ``script.<code>.md``; the rest of
the pipeline asks this table rather than holding English values.
"""

from collections import namedtuple

Language = namedtuple("Language", "paper rate page_font subtitle_fonts words subtitle_sentences")
Language.__doc__ = """
One language of the video.

Parameters
----------
paper : str
    The paper's file name in ``docs/paper/``.
rate : float
    Spoken units a minute, for timing before audio exists: words, with each
    CJK character counted as one unit (``script.Segment.words``).
page_font : str
    The CSS font stack of the pages.
subtitle_fonts : tuple of str
    The families the subtitles may use, the first one installed winning.
words : str or None
    The word splitter for subtitle lines: ``"jieba"`` for Chinese, None where
    lines break at spaces.
subtitle_sentences : bool
    Each subtitle changes at a sentence end (``subtitles.sentence_groups``),
    where the narration pauses; True for English. Chinese subtitles fill each
    pair of lines in turn and change at the pauses found near them.
"""

LATIN_FONT = '"Segoe UI", -apple-system, Helvetica, Arial'

LANGUAGES = {
    "en": Language("ER_NORMAL_MAPS.md", 145, f"{LATIN_FONT}, sans-serif", ("Segoe UI",), None, True),
    "zh-CN": Language("ER_NORMAL_MAPS.zh-CN.md", 260,
                      f'{LATIN_FONT}, "Source Han Sans SC", "Noto Sans SC", sans-serif',
                      ("Source Han Sans SC", "Noto Sans SC"), "jieba", False),
}

# The CJK families a Chinese page lists, in order, for figures to lead with
CJK_FONTS = ('"Source Han Sans SC"', '"Noto Sans SC"')


def language(code):
    """
    The settings of a language.

    Parameters
    ----------
    code : str
        ``en`` or ``zh-CN``.

    Returns
    -------
    Language

    Raises
    ------
    KeyError
        For a language the video has no settings for.
    """
    if code not in LANGUAGES:
        raise KeyError(f"no video settings for language {code!r}; known: {', '.join(LANGUAGES)}")
    return LANGUAGES[code]
