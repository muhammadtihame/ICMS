"""
Test script to verify media file serving works correctly
"""
import os
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User


class MediaServingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_media_serving(self):
        """Test that media files are served correctly"""
        # Test serving default.png
        response = self.client.get('/media/default.png')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        
    def test_profile_picture_upload(self):
        """Test profile picture upload and serving"""
        # Login the user
        self.client.login(username='testuser', password='testpass123')
        
        # Create a simple test image
        test_image = SimpleUploadedFile(
            "test_image.png",
            b"fake image content",
            content_type="image/png"
        )
        
        # Update profile with picture
        response = self.client.post('/accounts/setting/', {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'picture': test_image,
        })
        
        # Check if the profile was updated
        self.user.refresh_from_db()
        if self.user.picture:
            # Test serving the uploaded picture
            picture_url = self.user.get_picture()
            response = self.client.get(picture_url)
            self.assertEqual(response.status_code, 200)
