from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ProfileForm, ProfilePictureForm
from .models import Profile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('home')

    return render(request, 'expensetracker/login.html', {'form': form})


@login_required(login_url='login')
def home(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    form = ProfileForm(request.POST or None, instance=request.user)
    picture_form = ProfilePictureForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
    )
    if request.method == 'POST' and form.is_valid() and picture_form.is_valid():
        old_image = profile.image
        form.save()
        picture_form.save()
        if old_image and (not profile.image or old_image.name != profile.image.name):
            old_image.delete(save=False)
        messages.success(request, 'Your profile has been updated.')
        return redirect('home')
    return render(request, 'expensetracker/home.html', {
        'form': form,
        'picture_form': picture_form,
        'profile': profile,
    })


def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')
    return render(request, 'expensetracker/register.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')