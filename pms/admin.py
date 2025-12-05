from django.contrib import admin

from .models import Room, Booking, Customer, RoomType

admin.site.register([Room, Booking, Customer, RoomType])
