from django.contrib.auth.tokens import PasswordResetTokenGenerator

class UserPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for user password reset, extending Django's default.
    """
    pass

password_reset_token = UserPasswordResetTokenGenerator()