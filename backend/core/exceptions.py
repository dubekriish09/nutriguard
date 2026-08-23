class UserProfileIncompleteError(Exception):
    pass

class FoodPoolEmptyError(Exception):
    """Raised when no foods pass the safety filter for a user.
    This can happen with very restrictive combined profiles."""
    pass

class MealCompositionError(Exception):
    pass
