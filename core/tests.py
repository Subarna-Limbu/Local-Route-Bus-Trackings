from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Driver, Bus, BusRoute, PickupRequest


class PickupNotificationFlowTest(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='passenger1', password='pass')
		self.driver_user = User.objects.create_user(username='driver1', password='pass')
		self.driver = Driver.objects.create(user=self.driver_user, phone='123', vehicle_number='V1', verified=True)
		self.bus = Bus.objects.create(number_plate='BUS1', total_seats=20, driver=self.driver)
		self.client = Client()

	def test_pickup_and_driver_notification_includes_username(self):
		# passenger sends pickup via HTTP
		self.client.login(username='passenger1', password='pass')
		resp = self.client.post('/api/send_pickup/', {'bus_id': self.bus.id, 'stop': 'balkhu', 'message': 'wait about 5 min.'})
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertEqual(data.get('status'), 'success')

		# driver fetches notifications
		self.client.login(username='driver1', password='pass')
		resp2 = self.client.get('/driver/notifications/')
		self.assertEqual(resp2.status_code, 200)
		d2 = resp2.json()
		self.assertIn('unread_count', d2)
		recent = d2.get('recent', [])
		# ensure username appears in recent payload
		self.assertTrue(any((r.get('user') == 'passenger1') for r in recent))
