def driver_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('driver_register')
        user = User.objects.create_user(
            username=username, password=password, email=email)
        # Create Driver profile for this user
        from .models import Driver
        Driver.objects.create(user=user)
        messages.success(request, 'Driver registration successful.')
        return redirect('driver_login')
    return render(request, 'registration/driver_register.html')
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import BusRoute, Driver, Bus, Seat


def homepage(request):
    # Collect stops from all bus routes
    stops = set()
    routes = BusRoute.objects.filter(is_active=True, bus__isnull=False)
    for route in routes:
        stops.update(route.get_stops_list())
    stops = sorted(list(stops))

    buses_info = []
    pickup = request.GET.get('pickup', '').strip().lower() if 'pickup' in request.GET else ''
    destination = request.GET.get('destination', '').strip().lower() if 'destination' in request.GET else ''
    matching_routes = []
    if pickup and destination:
        for route in routes:
            stops_list = [stop.strip().lower() for stop in route.get_stops_list()]
            if pickup in stops_list and destination in stops_list:
                matching_routes.append(route)

        import math
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        def get_stop_coords(stop_name):
            stop_coords = {
                'kathmandu': (27.7172, 85.3240),
                'lalitpur': (27.6644, 85.3188),
                'bhaktapur': (27.6710, 85.4298),
            }
            return stop_coords.get(stop_name.lower())

        for route in matching_routes:
            bus = route.bus
            available_seats = bus.seats.filter(is_available=True).count() if bus else 0
            eta = None
            bus_lat = getattr(bus, 'current_lat', None)
            bus_lng = getattr(bus, 'current_lng', None)
            has_live_location = bus and bus_lat is not None and bus_lng is not None
            if has_live_location:
                pickup_coords = get_stop_coords(pickup)
                if pickup_coords:
                    distance_km = haversine(bus_lat, bus_lng, pickup_coords[0], pickup_coords[1])
                    avg_speed_kmh = 25
                    eta = int((distance_km / avg_speed_kmh) * 60)
                    if eta < 1:
                        eta = 1
                else:
                    import random
                    eta = random.randint(2, 15)
            else:
                import random
                eta = random.randint(2, 15)
            buses_info.append({
                'route': route,
                'bus': bus,
                'eta': eta,
                'available_seats': available_seats,
            })
    context = {
        'stops': stops,
        'buses_info': buses_info,
        'pickup': pickup,
        'destination': destination,
    }
    return render(request, 'user/homepage.html', context)


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
    route = driver.routes.first()
    bus = None
    seats = []
    last_row_start = None
    seat_grid_columns = []
    if route:
        if request.method == 'POST' and not route.bus:
            # Create bus and seats
            total_seats = int(request.POST.get('total_seats', 25))
            number_plate = request.POST.get('number_plate')
            bus = Bus.objects.create(number_plate=number_plate, total_seats=total_seats, driver=driver)
            route.bus = bus
            route.save()
            bus.create_seats()
        if route.bus:
            bus = route.bus
            bus.create_seats()
            seats = list(bus.seats.order_by('seat_number').all())
            last_row_start = bus.total_seats - 5 if bus.total_seats >= 5 else 0
            for idx, seat in enumerate(seats):
                if idx < last_row_start:
                    seat_grid_columns.append((seat, (idx % 4) + 1))
                else:
                    seat_grid_columns.append((seat, idx - last_row_start + 1))
    context = {
        'driver': driver,
        'route': route,
        'bus': bus,
        'seats': seats,
        'last_row_start': last_row_start,
        'seat_grid_columns': seat_grid_columns,
    }
    return render(request, 'driver/dashboard.html', context)


@csrf_exempt
@login_required
def toggle_seat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            seat_id = data.get('seat_id')
            seat = Seat.objects.get(id=seat_id)
            seat.is_available = not seat.is_available
            seat.save()
            return JsonResponse({'status': 'success', 'is_available': seat.is_available})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)})
    return JsonResponse({'status': 'error', 'error': 'Invalid request'})


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
    # Display live tracking and seat info for the selected bus.
    from .models import Bus
    bus = Bus.objects.filter(id=bus_id).first()
    seats = list(bus.seats.order_by('seat_number').all()) if bus else []
    last_row_start = bus.total_seats - 5 if bus and bus.total_seats >= 5 else 0
    seat_grid_columns = []
    for idx, seat in enumerate(seats):
        if idx < last_row_start:
            seat_grid_columns.append((seat, (idx % 4) + 1))
        else:
            seat_grid_columns.append((seat, idx - last_row_start + 1))
    return render(request, 'user/tracking.html', {
        'bus_id': bus_id,
        'bus': bus,
        'seats': seats,
        'last_row_start': last_row_start,
        'seat_grid_columns': seat_grid_columns,
    })
