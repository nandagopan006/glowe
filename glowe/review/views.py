from django.shortcuts import render,get_object_or_404, redirect
from django.contrib import messages
from .models import Review, ReviewImage
from product.models import Product
from order.models import Order
from .utils import can_user_review
from django.db import transaction
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse
# Create your views here.


def create_review(request, product_id, order_id):
    product = get_object_or_404(Product, id=product_id)
    order = get_object_or_404(Order, id=order_id)
    
    if not can_user_review(request.user, product, order):
        messages.error(request, "You cannot review this product")
        return redirect('orders')
    if request.method == "POST":
        rating = request.POST.get('rating')
        title = (request.POST.get('title') or "").strip()
        comment = (request.POST.get('comment') or "").strip()

        # Safe rating conversion
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            messages.error(request, "Invalid rating")
            return redirect('product_detail_view', slug=product.slug)

        #Rating validation
        if rating < 1 or rating > 5:
            messages.error(request, "Rating must be between 1 and 5")
            return redirect('product_detail_view', slug=product.slug)

        #Prevent empty comment
        if not comment or not comment.strip():
            messages.error(request, "Review cannot be empty")
            return redirect('product_detail_view', slug=product.slug)
        if len(comment) < 7:
            messages.error(request, "Review too short")
            return redirect('product_detail_view', slug=product.slug)
        if title and len(title) < 4:
            messages.error(request, "Title must be at least 4 characters")
            return redirect('product_detail_view', slug=product.slug)
        images = request.FILES.getlist('images')

        if len(images) > 3:
            messages.error(request, "You can upload maximum 3 images")
            return redirect('product_detail_view', slug=product.slug)

        for img in images:
            if img.size > 2 * 1024 * 1024:  # 2MB limit
                messages.error(request, "Each image must be under 2MB")
                return redirect('product_detail_view', slug=product.slug)
        
        review = Review.objects.create(
            user=request.user,
            product=product,
            order=order,
            rating=rating,
            title=title,
            comment=comment,
            status='pending'
        )
        
        
        for img in images:
            ReviewImage.objects.create(review=review,image=img)
        
        messages.success(request, "Review added successfully")
        return redirect('product_detail_view', slug=product.slug)
    
    
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404( Review,id=review_id,user=request.user,is_deleted=False)

    with transaction.atomic():
        review.is_deleted = True
        review.status = "rejected"  
        review.save()

    messages.success(request, "Your review has been deleted")

    return redirect('product_detail', slug=review.product.slug)



def admin_review_list(request):

    is_deleted_filter = request.GET.get('is_deleted', 'false') == 'true'
    
    status = request.GET.get('status')
    search = request.GET.get('search')
    rating = request.GET.get('rating')
    sort = request.GET.get('sort')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    reviews = Review.objects.filter(is_deleted=is_deleted_filter).select_related('user', 'product')

    #Status Filter
    if status in ['pending', 'approved', 'rejected']:
        reviews = reviews.filter(status=status)

    # Search
    if search:
        reviews = reviews.filter(
            Q(comment__icontains=search) |
            Q(title__icontains=search) |
            Q(user__full_name__icontains=search) |
            Q(product__name__icontains=search)
        )

    # Rating Filter
    if rating:
        try:
            reviews = reviews.filter(rating=int(rating))
        except ValueError:
            pass

    #Date Filter
    if start_date and end_date:
        reviews = reviews.filter(created_at__date__range=[start_date, end_date])

    #Sorting 
    if sort == "rating_high":
        reviews = reviews.order_by('-rating')
    elif sort == "rating_low":
        reviews = reviews.order_by('rating')
    else:
        reviews = reviews.order_by('-created_at')  # default

    #Pagination
    paginator = Paginator(reviews, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    review_all = Review.objects.filter(is_deleted=is_deleted_filter).count()
    pending = Review.objects.filter(status='pending', is_deleted=is_deleted_filter).count()
    approved = Review.objects.filter(status='approved', is_deleted=is_deleted_filter).count()
    rejected = Review.objects.filter(status='rejected', is_deleted=is_deleted_filter).count()
    
    return render(request, 'admin/review_list.html', {
        'reviews': page_obj,
        "review_all":review_all,
        'pending':pending,
        'approved':approved,
        'rejected':rejected,
        'current_status': status,
        'search_query': search,
        'current_rating': rating,
        'current_sort': sort,
        'start_date': start_date,
        'end_date': end_date,
        'is_deleted': 'true' if is_deleted_filter else 'false',
    })
    
def admin_review_detail(request, review_id):

    review = get_object_or_404(
        Review.objects.select_related('user', 'product', 'order')
                      .prefetch_related('images'),
        id=review_id,
        is_deleted=False
    )

    
    is_low_rating = review.rating <= 2
    has_images = review.images.exists()

    return render(request, 'admin/detail.html', {
        'review': review,
        'is_low_rating': is_low_rating,
        'has_images': has_images,
    })



@require_POST
def approve_review(request, review_id):
    review = get_object_or_404(
        Review,
        id=review_id,
        is_deleted=False
    )

    # prevent unnecessary update
    if review.status == "approved":
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "success", "message": "Review already approved"})
        messages.info(request, "Review already approved")
        return redirect(request.META.get('HTTP_REFERER', 'review_list'))

    with transaction.atomic():
        review.status = "approved"
        review.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "success", "message": "Review approved successfully"})
        
    messages.success(request, "Review approved successfully")
    return redirect(request.META.get('HTTP_REFERER', 'review_list'))

@require_POST
def reject_review(request, review_id):
    review = get_object_or_404(
        Review,
        id=review_id,
        is_deleted=False
    )

    if review.status == "rejected":
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "success", "message": "Review already rejected"})
        messages.info(request, "Review already rejected")
        return redirect(request.META.get('HTTP_REFERER', 'review_list'))

    with transaction.atomic():
        review.status = "rejected"
        review.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "success", "message": "Review rejected successfully"})
        
    messages.success(request, "Review rejected successfully")
    return redirect(request.META.get('HTTP_REFERER', 'review_list'))


@require_POST
def archive_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, is_deleted=False)
    with transaction.atomic():
        review.is_deleted = True
        review.save()
        
    messages.success(request, "Review archived successfully")
    return redirect(request.META.get('HTTP_REFERER', 'review_list'))

@require_POST
def restore_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, is_deleted=True)
    with transaction.atomic():
        review.is_deleted = False
        review.save()
        
    messages.success(request, "Review restored successfully")
    return redirect(request.META.get('HTTP_REFERER', 'review_list'))

@require_POST
def permanent_delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, is_deleted=True)
    review.delete()
        
    messages.success(request, "Review permanently deleted")
    return redirect(request.META.get('HTTP_REFERER', 'review_list'))