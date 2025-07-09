from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, authenticate
from users.forms import SignupForm
from users.models import UserProfile
from django.contrib.auth import get_backends


# Create your views here.
@login_required
def home(request):
    profile = request.user.userprofile
    return render(request, 'home.html', {'profile': profile})

@login_required
def about(request):
    return render(request, 'about.html')

@login_required
def contact(request):
    return render(request, 'contact.html')

def login_view(request):
    if request.method == 'POST':
        # Handle login logic here
        pass
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # ✅ Set backend manually (required when multiple backends like allauth are used)
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

            login(request, user)
            messages.success(request, "Signup successful. Welcome!")
            return redirect('home')  # or any page you want
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})