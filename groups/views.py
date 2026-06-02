from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import Group


@login_required
def group_list(request):

    if request.method == "POST":

        name = request.POST.get("name")
        target_budget = request.POST.get("target_budget")

        if name and target_budget:

            Group.objects.create(
                name=name,
                target_budget=target_budget,
                owner=request.user
            )

            return redirect("groups:group_list")

    groups = Group.objects.filter(
    owner=request.user
)

    context = {
        "groups": groups
    }

    return render(
        request,
        "groups/group_list.html",
        context
    )
def delete_group(request, group_id):

    group = Group.objects.get(id=group_id)

    group.delete()

    return redirect("groups:group_list")