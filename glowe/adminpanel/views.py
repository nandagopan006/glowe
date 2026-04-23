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
    all_addresses = Address.objects.filter(user=user)
    
    # Paginate addresses 
    address_paginator = Paginator(all_addresses, 3)
    address_page_number = request.GET.get('address_page', 1)
    addresses_page = address_paginator.get_page(address_page_number)
    
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
        'delivered_count': delivered_orders,
        'orders': orders_page,
        'addresses': addresses_page,
        'phone_number': phone_number,
        'full_name': full_name,
        'joined_date': joined_date,
        'last_login': last_login,
    }
    
    return render(request, 'user_detail.html', context)
    

def sales_report(request):

    
    filter_type = request.GET.get('filter', 'month')
    now = timezone.localtime(timezone.now())
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if filter_type == 'day':
        # Today (since midnight)
        start_date = today_midnight
        end_date = now
    elif filter_type == 'week':
        # Last 7 days
        start_date = now - timedelta(days=7)
        end_date = now
    elif filter_type == 'year':
        # Last 365 days
        start_date = now - timedelta(days=365)
        end_date = now
    elif filter_type == 'custom':
        start = request.GET.get('start_date')
        end   = request.GET.get('end_date')
        if start and end:
            try:
                start_date = make_aware(datetime.strptime(start, '%Y-%m-%d'))
                end_date   = make_aware(datetime.strptime(end,   '%Y-%m-%d'))
            except:
                start_date = now - timedelta(days=30)
                end_date   = now
        else:
            start_date = now - timedelta(days=30)
            end_date   = now
    else:  # default: month
        # Last 30 days
        start_date = now - timedelta(days=30)
        end_date   = now

    #Get all delivered orders in the date range
    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        order_status='DELIVERED'
    )

    
    total_revenue = 0.0
    coupon_discount = 0.0
    for order in orders:
        total_revenue += float(order.total_amount)
        coupon_discount += float(order.discount_amount)

    # Count total products sold
    order_items = OrderItem.objects.filter(order__in=orders)
    products_sold = sum(item.quantity for item in order_items)

    
    chart_dict = {}
    if filter_type == 'day':
        # Hourly data for Today
        for h in range(24):
            chart_dict[f"{h:02d}:00"] = 0.0
            
        for order in orders:
            hour_key = order.created_at.strftime("%H:00")
            if hour_key in chart_dict:
                chart_dict[hour_key] += float(order.total_amount)
        
        chart_list = [{'date': k, 'total': v} for k, v in chart_dict.items()]
    else:
        # Daily data for other filters
        temp_date = start_date.date()
        end_date_only = end_date.date()
        while temp_date <= end_date_only:
            chart_dict[str(temp_date)] = 0.0
            temp_date += timedelta(days=1)
                
        for order in orders:
            date_str = str(order.created_at.date())
            if date_str in chart_dict:
                chart_dict[date_str] += float(order.total_amount)

        chart_list = [{'date': k, 'total': v} for k, v in chart_dict.items()]
        chart_list.sort(key=lambda x: x['date'])

  
    if filter_type == 'day':
        # Exactly yesterday (full day)
        prev_date = start_date.date() - timedelta(days=1)
        prev_rev_sum = Order.objects.filter(
            created_at__date=prev_date,
            order_status='DELIVERED'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        previous_revenue = float(prev_rev_sum)
    else:
        
        if filter_type == 'week':
            prev_start, prev_end = start_date - timedelta(days=7), start_date
        elif filter_type == 'year':
            prev_start, prev_end = start_date - timedelta(days=365), start_date
        else:
            period_length = end_date - start_date
            prev_start, prev_end = start_date - period_length, start_date

        prev_rev_sum = Order.objects.filter(
            created_at__range=[prev_start, prev_end],
            order_status='DELIVERED'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        previous_revenue = float(prev_rev_sum)

    # Growth percentage calculation
    if previous_revenue > 0:
        growth = round(((total_revenue - previous_revenue) / previous_revenue) * 100, 2)
    else:
        growth = 100.0 if total_revenue > 0 else 0.0

   
    orders_list = orders.select_related('payment').order_by('-created_at')
    coupon_stats = CouponModel.objects.filter(used_count__gt=0, is_deleted=False).order_by('-used_count')

    order_page_obj = Paginator(orders_list, 4).get_page(request.GET.get('order_page'))
    coupon_page_obj = Paginator(coupon_stats, 4).get_page(request.GET.get('coupon_page'))

    context = {
        'total_revenue':     total_revenue,
        'previous_revenue':  previous_revenue,
        'total_orders':      orders.count(),
        'products_sold':     products_sold,
        'coupon_discount':   coupon_discount,
        'chart_data':        chart_list,
        'growth':            growth,
        'filter_type':       filter_type,
        'start_date':        start_date,
        'end_date':          end_date,
        'orders_list':       order_page_obj,
        'coupon_stats':      coupon_page_obj,
    }

    return render(request, 'admin/sales_report.html', context)



def export_sales_excel(request):
    filter_type = request.GET.get('filter', 'month')
    now = timezone.localtime(timezone.now())
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if filter_type == 'day':
        start_date, end_date = today_midnight, now
    elif filter_type == 'week':
        start_date, end_date = now - timedelta(days=7), now
    elif filter_type == 'year':
        start_date, end_date = now - timedelta(days=365), now
    elif filter_type == 'custom':
        start, end = request.GET.get('start_date'), request.GET.get('end_date')
        if start and end:
            try:
                start_date = make_aware(datetime.strptime(start, '%Y-%m-%d'))
                end_date = make_aware(datetime.strptime(end, '%Y-%m-%d'))
            except:
                start_date, end_date = now - timedelta(days=30), now
        else:
            start_date, end_date = now - timedelta(days=30), now
    else:
        start_date, end_date = now - timedelta(days=30), now

    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        order_status='DELIVERED'
    ).select_related('payment').order_by('-created_at')

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sales Report'

    header_fill = PatternFill(start_color='4A9050', end_color='4A9050', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)
    center_align = Alignment(horizontal='center')
    money_format = '₹#,##0.00'
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    headers = ['Order Number', 'Date', 'Subtotal', 'Discount', 'Total Amount', 'Payment Method']
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    total_sum = 0
    for order in orders:
        pm = getattr(order.payment, 'payment_method', 'N/A')
        ws.append([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d'),
            float(order.subtotal),
            float(order.discount_amount),
            float(order.total_amount),
            pm
        ])
        total_sum += float(order.total_amount)
        curr_row = ws.max_row
        for i, cell in enumerate(ws[curr_row], 1):
            cell.border = thin_border
            if i in [3, 4, 5]: cell.number_format = money_format
            if i in [1, 2, 6]: cell.alignment = center_align

    ws.append([])
    ws.append(['', '', '', 'GRAND TOTAL', total_sum])
    total_row = ws.max_row
    ws.cell(row=total_row, column=4).font = Font(bold=True)
    ws.cell(row=total_row, column=5).font = Font(bold=True)
    ws.cell(row=total_row, column=5).number_format = money_format

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_len + 5

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Glowe_Sales_{filter_type}.xlsx"'
    wb.save(response)
    return response


def export_sales_pdf(request):
    filter_type = request.GET.get('filter', 'month')
    now = timezone.localtime(timezone.now())
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if filter_type == 'day':
        start_date, end_date = today_midnight, now
    elif filter_type == 'week':
        start_date, end_date = now - timedelta(days=7), now
    elif filter_type == 'year':
        start_date, end_date = now - timedelta(days=365), now
    elif filter_type == 'custom':
        start, end = request.GET.get('start_date'), request.GET.get('end_date')
        if start and end:
            try:
                start_date = make_aware(datetime.strptime(start, '%Y-%m-%d'))
                end_date = make_aware(datetime.strptime(end, '%Y-%m-%d'))
            except:
                start_date, end_date = now - timedelta(days=30), now
        else:
            start_date, end_date = now - timedelta(days=30), now
    else:
        start_date, end_date = now - timedelta(days=30), now

    orders = Order.objects.filter(
        created_at__range=[start_date, end_date],
        order_status='DELIVERED'
    ).select_related('payment').order_by('-created_at')

    total_revenue = sum(float(o.total_amount) for o in orders)
    total_discount = sum(float(o.discount_amount) for o in orders)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Glowe_Sales_{filter_type}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    title_style = styles['Title']
    title_style.textColor = colors.HexColor('#1A2E1A')
    title_style.fontSize = 20
    title_style.spaceAfter = 20

    elements = []
    
    elements.append(Paragraph("GLOWÉ — SALES REPORT", title_style))
    elements.append(Paragraph(f"Period: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    summary_data = [
        ['Total Orders', 'Total Revenue', 'Total Savings'],
        [str(orders.count()), f"₹{total_revenue:,.2f}", f"₹{total_discount:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[150, 150, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#6B7280')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,1), (-1,1), 14),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    table_data = [['Order Number', 'Date', 'Subtotal', 'Discount', 'Total Amount']]
    for o in orders:
        table_data.append([
            o.order_number,
            o.created_at.strftime('%Y-%m-%d'),
            f"₹{float(o.subtotal):.2f}",
            f"₹{float(o.discount_amount):.2f}",
            f"₹{float(o.total_amount):.2f}",
        ])

    main_table = Table(table_data, colWidths=[120, 90, 100, 100, 100])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A9050')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(main_table)

    doc.build(elements)
    return response
