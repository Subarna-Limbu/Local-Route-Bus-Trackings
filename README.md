# Smart Transport System

## Overview
This project is a Smart Transport System built with Django. It provides features such as live bus tracking, user and driver registration, and route management. The system uses real-time technologies to allow users to track buses on a map as they move.

## Technologies Used
- **Django**: Main backend web framework.
- **Django Channels**: For real-time WebSocket communication.
- **SQLite**: Default database for development.
- **Leaflet.js**: For interactive maps on the frontend.
- **WebSockets**: For live location updates between server and clients.
- **HTML/CSS/JavaScript**: For frontend templates and interactivity.

## Features
- User and driver registration/login
- Live bus tracking on a map
- Real-time location updates using WebSockets
- Route management and shortest path calculation (Dijkstra's algorithm)

## How to Run the Project

### 1. Clone the Repository
git clone <repo-url>
cd smart_transport

### 2. Create and Activate a Virtual Environment 
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate


### 3. Install Dependencies
pip install -r requirements.txt


### 4. Apply Migrations
python manage.py migrate


### 5. Run the Development Server
python manage.py runserver
daphne smart_transport.asgi:application

### 6. Access the Application
Open your browser and go to [http://localhost:8000/](http://localhost:8000/)

## Live Tracking
- Drivers start tracking from their dashboard.
- Users can view live bus locations on the map (uses Leaflet.js and WebSockets).