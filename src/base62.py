"""base62 인코딩: 0 이상의 정수 <-> 0-9, a-z, A-Z 순서의 62진법 문자열."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def encode(n):
    """0 이상의 정수 n을 base62 문자열로 바꾼다. encode(0) == "0"."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n은 정수여야 합니다")
    if n < 0:
        raise ValueError("n은 0 이상이어야 합니다")
    if n == 0:
        return ALPHABET[0]
    digits = []
    while n > 0:
        n, r = divmod(n, BASE)
        digits.append(ALPHABET[r])
    return "".join(reversed(digits))


def decode(s):
    """base62 문자열 s를 정수로 되돌린다. encode의 역변환."""
    if not isinstance(s, str) or s == "":
        raise ValueError("빈 문자열은 디코딩할 수 없습니다")
    n = 0
    for ch in s:
        i = ALPHABET.find(ch)
        if i < 0:
            raise ValueError(f"base62 문자가 아닙니다: {ch!r}")
        n = n * BASE + i
    return n
