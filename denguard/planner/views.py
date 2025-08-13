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
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')  # 🔁 redirect to your homepage/dashboard
        else:
            messages.error(request, 'Invalid username or password.')

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


# planner/views.py
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Max
from .models import DengueStat

def heatmap_view(request):
    # No need to filter by year, just render the template
    return render(request, "heatmap.html")

def heatmap_data_api(request):
    qs = DengueStat.objects.all()  # Get all records

    max_total = qs.aggregate(m=Max("total"))["m"] or 1
    points = []
    for r in qs:
        if r.latitude is None or r.longitude is None:
            continue
        intensity = round(r.total / max_total, 3)  # normalize 0..1
        points.append([r.latitude, r.longitude, intensity])

    return JsonResponse({"points": points, "max_total": max_total})
