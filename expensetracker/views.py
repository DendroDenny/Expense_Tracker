from django.shortcuts import redirect, render
from django.contrib.auth.forms import UserCreationForm


def home(request):
    return render(request, 'expensetracker/login.html')


def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')
    return render(request, 'expensetracker/register.html', {'form': form})