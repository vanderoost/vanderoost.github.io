"""The platforms an article is cross-posted to.

Medium is deliberately absent. It stopped issuing integration tokens, so there
is no way to get credentials for a new setup, and more decisively its API has
no update endpoint at all -- only POST /users/{id}/posts. An article that can
be created but never corrected cannot meet the one requirement this package is
built around, which is that running it twice fixes the remote rather than
duplicating it. If a token ever turns up, the honest shape is create-once with
update() logging a skip; the Platform protocol already allows that.

Substack is absent for a different reason: its posts always name themselves as
canonical, so a copy there would compete with the original in search results
rather than point at it.
"""

from .devto import DevTo
from .hashnode import Hashnode

ADAPTERS = {adapter.name: adapter for adapter in (DevTo(), Hashnode())}
