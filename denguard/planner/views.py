from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login
from users.forms import SignupForm


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
            login(request, user)
            messages.success(request, "Signup successful. Welcome!")
            return redirect('home')  # change to your home/dashboard
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})