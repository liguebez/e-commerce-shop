from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password



class EmailAuthBackend(BaseBackend):
    
     def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=username)
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            user_model().set_password(password or make_password(None))
            return None
        if user.check_password(password):
            return user
        return None
        
     def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
        
