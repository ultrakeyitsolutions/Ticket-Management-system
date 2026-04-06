"""
Template context processors for user profile data
"""

def user_profile_context(request):
    """
    Add user profile information to all templates
    """
    if request.user.is_authenticated:
        try:
            user_profile = request.user.userprofile
            return {
                'user_profile': user_profile,
            }
        except AttributeError:
            # User profile doesn't exist
            return {'user_profile': None}
    else:
        return {'user_profile': None}
