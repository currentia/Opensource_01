from django.db import models
from django.conf import settings

class Group(models.Model):
    name = models.CharField(max_length=50)
    target_budget = models.IntegerField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name
class GroupMember(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )