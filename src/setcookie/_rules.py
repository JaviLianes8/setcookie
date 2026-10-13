"""Rules shared by the builder, strict mode and the storage model."""

from __future__ import annotations

from ._chars import ascii_lower


def prefix_problem(name: str, *, secure: bool, has_domain: bool, path: str | None) -> str | None:
    """Explain how a name prefix rule (section 5.7 steps 20 and 21) is broken, or None.

    Prefixes are matched case-insensitively, as user agents do (section 5.4).
    """
    folded = ascii_lower(name)
    if folded.startswith("__secure-") and not secure:
        return "a __Secure- cookie needs the Secure attribute"
    if folded.startswith("__host-"):
        if not secure:
            return "a __Host- cookie needs the Secure attribute"
        if has_domain:
            return "a __Host- cookie must not have a Domain attribute"
        if path != "/":
            return "a __Host- cookie needs Path=/"
    return None


def secure_problem(*, same_site: str | None, partitioned: bool, secure: bool) -> str | None:
    """Explain why SameSite=None or Partitioned is refused without Secure, or None."""
    if secure:
        return None
    if same_site == "None":
        return "SameSite=None needs the Secure attribute"
    if partitioned:
        return "Partitioned needs the Secure attribute"
    return None
