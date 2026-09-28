from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('place-order/', views.place_order, name='place_order'),
     path('signup/', views.signup, name='signup'),  # <- the name here must match
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='store_logout'),
    path('search/', views.search_products, name='search_products'),
    path('seller_dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('product_detail/<int:product_id>/', views.product_detail, name='product_detail'),

    # Static pages
    path('about/', views.about_us, name='about_us'),
    path('contact/', views.contact, name='contact'),
    path('contact-messages/', views.contact_messages, name='contact_messages'),

    # urls.py
    path('payment/', views.payment_selection, name='payment_selection'),
    path('order-success/', views.order_success, name='order_success'),
    path('profile/', views.profile, name='profile'),

    # Add these to your urlpatterns

# Review URLs
path('product/<int:product_id>/add-review/', views.add_product_review, name='add_product_review'),
path('review/<int:review_id>/helpful/', views.mark_review_helpful, name='mark_review_helpful'),
path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
]
