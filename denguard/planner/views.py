from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def login_view(request):
    if request.method == 'POST':
        # Handle login logic here
        pass
    return render(request, 'login.html')

def logout_view(request):
    # Handle logout logic here
    return render(request, 'logout.html')

def signup(request):
    if request.method == 'POST':
        # Handle registration logic here
        pass
    return render(request, 'signup.html')