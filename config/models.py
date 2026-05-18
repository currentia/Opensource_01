from django.db import models

class User(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    user_pw = models.CharField(max_length=100)

    def __str__(self):
        return self.user_id