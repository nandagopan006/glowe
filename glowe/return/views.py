from django.shortcuts import render,redirect,get_object_or_404
from . models import ReturnRequest,ReturnImage
from order.models import Order,OrderItem,OrderStatusHistory
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required


def request_return(request,item_id):
    item = get_object_or_404(OrderItem,id=item_id,order__user=request.user)
    
    #only delvered allow
    if item.order.order_status != Order.Status.DELIVERED:
        messages.error(request, "Return not allowed")
        return redirect('order_detail', order_id=item.order.id)
    
     #return window (7 days)
    if timezone.now() > item.order.delivered_date + timedelta(days=7):
        messages.error(request, "Return window expired")
        return redirect('order_detail',order_id=item.order.id)

    if ReturnRequest.objects.filter(order_item=item).exists():
        messages.error(request,"Already requested")
        return redirect('order_detail',order_id=item.order.id)
    
    if item.item_status ==OrderItem.Status.CANCELLED:
        messages.error(request,"Cannot return cancelled item")
        return redirect('order_detail',order_id=item.order.id)
    
    RETURN_REASONS = [
    "Changed my mind",
    "Ordered by mistake",
    "Received wrong product",
    "Product arrived damaged",
    "Product quality not as expected",
    "Caused skin irritation or allergy",
    "Not suitable for my skin type",
    "Product expired or near expiry",
    "Missing items in package",
    "Packaging was damaged or leaking",
]
    ITEM_CONDITIONS = [
    "Unopened (Sealed)",
    "Opened but not used",
    "Used a few times",
    "Damaged on arrival",
    "Leaking or broken packaging",
]
    
    if request.method =="POST":
        
        reason=request.POST.get('reason')
        description=request.POST.get('description')
        condition=request.POST.get('condition')
        
        if reason not in RETURN_REASONS:
            messages.error(request, "Invalid reason")
            return redirect('order_detail', order_id=item.order.id)

        if condition not in ITEM_CONDITIONS:
            messages.error(request, "Invalid condition")
            return redirect('order_detail', order_id=item.order.id)
        

        # create return
        return_request = ReturnRequest.objects.create(
            order_item=item,
            user=request.user,
            reason=reason,
            description=description,
            item_condition=condition
        )
        
        images = request.FILES.getlist('images')
        if len(images) > 5:
            messages.error(request, "Maximum 5 images allowed")
            return redirect('order_detail', order_id=item.order.id)
        
        for img in images:
            ReturnImage.objects.create(
                return_request=return_request,
                image=img
            )
            
        item.item_status =OrderItem.Status.RETURN_REQUESTED
        item.save()

        

        messages.success(request,"Return requested  submitted successfully")
        return redirect('order_detail',order_id=item.order.id)

    return render(request,'user/return_form.html',{'item':item,
                                                   'RETURN_REASONS': RETURN_REASONS,
                                                    'ITEM_CONDITIONS': ITEM_CONDITIONS})

@login_required
def return_success(request, return_id):

    return_request =get_object_or_404(
        ReturnRequest,
        id=return_id,
        user=request.user
    )

    return render(request, 'user/return_success.html', {
        'return_request':return_request,
        'order':return_request.order_item.order
    })

