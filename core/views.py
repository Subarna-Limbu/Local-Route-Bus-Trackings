import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import BusRoute, Driver


def homepage(request):
    # Collect stops from all bus routes
    stops = set()
    routes = BusRoute.objects.all()
    for route in routes:
        stops.update(route.get_stops_list())
    stops = sorted(list(stops))

    if request.method == 'GET' and 'pickup' in request.GET and 'destination' in request.GET:
        pickup = request.GET.get('pickup', '').strip().lower()
        destination = request.GET.get('destination', '').strip().lower()
        matching_routes = []
        for route in routes:
            stops_list = [stop.strip().lower() for stop in route.get_stops_list()]
            # Match if both stops are present, regardless of order, case, or whitespace.
            if pickup in stops_list and destination in stops_list:
                matching_routes.append(route)
        return render(request, 'user/homepage.html', {
            'stops': stops,
            'routes': matching_routes,
            'pickup': request.GET.get('pickup', ''),
            'destination': request.GET.get('destination', '')
        })
    return render(request, 'user/homepage.html', {'stops': stops})


def driver_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        vehicle_number = request.POST.get('vehicle_number')
        email = request.POST.get('email')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('driver_register')
        user = User.objects.create_user(
            username=username, password=password, email=email)
        # Create a driver profile linked to this user.
        Driver.objects.create(user=user, phone=phone,
                              vehicle_number=vehicle_number)
        messages.success(
            request, 'Registration successful, pending admin verification.')
        return redirect('driver_login')
    return render(request, 'registration/driver_register.html')


def driver_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if hasattr(user, 'driver_profile'):
                login(request, user)
                return redirect('driver_dashboard')
            else:
                messages.error(request, 'Not registered as a driver.')
                return redirect('driver_login')
        messages.error(request, 'Invalid credentials.')
        return redirect('driver_login')
    return render(request, 'registration/driver_login.html')


@login_required
def driver_dashboard(request):
    if not hasattr(request.user, 'driver_profile'):
        return redirect('homepage')
    driver = request.user.driver_profile
    # For simplicity, assume one route per driver.
    route = driver.routes.first()
    context = {
        'driver': driver,
        'route': route,
    }
    return render(request, 'driver/dashboard.html', context)


def update_location(request):
    # This view is used via AJAX to update driver's location.
    if request.method == 'POST' and request.user.is_authenticated and hasattr(request.user, 'driver_profile'):
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        driver = request.user.driver_profile
        driver.current_lat = lat
        driver.current_lng = lng
        driver.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('homepage')
        messages.error(request, 'Invalid credentials.')
        return redirect('user_login')
    return render(request, 'registration/user_login.html')


def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('user_register')
        User.objects.create_user(
            username=username, password=password, email=email)
        messages.success(request, 'Registration successful.')
        return redirect('user_login')
    return render(request, 'registration/user_register.html')


def track_bus(request, bus_id):
    # Display live tracking for the selected bus.
    return render(request, 'user/tracking.html', {'bus_id': bus_id})
