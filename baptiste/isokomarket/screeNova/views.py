from decimal import Decimal
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg
from django.http import JsonResponse
from .models import Product, Cart, Order, Category, Profile, ContactMessage, ProductReview  # Add ProductReview
from .forms import SignUpForm, ProductForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

# ----------------- HELPER FUNCTIONS -----------------

def _get_user_type(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'user_type', None)


def _user_is_buyer(user):
    """Return True if the user has a buyer profile."""
    return hasattr(user, 'profile') and user.profile.user_type == 'buyer'


def _user_can_purchase(user):
    """Return True if the user can purchase products (buyer or seller)."""
    return hasattr(user, 'profile') and user.profile.user_type in ('buyer', 'seller')


# ----------------- HOME PAGE ----------------- (UPDATED - with recent reviews)

def home(request):
    """Displays products on homepage with MINIMAL info + PAGINATION + recent reviews."""
    
    products = Product.objects.filter(stock__gt=0).select_related('category').only(
        'id', 'name', 'price', 'image', 'category__name'
    ).annotate(order_count=Count('order'))
    
    categories = Category.objects.all()
    user_type = _get_user_type(request.user)
    
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # Order products
    products = products.order_by('-order_count', 'name')
    
    # Pagination
    paginator = Paginator(products, 8)  # 8 per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    # ✅ ADD: Get recent reviews for homepage (3 most recent approved reviews)
    recent_reviews = ProductReview.objects.filter(status='approved').select_related('user', 'product').order_by('-created_at')[:3]

    return render(request, 'screeNova/home.html', {
        'products': products,
        'categories': categories,
        'user_type': user_type,
        'selected_category': category_id,
        'recent_reviews': recent_reviews,  # ✅ ADD THIS
    })


# ----------------- PRODUCT DETAIL ----------------- (UPDATED with reviews)

def product_detail(request, product_id):
    """
    Shows COMPREHENSIVE details of a single product + customer reviews
    """
    # Get product with all details
    product = get_object_or_404(
        Product.objects.select_related('seller', 'category'),
        id=product_id
    )
    
    # Increment view count
    product.views += 1
    product.save(update_fields=['views'])
    
    # Get related products (minimal data for suggestions)
    related_products = Product.objects.filter(
        category=product.category,
        stock__gt=0
    ).exclude(
        id=product.id
    ).only(
        'id', 'name', 'price', 'image'
    )[:4]
    
    # ========== ✅ ADD REVIEW CODE HERE ==========
    # Get all reviews for this product
    reviews = ProductReview.objects.filter(product=product, status='approved').select_related('user')
    reviews_count = reviews.count()
    
    # Calculate average rating
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Calculate rating breakdown (for star bars)
    rating_breakdown = []
    for i in range(5, 0, -1):
        count = reviews.filter(rating=i).count()
        percentage = (count / reviews_count * 100) if reviews_count > 0 else 0
        rating_breakdown.append({
            'stars': i,
            'count': count,
            'percentage': percentage
        })
    
    # Check if user has purchased this product (for review eligibility)
    has_purchased = False
    has_reviewed = False
    if request.user.is_authenticated and _user_is_buyer(request.user):
        has_purchased = Order.objects.filter(
            buyer=request.user,
            product=product
        ).exclude(status='Cancelled').exists()
        has_reviewed = ProductReview.objects.filter(
            product=product,
            user=request.user
        ).exists()
    
    # Paginate reviews (optional - show 5 per page)
    review_paginator = Paginator(reviews, 5)
    review_page = request.GET.get('review_page')
    paginated_reviews = review_paginator.get_page(review_page)
    # ========== END OF REVIEW CODE ==========
    
    return render(request, 'screeNova/product_detail.html', {
        'product': product,
        'related_products': related_products,
        # ✅ ADD THESE TO CONTEXT
        'reviews': paginated_reviews,
        'reviews_count': reviews_count,
        'avg_rating': avg_rating,
        'rating_breakdown': rating_breakdown,
        'has_purchased': has_purchased,
        'has_reviewed': has_reviewed,
    })


# ========== ✅ ADD NEW REVIEW VIEWS ==========

@login_required
def add_product_review(request, product_id):
    """Add a review for a product (only verified buyers can review)."""
    if request.method != 'POST':
        return redirect('product_detail', product_id=product_id)
    
    if not _user_is_buyer(request.user):
        messages.error(request, "Only buyers can leave reviews.")
        return redirect('product_detail', product_id=product_id)
    
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has purchased this product
    has_purchased = Order.objects.filter(
        buyer=request.user,
        product=product
    ).exclude(status='Cancelled').exists()
    
    if not has_purchased:
        messages.error(request, 'You can only review products you have purchased.')
        return redirect('product_detail', product_id=product_id)
    
    # Check if already reviewed
    existing_review = ProductReview.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.error(request, 'You have already reviewed this product.')
        return redirect('product_detail', product_id=product_id)
    
    rating = request.POST.get('rating')
    title = request.POST.get('title', '')
    comment = request.POST.get('comment')
    
    if not rating or not comment:
        messages.error(request, 'Please provide both rating and comment.')
        return redirect('product_detail', product_id=product_id)
    
    try:
        review = ProductReview.objects.create(
            product=product,
            user=request.user,
            rating=int(rating),
            title=title,
            comment=comment,
            is_verified_purchase=True,
            status='approved'  # Auto-approve
        )
        
        # Handle image upload if any
        if request.FILES.get('review_image'):
            review.image = request.FILES['review_image']
            review.save()
        
        messages.success(request, 'Thank you for your review!')
    except Exception as e:
        messages.error(request, f'Error saving review: {str(e)}')
    
    return redirect('product_detail', product_id=product_id)


@login_required
def mark_review_helpful(request, review_id):
    """Mark a review as helpful."""
    if request.method == 'POST':
        review = get_object_or_404(ProductReview, id=review_id)
        review.helpful_count += 1
        review.save()
        return JsonResponse({'success': True, 'count': review.helpful_count})
    return JsonResponse({'success': False}, status=400)


@login_required
def delete_review(request, review_id):
    """Delete user's own review."""
    if request.method == 'POST':
        review = get_object_or_404(ProductReview, id=review_id, user=request.user)
        review.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


# ----------------- ADD TO CART ----------------- (unchanged)

@login_required
def add_to_cart(request, product_id):
    """Adds a product to the cart with stock check and quantity specification."""
    if not _user_can_purchase(request.user):
        messages.error(request, "Only registered buyers or sellers can add products to the cart.")
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)
    
    # Get quantity from POST data or default to 1
    quantity = int(request.POST.get('quantity', 1))
    
    # Validate quantity
    if quantity <= 0:
        messages.error(request, "Quantity must be at least 1.")
        return redirect('product_detail', product_id=product.id)
    
    # Check if product is in stock
    if product.stock <= 0:
        messages.error(request, "Sorry, this product is out of stock.")
        return redirect('product_detail', product_id=product.id)
    
    # Check if requested quantity exceeds stock
    if quantity > product.stock:
        messages.error(request, f"Only {product.stock} items available in stock.")
        return redirect('product_detail', product_id=product.id)
    
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        # Check if total quantity exceeds stock
        if cart_item.quantity + quantity > product.stock:
            messages.error(request, f"Only {product.stock} items available in stock. You already have {cart_item.quantity} in cart.")
            return redirect('product_detail', product_id=product.id)
        cart_item.quantity += quantity
        cart_item.save()
        messages.success(request, f"Added {quantity} more {product.name} to cart.")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"{quantity} x {product.name} added to cart.")

    next_action = request.GET.get('next')
    if next_action == 'payment_selection':
        return redirect('payment_selection')
    if next_action == 'view_cart':
        return redirect('view_cart')

    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ----------------- VIEW CART ----------------- (unchanged)

@login_required
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')

    total_price = 0
    for item in cart_items:
        total_price += item.product.price * item.quantity

    context = {
        'cart_items': cart_items,
        'total_price': total_price
    }

    return render(request, 'screeNova/cart.html', context)


# ----------------- PLACE ORDER ----------------- (unchanged)

@login_required
def place_order(request):

    if request.method == "POST":

        if not _user_can_purchase(request.user):
            messages.error(request, "Only registered buyers or sellers can place orders.")
            return redirect('home')

        cart_items = Cart.objects.filter(user=request.user)

        if not cart_items.exists():
            messages.info(request, "Your cart is empty.")
            return redirect('view_cart')

        # Check stock availability for all items
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(request, f"Insufficient stock for {item.product.name}. Only {item.product.stock} available.")
                return redirect('view_cart')

        # Place orders and update stock
        for item in cart_items:
            Order.objects.create(
                buyer=request.user,
                product=item.product,
                quantity=item.quantity
            )
            # Update product stock
            from django.db.models import F
            item.product.stock = F('stock') - item.quantity
            item.product.save(update_fields=['stock'])

        cart_items.delete()

        messages.success(request, "Your order has been placed successfully!")

    return redirect('home')


# ----------------- SELLER DASHBOARD ----------------- (unchanged)

@login_required
def seller_dashboard(request):
    """Shows products added by the seller and orders for their products."""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'seller':
        messages.error(request, "Only sellers can view this page.")
        return redirect('home')

    # Get seller's products with minimal fields
    products = Product.objects.filter(seller=request.user).only(
        'id', 'name', 'price', 'stock', 'image', 'views'
    )

    # Get orders for seller's products
    orders = Order.objects.filter(
        product__seller=request.user
    ).select_related(
        'buyer', 'product'
    ).only(
        'id', 'quantity', 'status', 'ordered_at',
        'buyer__username', 'product__name', 'product__price'
    ).order_by('-ordered_at')

    # Calculate income metrics for all non-cancelled orders
    # This includes any order that represents a completed transaction
    completed_orders = orders.exclude(status='Cancelled')
    gross_income = Decimal('0.00')
    for order in completed_orders:
        gross_income += order.product.price * order.quantity

    platform_fee_percentage = Decimal('0.03')  # 3%
    platform_fee = gross_income * platform_fee_percentage
    net_income = gross_income - platform_fee

    return render(request, 'screeNova/seller_dashboard.html', {
        'products': products,
        'orders': orders,
        'gross_income': gross_income,
        'platform_fee': platform_fee,
        'net_income': net_income,
        'platform_fee_percentage': platform_fee_percentage,
        'delivered_orders_count': completed_orders.count(),
    })


# ----------------- ADD PRODUCT (SELLER) ----------------- (unchanged)

@login_required
def add_product(request):
    """Allow a seller to add a new product with all details."""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'seller':
        messages.error(request, "Only sellers can add products.")
        return redirect('home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, "Product added successfully.")
            return redirect('seller_dashboard')
    else:
        form = ProductForm()

    return render(request, 'screeNova/product_form.html', {
        'form': form, 
        'title': 'Add Product'
    })


def edit_product(request, product_id):
    """Allow a seller to edit their own product."""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user is the seller of this product
    if product.seller != request.user:
        messages.error(request, "You can only edit your own products.")
        return redirect('product_detail', product_id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'screeNova/product_form.html', {
        'form': form, 
        'title': 'Edit Product'
    })


def delete_product(request, product_id):
    """Allow a seller to delete their own product."""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user is the seller of this product
    if product.seller != request.user:
        messages.error(request, "You can only delete your own products.")
        return redirect('product_detail', product_id=product_id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect('seller_dashboard')
    
    return render(request, 'screeNova/delete_confirm.html', {
        'product': product
    })


# ----------------- AUTHENTICATION VIEWS ----------------- (unchanged)

def signup(request):
    """Register a new user and set their role (buyer or seller)."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set the chosen user type on the Profile
            user_type = form.cleaned_data.get('user_type')
            Profile.objects.update_or_create(user=user, defaults={'user_type': user_type})

            # Log the user in immediately after signup
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'screeNova/signup.html', {'form': form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'screeNova/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


# ----------------- SEARCH ----------------- (unchanged)

def search_products(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query)
    categories = Category.objects.all()
    user_type = _get_user_type(request.user)
    return render(request, 'screeNova/home.html', {
        'products': products,
        'categories': categories,
        'user_type': user_type,
    })


# ----------------- PAYMENT VIEWS ----------------- (unchanged)

@login_required
def payment_selection(request):
    """Select a payment method before placing the order."""
    if not _user_can_purchase(request.user):
        messages.error(request, "Only buyers or sellers can place orders.")
        return redirect('home')

    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect('view_cart')

    total_price = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        buyer_fullname = request.POST.get('buyer_fullname', '').strip()
        delivery_location = request.POST.get('delivery_location', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        delivery_instructions = request.POST.get('delivery_instructions', '').strip()

        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return redirect('payment_selection')

        if not buyer_fullname or len(buyer_fullname) < 2:
            messages.error(request, "Please provide a valid full name for delivery.")
            return redirect('payment_selection')

        if not delivery_location or len(delivery_location) < 10:
            messages.error(request, "Please provide a detailed delivery address.")
            return redirect('payment_selection')

        # Check stock availability and update stock for all items
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(request, f"Insufficient stock for {item.product.name}. Only {item.product.stock} available.")
                return redirect('view_cart')

        for item in cart_items:
            Order.objects.create(
                buyer=request.user,
                product=item.product,
                quantity=item.quantity,
                payment_method=payment_method,
                buyer_fullname=buyer_fullname,
                delivery_location=delivery_location,
                contact_phone=contact_phone or None,
                delivery_instructions=delivery_instructions or None,
            )
            # Reduce stock after making order
            from django.db.models import F
            item.product.stock = F('stock') - item.quantity
            item.product.save(update_fields=['stock'])

        cart_items.delete()  # clear cart
        return redirect('order_success')

    return render(request, 'screeNova/payment.html', {'total_price': total_price})


@login_required
def order_success(request):
    """Show success message after placing order."""
    return render(request, 'screeNova/order_success.html')


# ----------------- STATIC PAGES ----------------- (unchanged)

def about_us(request):
    """Show the About Us page."""
    return render(request, 'screeNova/about.html')


def contact(request):
    """Show a contact form and handle submissions."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, "Please fill in all the fields.")
            return render(request, 'screeNova/contact.html', {
                'name': name,
                'email': email,
                'message': message,
            })

        # Save the submitted message so it can be reviewed later
        ContactMessage.objects.create(name=name, email=email, message=message)

        messages.success(request, "Thank you! Your message has been received.")
        return redirect('contact')

    return render(request, 'screeNova/contact.html')


@login_required
def contact_messages(request):
    """List submitted contact messages (staff-only)."""
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to view contact messages.")
        return redirect('home')

    messages_list = ContactMessage.objects.order_by('-created_at')
    return render(request, 'screeNova/contact_messages.html', {'messages_list': messages_list})


@login_required
def profile(request):
    return render(request, 'screeNova/profile.html')