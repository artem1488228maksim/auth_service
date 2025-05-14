def activate_user(strategy, details,user=None,*args, **kwargs):
    if user and not user.is_active:
        user.is_active = True
        user.save()
