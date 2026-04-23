# views.py

from django.shortcuts import render, redirect, get_object_or_404
import openpyxl
from django.http import HttpResponse
from coupons.models import Coupon as CouponModel
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.models import OTPVerification, ProfileUser
from user.models import Address
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils import timezone
import random
from django.core.mail import send_mail
from django.conf import settings
import re
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.email_utils import send_admin_otp_email
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
    # Get the user
    user = get_object_or_404(ProfileUser, id=id, is_superuser=False)
    
    # Get all orders for this user
    all_orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Calculate total orders
    total_orders = all_orders.count()
    
    
    total_spent = 0
    for order in all_orders:
        total_spent += float(order.total_amount)
    
    # Calculate average order value
    if total_orders > 0:
        avg_order = round(total_spent / total_orders, 2)
    else:
        avg_order = 0
    
    # Count delivered orders
    delivered_orders = all_orders.filter(order_status='DELIVERED').count()
    
    # Paginate
    paginator = Paginator(all_orders, 5)
    page_number = request.GET.get('page', 1)
    orders_page = paginator.get_page(page_number)
    
    # Get user's addresses
    addresses = Address.objects.filter(user=user)
    
    
    phone_number = user.phone_number if user.phone_number else 'Not provided'
    full_name = user.get_full_name() if user.get_full_name() else user.username
    joined_date = user.date_joined
    
    # Get user's last login
    last_login = user.last_login if user.last_login else 'Never'

    context = {
        'user': user,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'avg_order': avg_order,
        'delivered_orders': delivered_orders,
        'orders': orders_page,
        'addresses': addresses,
        'phone_number': phone_number,
        'full_name': full_name,
        'joined_date': joined_date,
        'last_login': last_login,
    }
    
    return render(request, 'user_detail.html', context)
    

def sales_report(request):

    
    filter_type = request.GET.get('filter', 'month')
    today = timezone.now()

    
    if filter_type == 'day':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today

    elif filter_type == 'week':
        start_date = today - timedelta(days=7)
        end_date = today

    elif filter_type == 'year':
        start_date = today - timedelta(days=365)
        end_date = today

    elif filter_type == 'custom':
        start = request.GET.get('start_date')
        end   = request.GET.get('end_date')
        if start and end:
            start_date = make_aware(datetime.strptime(start, '%Y-%m-%d'))
            end_date   = make_aware(datetime.strptime(end,   '%Y-%m-%d'))
        else:
            start_date = today - timedelta(days=30)
            end_date   = today

    else:  # default: month
        start_date = today - timedelta(days=30)
        end_date   = today

    #Get all delivered orders in the date range
    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        order_status='DELIVERED'
    )

    
    total_orders = orders.count()

    total_revenue = 0
    for order in orders:
        total_revenue += float(order.total_amount)

    coupon_discount = 0
    for order in orders:
        coupon_discount += float(order.discount_amount)

    total_discount = coupon_discount  # discount_amount = coupon savings

    #Count total products sold
    order_items = OrderItem.objects.filter(order__in=orders)
    products_sold = 0
    for item in order_items:
        products_sold += item.quantity

    #Build chart data 
    daily_data = (
        orders
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(total=Sum('total_amount'))
        .order_by('date')
    )

    chart_list = []
    for row in daily_data:
        chart_list.append({
            'date':  str(row['date']),
            'total': float(row['total'] or 0),
        })

    # Calculate growth vs previous period
    period_length = end_date - start_date
    prev_start    = start_date - period_length
    prev_end      = start_date

    previous_orders = Order.objects.filter(
        created_at__range=[prev_start, prev_end],
        order_status='DELIVERED'
    )

    previous_revenue = 0
    for order in previous_orders:
        previous_revenue += float(order.total_amount)

    # Growth calculation logic
    if previous_revenue > 0:
        growth = round((total_revenue - previous_revenue) / previous_revenue * 100, 2)
    elif total_revenue > 0 and previous_revenue == 0:
  
        growth = 100.0
    else:
        
        growth = 0.0

    # Build orders list for the discount table
    orders_list = orders.select_related('payment').order_by('-created_at')[:50]


   
    orders_with_discount_count = orders.filter(discount_amount__gt=0).count()

   
    
    coupon_stats = CouponModel.objects.filter(
        used_count__gt=0,
        is_deleted=False
    ).order_by('-used_count')

    context = {
        'total_revenue':              total_revenue,
        'total_orders':               total_orders,
        'products_sold':              products_sold,
        'total_discount':             total_discount,
        'coupon_discount':            coupon_discount,
        'offer_discount':             0,
        'chart_data':                 chart_list,
        'growth':                     growth,
        'filter_type':                filter_type,
        'start_date':                 start_date,
        'end_date':                   end_date,
        'orders_list':                orders_list,
        'orders_with_discount_count': orders_with_discount_count,
        'coupon_stats':               coupon_stats,
    }

    return render(request, 'admin/sales_report.html', context)



def export_sales_excel(request):

  
    filter_type = request.GET.get('filter', 'month')
    today = timezone.now()

    #Set dates
    if filter_type == 'day':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date   = today
    elif filter_type == 'week':
        start_date = today - timedelta(days=7)
        end_date   = today
    elif filter_type == 'year':
        start_date = today - timedelta(days=365)
        end_date   = today
    elif filter_type == 'custom':
        start = request.GET.get('start_date')
        end   = request.GET.get('end_date')
        if start and end:
            start_date = make_aware(datetime.strptime(start, '%Y-%m-%d'))
            end_date   = make_aware(datetime.strptime(end,   '%Y-%m-%d'))
        else:
            start_date = today - timedelta(days=30)
            end_date   = today
    else:
        start_date = today - timedelta(days=30)
        end_date   = today

    #Fetch delivered orders
    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        order_status='DELIVERED'
    ).select_related('payment')

    #Create Excel workbook
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sales Report'

    #Write header row
    headers = ['Order ID', 'Date', 'Subtotal', 'Coupon Discount', 'Total Amount', 'Payment Method']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

  
    grand_total = 0
    for order in orders:
        # Get payment method safely
        try:
            payment_method = order.payment.payment_method
        except Exception:
            payment_method = 'N/A'

        ws.append([
            order.id,
            order.created_at.strftime('%Y-%m-%d'),
            float(order.subtotal),
            float(order.discount_amount),
            float(order.total_amount),
            payment_method,
        ])
        grand_total += float(order.total_amount)

   
    ws.append([])
    ws.append(['', '', '', 'Grand Total', grand_total])

  
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = max_len + 4


    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
    wb.save(response)
    return response


def export_sales_pdf(request):

    # Step 1: Read filter
    filter_type = request.GET.get('filter', 'month')
    today = timezone.now()

    # Step 2: Set dates
    if filter_type == 'day':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date   = today
    elif filter_type == 'week':
        start_date = today - timedelta(days=7)
        end_date   = today
    elif filter_type == 'year':
        start_date = today - timedelta(days=365)
        end_date   = today
    elif filter_type == 'custom':
        start = request.GET.get('start_date')
        end   = request.GET.get('end_date')
        if start and end:
            start_date = make_aware(datetime.strptime(start, '%Y-%m-%d'))
            end_date   = make_aware(datetime.strptime(end,   '%Y-%m-%d'))
        else:
            start_date = today - timedelta(days=30)
            end_date   = today
    else:
        start_date = today - timedelta(days=30)
        end_date   = today

   #Fetch delivered orders
    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        order_status='DELIVERED'
    ).select_related('payment')

    #Calculate totals
    total_revenue  = 0
    total_discount = 0
    for order in orders:
        total_revenue  += float(order.total_amount)
        total_discount += float(order.discount_amount)

    # Set up PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    doc    = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Step 6: Title and summary
    elements.append(Paragraph('Glowe — Sales Report', styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f'Period : {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}', styles['Normal']))
    elements.append(Paragraph(f'Total Orders  : {orders.count()}',     styles['Normal']))
    elements.append(Paragraph(f'Total Revenue : Rs.{total_revenue:.2f}',  styles['Normal']))
    elements.append(Paragraph(f'Total Discount: Rs.{total_discount:.2f}', styles['Normal']))
    elements.append(Spacer(1, 20))

    # Step 7: Build table rows
    table_data = [['Order ID', 'Date', 'Subtotal', 'Discount', 'Total', 'Payment']]

    for order in orders:
        try:
            payment_method = order.payment.payment_method
        except Exception:
            payment_method = 'N/A'

        table_data.append([
            str(order.id),
            order.created_at.strftime('%Y-%m-%d'),
            f'Rs.{float(order.subtotal):.2f}',
            f'Rs.{float(order.discount_amount):.2f}',
            f'Rs.{float(order.total_amount):.2f}',
            payment_method,
        ])

 
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#4a9050')),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, -1), 9),
        ('GRID',        (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN',       (2, 1), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]))

    elements.append(table)


    doc.build(elements)
    return response
