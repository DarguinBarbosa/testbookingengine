from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import Room, Room_type, Booking, Customer
from datetime import date, timedelta

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class RoomsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rt = Room_type.objects.create(name="Single", price=50, max_guests=1)
        self.r1 = Room.objects.create(name="Room 101", room_type=self.rt, description="Desc")
        self.r2 = Room.objects.create(name="Room 102", room_type=self.rt, description="Desc")
        self.r3 = Room.objects.create(name="Suite 201", room_type=self.rt, description="Desc")

    def test_filter_rooms(self):
        # Test exact match logic: "1" should find "Room 101" but NOT "Room 2.1"
        Room.objects.create(name="Room 2.1", room_type=self.rt, description="Desc")
        
        response = self.client.get(reverse('rooms'), {'search': '1'})
        self.assertEqual(response.status_code, 200)
        
        found_names = [r['name'] for r in response.context['rooms']]
        self.assertIn("Room 101", found_names)
        self.assertIn("Room 102", found_names)
        self.assertNotIn("Room 2.1", found_names)
        self.assertNotIn("Suite 201", found_names)

    def test_filter_rooms_case_insensitive(self):
        response = self.client.get(reverse('rooms'), {'search': 'room'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['rooms']), 2)

    def test_no_filter(self):
        response = self.client.get(reverse('rooms'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['rooms']), 3)

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rt = Room_type.objects.create(name="Single", price=50, max_guests=1)
        self.r1 = Room.objects.create(name="R1", room_type=self.rt, description="D")
        self.r2 = Room.objects.create(name="R2", room_type=self.rt, description="D")
        self.customer = Customer.objects.create(name="John", email="j@j.com", phone="123")

    def test_occupancy_percentage(self):
        today = date.today()
        # Active booking
        Booking.objects.create(
            room=self.r1, customer=self.customer,
            checkin=today, checkout=today + timedelta(days=1),
            state="NEW", total=50, guests=1, code="111"
        )
        # Future booking (not active)
        Booking.objects.create(
            room=self.r2, customer=self.customer,
            checkin=today + timedelta(days=10), checkout=today + timedelta(days=11),
            state="NEW", total=50, guests=1, code="222"
        )
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        # 1 active booking / 2 rooms = 50%
        self.assertEqual(response.context['dashboard']['occupancy_percentage'], 50.0)

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class EditBookingDatesViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rt = Room_type.objects.create(name="Single", price=50, max_guests=1)
        self.r1 = Room.objects.create(name="R1", room_type=self.rt, description="D")
        self.customer = Customer.objects.create(name="John", email="j@j.com", phone="123")
        self.today = date.today()
        self.booking = Booking.objects.create(
            room=self.r1, customer=self.customer,
            checkin=self.today, checkout=self.today + timedelta(days=2),
            state="NEW", total=100, guests=1, code="ABC"
        )

    def test_edit_dates_success(self):
        new_checkin = self.today + timedelta(days=5)
        new_checkout = self.today + timedelta(days=7)
        response = self.client.post(reverse('edit_booking_dates', args=[self.booking.id]), {
            'checkin': new_checkin.strftime('%Y-%m-%d'),
            'checkout': new_checkout.strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 302) # Redirect
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkin, new_checkin)
        self.assertEqual(self.booking.checkout, new_checkout)

    def test_edit_dates_invalid_range(self):
        response = self.client.post(reverse('edit_booking_dates', args=[self.booking.id]), {
            'checkin': (self.today + timedelta(days=5)).strftime('%Y-%m-%d'),
            'checkout': (self.today + timedelta(days=4)).strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("La fecha de salida debe ser posterior", response.context['error'])

    def test_edit_dates_overlap(self):
        # Create another booking that overlaps with the desired new dates
        Booking.objects.create(
            room=self.r1, customer=self.customer,
            checkin=self.today + timedelta(days=10), checkout=self.today + timedelta(days=12),
            state="NEW", total=100, guests=1, code="XYZ"
        )
        
        # Try to move the first booking to overlap with the second one
        response = self.client.post(reverse('edit_booking_dates', args=[self.booking.id]), {
            'checkin': (self.today + timedelta(days=9)).strftime('%Y-%m-%d'),
            'checkout': (self.today + timedelta(days=11)).strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("No hay disponibilidad", response.context['error'])