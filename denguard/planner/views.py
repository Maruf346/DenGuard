from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

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

def signup(request):
    if request.method == 'POST':
        # Handle registration logic here
        pass
    return render(request, 'signup.html')