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
import pandas as pd
import json
from planner.services.tomorrow import get_today_weather_and_air

# Create your views here.
@login_required
def home(request):
    profile = request.user.userprofile
    city = "Dhaka"   # or profile.city if user has city saved in profile
    data = get_today_weather_and_air(city)

    # === Load dengue CSV for charts ===
    df = pd.read_csv("planner/data/dengue_stats.csv")

    # Aggregate total/male/female/dead by location
    agg_df = df.groupby("location_name").sum().reset_index()
    locations = agg_df["location_name"].tolist()
    total_cases = agg_df["total"].tolist()
    male_cases = agg_df["male"].tolist()
    female_cases = agg_df["female"].tolist()
    dead_cases = agg_df["dead"].tolist()

    # Gender distribution overall
    gender_distribution = [sum(male_cases), sum(female_cases)]

    # Bubble/Scatter chart data
    latitudes = agg_df["latitude"].tolist()
    longitudes = agg_df["longitude"].tolist()
    bubble_sizes = [x / 10 for x in total_cases]  # scale down for visibility

    # Pass everything as JSON for Chart.js
    context = {
        'profile': profile,
        'data': data,
        'city': city,
        'locations_json': json.dumps(locations),
        'total_cases_json': json.dumps(total_cases),
        'male_cases_json': json.dumps(male_cases),
        'female_cases_json': json.dumps(female_cases),
        'dead_cases_json': json.dumps(dead_cases),
        'gender_distribution_json': json.dumps(gender_distribution),
        'latitudes_json': json.dumps(latitudes),
        'longitudes_json': json.dumps(longitudes),
        'bubble_sizes_json': json.dumps(bubble_sizes),
    }

    return render(request, 'home.html', context)

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
        points.append([r.longitude, r.latitude, intensity])

    return JsonResponse({"points": points, "max_total": max_total})



from django.views.decorators.cache import cache_page
from .services.tomorrow import get_today_weather_and_air

@cache_page(60 * 15)  # cache for 15 minutes to save API calls
def weather_today(request):
    city = request.GET.get("city", "Dhaka")
    data = get_today_weather_and_air(city)
    return render(request, "weather_today.html", {"data": data, "city": city})
