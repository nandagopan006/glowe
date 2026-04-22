# views.py

from django.shortcuts import render, redirect
import openpyxl
from django.http import HttpResponse

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.models import OTPVerification, ProfileUser
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils import timezone
import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import  get_object_or_404
import re
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.email_utils import send_admin_otp_email
from django.utils import timezone
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from order.models import Order, OrderItem
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet



@never_cache
def admin_signin(request):

    # Already logged in admin
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    if request.method=="POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        
        if not email :
            messages.error(request,"Email is required")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email}) 
        if not password :
            messages.error(request,"password is required")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email}) 
        
        
        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request,"Invalid email or password")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email})

        #admin acces not normal usr
        if not user.is_superuser:
            messages.error(request,"Access denied.Admin only.")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email}) 
        
        login(request, user)
        
        request.session['success']='Welcome to the Dashboard'
        return redirect('admin_dashboard')

    return render(request, 'auth/admin_signin.html', {'submitted_email': ''})

@never_cache
@login_required(login_url='/admin-signin/')
def admin_dashboard(request):
    success=request.session.pop('success',None)
    if not request.user.is_superuser:
        return redirect('admin_signin')

    return render(request, 'admin_dashboard.html',{"success":success})

def admin_signout(request):
    logout(request)
    return redirect('admin_signin')


def admin_forget_password(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    if request.method=="POST":
        email=request.POST.get('email')

        if not email:
            messages.error(request,"Email required")
            return render(request, 'auth/admin_forget_password.html', {'submitted_email': email})

        try:
            user = ProfileUser.objects.get(email=email)

            
            if not user.is_superuser:
                messages.error(request,"Not authorized")
                return render(request, 'auth/admin_forget_password.html', {'submitted_email': email})
        except ProfileUser.DoesNotExist:
            messages.error(request,"Email not found")
            return render(request, 'auth/admin_forget_password.html', {'submitted_email': email})

        # if old otp have it will dlt
        OTPVerification.objects.filter(user=user).delete()
        otp =str(random.randint(1000, 9999))

        OTPVerification.objects.create(user=user,otp_code=otp,
            expires_at=timezone.now() +timedelta(minutes=2))

        
        # Send premium admin OTP email
        send_admin_otp_email(user, otp)

        request.session['reset_user']=user.id
        return redirect('admin_otp_verification')


    return render(request, 'auth/admin_forget_password.html', {'submitted_email': ''})

def admin_otp_verification(request):
    
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    user_id=request.session.get('reset_user')

    if not user_id:
        return redirect('admin_forgot_password')

    user=ProfileUser.objects.get(id=user_id)

    if request.method=="POST":
        entered_otp=request.POST.get('otp')

        otp_obj = OTPVerification.objects.filter(user=user).order_by('-created_at').first()

        if not otp_obj:
            messages.error(request,"OTP not found")
            return redirect('admin_otp_verification')

        if timezone.now() >otp_obj.expires_at:
            messages.error(request, "OTP expired")
            return redirect('admin_forgot_password')

        if otp_obj.otp_code!=entered_otp:
            messages.error(request,"Invalid OTP")
            return redirect('admin_otp_verification')

        otp_obj.is_verified =True
        otp_obj.save()

        otp_obj.delete() #delte otp ot[ is one ytime use]
        
        request.session['otp_verified']=True # delt otp aftr user cn still procced resset pass
        return redirect('admin_reset_password')

    return render(request,'auth/admin_otp_verification.html')


def admin_resend_otp(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    user_id=request.session.get('reset_user')
    if not user_id:
        return redirect('admin_forgot_password')

    user=ProfileUser.objects.get(id=user_id)

    OTPVerification.objects.filter(user=user).delete()
    otp =str(random.randint(1000,9999))


    OTPVerification.objects.create(user=user,otp_code=otp,
        expires_at=timezone.now() +timedelta(minutes=2))

    # Send premium admin OTP email
    send_admin_otp_email(user, otp)
    messages.success(request,"New OTP sent")
    return redirect('admin_otp_verification')





def admin_reset_password(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    user_id=request.session.get('reset_user')
    verified=request.session.get('otp_verified')

    if not user_id or not verified:
        return redirect('admin_forgot_password')

    user=ProfileUser.objects.get(id=user_id)

    if request.method =="POST":
        password=request.POST.get('password')
        confirm=request.POST.get('confirm_password')

        if not password or not confirm:
            messages.error(request,"All fields required")
            return redirect('admin_reset_password')

        if password!=confirm:
            messages.error(request,"Passwords do not match")
            return redirect('admin_reset_password')

        
        pattern_pass=r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$'
        if not re.match(pattern_pass, password):
            messages.error(request,"Weak password")
            return redirect('admin_reset_password')

        user.set_password(password)
        user.save()

        # cleanup
        OTPVerification.objects.filter(user=user).delete()
        request.session.flush()

        messages.success(request,"Password reset successful")
        return redirect('admin_signin')

    return render(request, 'auth/admin_reset_password.html')

def user_management(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    

    users = ProfileUser.objects.filter(is_superuser=False).order_by('-date_joined')

    if q:
        users = users.filter(
            Q(full_name__icontains=q) |
            Q(email__icontains=q)
        )
    if status=='active':
        users=users.filter(is_active=True)
    elif status =='blocked':
        users =users.filter(is_active=False)

    paginator =Paginator(users, 5)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    context={
        'users':page_obj,
        'page_obj': page_obj, 
        'q':q,
        'status':status,
    }
    

    return render(request, 'user_management.html',context)

def admin_toggle_block(request, id):
    if request.method !='POST':
        return redirect('user_management')
    user = get_object_or_404(ProfileUser, id=id)

    # Toggle is_activ
    
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    
    name=user.get_full_name() or user.email
    action='unblocked' if user.is_active else'blocked'
    messages.success(request,f"{name} has been {action} successfully.")

    return redirect('user_management')
def user_detail(request, id):
    user = get_object_or_404(ProfileUser, id=id, is_superuser=False)
 
    # Uncomment when Order model is ready:
    # from orders.models import Order
    # from django.db.models import Sum
    # all_orders   = Order.objects.filter(user=user).order_by('-created_at')
    # total_orders = all_orders.count()
    # total_spent  = all_orders.aggregate(s=Sum('total_amount'))['s'] or 0
    # avg_order    = round(total_spent / total_orders, 2) if total_orders else 0
    # orders_page  = Paginator(all_orders, 5).get_page(request.GET.get('order_page', 1))
 
    total_orders=0
    total_spent='0.00'
    avg_order='0.00'
    orders_page=    Paginator([], 5).get_page(1)
 
    return render(request,'user_detail.html',{
        'user':user,
        'total_orders':total_orders,
        'total_spent':total_spent,
        'avg_order':avg_order,
        'orders':orders_page,
    })
    

def sales_report(request):
    filter_type = request.GET.get("filter", "month")

    today = timezone.now()

    #Date filtering
    if filter_type == "day":
        start_date = today.replace(hour=0, minute=0, second=0)
        end_date = today

    elif filter_type == "week":
        start_date = today - timedelta(days=7)
        end_date = today

    elif filter_type == "year":
        start_date = today - timedelta(days=365)
        end_date = today

    elif filter_type == "custom":
        start = request.GET.get("start_date")
        end = request.GET.get("end_date")

        if start and end:
            start_date = make_aware(datetime.strptime(start, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end, "%Y-%m-%d"))
        else:
            start_date = today - timedelta(days=30)
            end_date = today

    else:
        start_date = today - timedelta(days=30)
        end_date = today

    
    orders = Order.objects.filter(created_at__range=[start_date, end_date],status="DELIVERED")

    total_revenue = orders.aggregate(Sum("final_amount"))["final_amount__sum"] or 0
    total_orders = orders.count()

    coupon_discount = orders.aggregate(Sum("coupon_discount"))["coupon_discount__sum"] or 0
    offer_discount = orders.aggregate(Sum("offer_discount"))["offer_discount__sum"] or 0

    total_discount = coupon_discount + offer_discount

    products_sold = OrderItem.objects.filter(
        order__in=orders
    ).aggregate(Sum("quantity"))["quantity__sum"] or 0

    #Chart Data
    chart_data = orders.annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        total=Sum("final_amount")
    ).order_by("date")

    #Growth Calculation
    previous_orders = Order.objects.filter(
        created_at__range=[
            start_date - (end_date - start_date),
            start_date
        ],
        status="DELIVERED"
    )

    previous_revenue = previous_orders.aggregate(
        Sum("final_amount")
    )["final_amount__sum"] or 0

    if previous_revenue > 0:
        growth = ((total_revenue - previous_revenue) / previous_revenue) * 100
    else:
        growth = 0

    context = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "products_sold": products_sold,
        "total_discount": total_discount,
        "coupon_discount": coupon_discount,
        "offer_discount": offer_discount,
        "chart_data": list(chart_data),
        "growth": round(growth, 2),
        "filter_type": filter_type,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "admin/sales_report.html", context)
 
 

def export_sales_excel(request):
    filter_type = request.GET.get("filter", "month")
    today = timezone.now()

 
    if filter_type == "day":
        start_date = today.replace(hour=0, minute=0, second=0)
        end_date = today

    elif filter_type == "week":
        start_date = today - timedelta(days=7)
        end_date = today

    elif filter_type == "year":
        start_date = today - timedelta(days=365)
        end_date = today

    elif filter_type == "custom":
        start = request.GET.get("start_date")
        end = request.GET.get("end_date")

        if start and end:
            start_date = make_aware(datetime.strptime(start, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end, "%Y-%m-%d"))
        else:
            start_date = today - timedelta(days=30)
            end_date = today

    else:
        start_date = today - timedelta(days=30)
        end_date = today


    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        status="DELIVERED"
    ).only(
        "id", "created_at", "total_amount",
        "coupon_discount", "offer_discount",
        "final_amount", "payment_method"
    )

   
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Report"

  
    headers = [
        "Order ID",
        "Date",
        "Total",
        "Coupon Discount",
        "Offer Discount",
        "Final Amount",
        "Payment Method"
    ]

    ws.append(headers)

    from openpyxl.styles import Font
    for cell in ws[1]:
        cell.font = Font(bold=True)

    total_sum = 0

    for order in orders:
        ws.append([
            order.id,
            order.created_at.strftime("%Y-%m-%d"),
            float(order.total_amount),
            float(order.coupon_discount),
            float(order.offer_discount),
            float(order.final_amount),
            order.payment_method
        ])
        total_sum += float(order.final_amount)

    # Add total row
    ws.append([])
    ws.append(["", "", "", "", "Total Revenue", total_sum])

    
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter

        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass

        ws.column_dimensions[col_letter].width = max_length + 2

  
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="sales_report.xlsx"'

    wb.save(response)
    return response





def export_sales_pdf(request):
    filter_type = request.GET.get("filter", "month")
    today = timezone.now()

    #  Date filter 
    if filter_type == "day":
        start_date = today.replace(hour=0, minute=0, second=0)
        end_date = today

    elif filter_type == "week":
        start_date = today - timedelta(days=7)
        end_date = today

    elif filter_type == "year":
        start_date = today - timedelta(days=365)
        end_date = today

    elif filter_type == "custom":
        start = request.GET.get("start_date")
        end = request.GET.get("end_date")

        if start and end:
            start_date = make_aware(datetime.strptime(start, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end, "%Y-%m-%d"))
        else:
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        start_date = today - timedelta(days=30)
        end_date = today

    # Filtered Orders
    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        status="DELIVERED"
    )

    #Totals
    total_revenue = sum([o.final_amount for o in orders])
    total_discount = sum([o.discount_amount for o in orders])

    #Response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    # Title
    elements.append(Paragraph("Sales Report", styles["Title"]))
    elements.append(Spacer(1, 10))

    # Summary
    elements.append(Paragraph(f"Total Revenue: ₹{total_revenue}", styles["Normal"]))
    elements.append(Paragraph(f"Total Discount: ₹{total_discount}", styles["Normal"]))
    elements.append(Paragraph(f"Total Orders: {orders.count()}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Table Data
    data = [
        ["ID", "Date", "Total", "Discount", "Final", "Payment"]
    ]

    for order in orders:
        data.append([
            order.id,
            order.created_at.strftime("%Y-%m-%d"),
            float(order.total_amount),
            float(order.discount_amount),
            float(order.final_amount),
            order.payment_method
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 1, colors.black),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))

    elements.append(table)

    doc.build(elements)

    return response