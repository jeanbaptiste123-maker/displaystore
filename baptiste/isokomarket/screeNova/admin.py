from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, Category, Product, Cart, Order, ContactMessage

# Register your basic models
admin.site.register(Profile)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(ContactMessage)

# Custom Order Admin with all the features
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Display these fields in the list view
    list_display = [
        'id',
        'buyer_fullname',  # Show buyer name
        'buyer_username',   # Show username as fallback
        'product_name',
        'quantity',
        'total_amount_display',
        'delivery_location_short',
        'contact_phone_display',
        'status_colored',
        'payment_method',
        'ordered_at'
    ]
    
    # Add search fields
    search_fields = [
        'buyer_fullname',
        'buyer__username',
        'buyer__email',
        'delivery_location',
        'contact_phone',
        'product__name'
    ]
    
    # Add filters
    list_filter = [
        'status',
        'payment_method',
        'ordered_at',
        'delivered_at'
    ]
    
    # Make fields clickable to edit
    list_display_links = ['id', 'buyer_fullname']
    
    # Fields to display in detail view
    fieldsets = (
        ('👤 BUYER INFORMATION', {
            'fields': (
                ('buyer', 'buyer_fullname'),
                ('contact_phone', 'delivery_location'),
                'delivery_instructions',
            ),
            'description': 'Customer details provided during checkout'
        }),
        
        ('📦 ORDER DETAILS', {
            'fields': (
                ('product', 'quantity'),
                ('product_price_at_order', 'total_amount'),
                'status',
            ),
        }),
        
        ('💰 PAYMENT INFORMATION', {
            'fields': (
                'payment_method',
                ('ordered_at', 'updated_at'),
                'delivered_at',
            ),
        }),
    )
    
    # Read-only fields
    readonly_fields = [
        'ordered_at',
        'updated_at',
        'product_price_at_order'
    ]
    
    # List per page
    list_per_page = 25
    
    # ========== CUSTOM METHODS ==========
    
    def buyer_username(self, obj):
        return obj.buyer.username
    buyer_username.short_description = 'Username'
    buyer_username.admin_order_field = 'buyer__username'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'
    product_name.admin_order_field = 'product__name'
    
    def total_amount_display(self, obj):
        # FIXED: Removed the comma from the format string
        return format_html(
            '<strong>RWF {}</strong>',
            obj.total_amount
        )
    total_amount_display.short_description = 'Total'
    total_amount_display.admin_order_field = 'total_amount'
    
    def delivery_location_short(self, obj):
        if obj.delivery_location:
            short = obj.delivery_location[:50] + '...' if len(obj.delivery_location) > 50 else obj.delivery_location
            return format_html(
                '<span title="{}">{}</span>',
                obj.delivery_location,
                short
            )
        return '-'
    delivery_location_short.short_description = 'Delivery Address'
    
    def contact_phone_display(self, obj):
        if obj.contact_phone:
            return format_html('📞 {}', obj.contact_phone)
        return '-'
    contact_phone_display.short_description = 'Phone'
    
    def status_colored(self, obj):
        colors = {
            'Pending': 'orange',
            'Confirmed': 'blue',
            'Processing': 'purple',
            'Shipped': 'teal',
            'Out for Delivery': 'cyan',
            'Delivered': 'green',
            'Cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.status
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    # ========== ACTIONS ==========
    
    actions = ['mark_as_confirmed', 'mark_as_delivered', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='Confirmed')
        self.message_user(request, f'{queryset.count()} orders marked as confirmed.')
    mark_as_confirmed.short_description = "Mark selected orders as Confirmed"
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='Delivered', delivered_at=timezone.now())
        self.message_user(request, f'{queryset.count()} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected orders as Delivered"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='Cancelled')
        self.message_user(request, f'{queryset.count()} orders marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"