import re
from abc import ABC, abstractmethod

_COMMENT_RES = [
    re.compile(r"/\*.*?\*/", re.S),   # /* block */
    re.compile(r"//[^\n]*"),          # // line comment
    re.compile(r"#[^\n]*"),           # # line comment (Python)
]
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+|\S")
_KEYWORDS = {
    "if", "else", "elif", "for", "while", "return", "def", "class", "import", "from",
    "try", "except", "finally", "with", "as", "in", "not", "and", "or", "is",
    "None", "True", "False", "null", "true", "false", "public", "private", "static",
    "void", "int", "float", "double", "string", "new", "this", "self", "function",
    "const", "let", "var", "break", "continue", "switch", "case", "default", "throw",
}


class ISimilarityStrategy(ABC):
    """חוזה לאלגוריתם השוואת דמיון בין קבצי קוד (Strategy Pattern)."""

    @abstractmethod
    def fingerprint(self, sources: dict[str, str]) -> set[int]:
        pass

    @abstractmethod
    def score(self, a: set[int], b: set[int]) -> float:
        pass


class TokenShingleSimilarity(ISimilarityStrategy):
    """מנרמל טוקנים ומשווה קבוצות k-grams בשיטת Dice (0.0 עד 1.0)."""

    def __init__(self, k: int = 6):
        self.k = k

    def _normalize(self, code: str) -> list[str]:
        for rx in _COMMENT_RES:
            code = rx.sub(" ", code)
        tokens = []
        for t in _TOKEN_RE.findall(code):
            if t in _KEYWORDS:
                tokens.append(t)
            elif t[0].isdigit():
                tokens.append("NUM")
            elif t[0].isascii() and (t[0].isalpha() or t[0] == "_"):
                tokens.append("ID")  # שינוי שם משתנים לא משנה את הטביעה
            else:
                tokens.append(t)
        return tokens

    def fingerprint(self, sources: dict[str, str]) -> set[int]:
        # hash() תקף לתהליך הנוכחי בלבד, וזה מספיק כי ההשוואה נעשית באותו תהליך
        fp: set[int] = set()
        for code in sources.values():
            toks = self._normalize(code)
            for i in range(len(toks) - self.k + 1):
                fp.add(hash(tuple(toks[i:i + self.k])))
        return fp

    def score(self, a: set[int], b: set[int]) -> float:
        if not a or not b:
            return 0.0
        return 2 * len(a & b) / (len(a) + len(b))