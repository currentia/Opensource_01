from django.db import models

class User(models.Model):
    user_id = models.CharField(max_length=30, unique=True)
    user_pw = models.CharField(max_length=30)

    def __str__(self):
        return self.user_id


class Friend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend')

    def __str__(self):
        return f"{self.user.user_id} -> {self.friend.user_id}"