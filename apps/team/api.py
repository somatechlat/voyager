"""Team API — re-export of the combined router from views.

All endpoints are defined in the views subpackage and assembled here
for registration with the main Django Ninja API.
"""

from apps.team.views import router  # noqa: F401
