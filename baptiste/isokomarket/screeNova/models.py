from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinLengthValidator, RegexValidator

# ------------------ PROFILE ------------------

class Profile(models.Model):
    USER_TYPE = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPE)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Ensure every new user has a Profile (defaults to buyer)."""
    if created:
        Profile.objects.create(user=instance, user_type='buyer')


# ------------------ CATEGORY ------------------

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# ------------------ PRODUCT ------------------ (UPDATED WITH DETAILED FIELDS)

class Product(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    # Basic info (shown on homepage)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    
    # Detailed info (shown only on product detail page)
    description = models.TextField()
    stock = models.IntegerField()
    
    # NEW DETAILED FIELDS (Optional - can be blank)
    brand = models.CharField(max_length=100, blank=True, null=True)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional images
    image2 = models.ImageField(upload_to='products/', null=True, blank=True)
    image3 = models.ImageField(upload_to='products/', null=True, blank=True)
    
    # Specifications (JSON field for flexible specs)
    specifications = models.JSONField(default=dict, blank=True)
    
    # Additional info
    warranty = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=200, blank=True, null=True)
    country_of_origin = models.CharField(max_length=100, blank=True, null=True)
    
    # Shipping info
    shipping_weight = models.CharField(max_length=50, blank=True, null=True)
    shipping_dimensions = models.CharField(max_length=100, blank=True, null=True)
    
    # Features (one per line)
    features = models.TextField(blank=True, null=True, help_text="One feature per line")
    
    # Meta data
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['price']),
            models.Index(fields=['category', 'stock']),
        ]

    def __str__(self):
        return self.name
    
    def get_features_list(self):
        """Convert features text to list"""
        if self.features:
            return [f.strip() for f in self.features.split('\n') if f.strip()]
        return []
    
    def get_all_images(self):
        """Return list of all available images"""
        images = []
        if self.image:
            images.append(self.image)
        if self.image2:
            images.append(self.image2)
        if self.image3:
            images.append(self.image3)
        return images


# ------------------ CART ------------------

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)


# ------------------ ORDER ------------------

class Order(models.Model):
    # Payment method choices
    PAYMENT_METHODS = [
        ('Credit Card', 'Credit Card'),
        ('Mobile Money', 'Mobile Money'),
        ('Cash on Delivery', 'Cash on Delivery'),
    ]
    
    # Order status choices
    ORDER_STATUS = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    # ========== EXISTING FIELDS ==========
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="Pending", choices=ORDER_STATUS)
    payment_method = models.CharField(max_length=50, blank=True, null=True, choices=PAYMENT_METHODS)
    
    # ========== NEW BUYER INFORMATION FIELDS ==========
    buyer_fullname = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(2, "Full name must be at least 2 characters")],
        help_text="Buyer's complete name as provided during checkout",
        default=''  # Added default for existing rows
    )
    
    delivery_location = models.TextField(
        validators=[MinLengthValidator(10, "Delivery location must be detailed")],
        help_text="Complete delivery address",
        default=''  # Added default for existing rows
    )
    
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9+\-\s()]{10,20}$',
                message='Enter a valid phone number'
            )
        ],
        help_text="Contact phone for delivery coordination"
    )
    
    delivery_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions for delivery"
    )
    
    # ========== ADDITIONAL USEFUL FIELDS ==========
    # Total amount (useful since product price might change)
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Total order amount"
    )
    
    # Product snapshot to preserve price at time of order
    product_price_at_order = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Product price at time of order"
    )
    
    # Delivery tracking
    delivered_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Delivery completion timestamp"
    )
    
    # Last update timestamp
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )

    class Meta:
        ordering = ['-ordered_at']
        indexes = [
            models.Index(fields=['buyer_fullname']),
            models.Index(fields=['status']),
            models.Index(fields=['-ordered_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.buyer_fullname or self.buyer.username}"

    def save(self, *args, **kwargs):
        # Automatically calculate total amount if not set
        if not self.total_amount and self.product_price_at_order:
            self.total_amount = self.product_price_at_order * self.quantity
        elif not self.total_amount and self.product:
            self.total_amount = self.product.price * self.quantity
            self.product_price_at_order = self.product.price
        
        # If buyer_fullname is not provided, use buyer's username as fallback
        if not self.buyer_fullname and self.buyer:
            self.buyer_fullname = self.buyer.get_full_name() or self.buyer.username
        
        super().save(*args, **kwargs)

    def get_delivery_address_display(self):
        """Return formatted delivery address"""
        address = self.delivery_location
        if self.delivery_instructions:
            address += f"\nInstructions: {self.delivery_instructions}"
        return address


# ------------------ CONTACT MESSAGE ------------------

class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} <{self.email}>"
    
    PAYMENT_METHODS = [
    ('Credit Card', 'Credit Card'),
    ('Mobile Money', 'Mobile Money'),
    ('Bank Transfer', 'Bank Transfer'),  # ✅ ADD THIS LINE
    ('Cash on Delivery', 'Cash on Delivery'),
]
    # Add this to your models.py

class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    image = models.ImageField(upload_to='review_images/', blank=True, null=True)
    helpful_count = models.IntegerField(default=0)
    is_verified_purchase = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['product', 'user']  # One review per user per product
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}★"
    
    