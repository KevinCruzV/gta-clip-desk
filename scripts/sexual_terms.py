"""Sexual vocabulary that must never appear as clear text in burned captions, hooks or post captions (EN/FR/ES).
The clip itself may be about it: only the text we add is masked with ***."""
import re

SEXUAL = re.compile(
    r"\b(sex\w*|porn\w*|nsfw|nud(?:e|es|ity)|naked|peg(?:ging|ged|ger)|blow\s?jobs?|hand\s?jobs?|dildos?|vibrators?|"
    r"orgasm\w*|cum(?:ming|shot)?|horny|boobs?|tits?|titties|nipples?|penis\w*|vagina\w*|genitals?|masturbat\w*|"
    r"anal|erotic\w*|stripper\w*|strip\s?club|onlyfans|hentai|fetish\w*|threesome|orgy|kinky|"
    r"chatte|seins|nichons?|branl\w*|enculer?|sucer|"
    r"sexo|polla|co[ñn]o|culo|tetas?|follar|puta|pene|desnud\w*)\b",
    re.I,
)


def mask_sexual(s):
    return SEXUAL.sub("***", s)
