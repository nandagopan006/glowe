from django.shortcuts import render, redirect
from .forms import SignupForm
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ProfileUser, OTPVerification, LoginAttempt, UserSecurity
from .email_utils import send_otp_email, send_password_reset_email
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db import transaction
from wallet.models import Wallet, WalletTransaction
import re
from django.views.decorators.cache import never_cache
from core.decorators import unauthenticated_user


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


@never_cache
@unauthenticated_user
def signup_page(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        # (Spam protection)
        if request.POST.get("website_url"):
           
            return redirect("signup")

        # take the data sent from the signup form
        form = SignupForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            # Check for existing unverified user with this email
            existing_user = ProfileUser.objects.filter(
                email=email, is_verified=False
            ).first()
            password = form.cleaned_data["password"]

            if existing_user:
                # Reuse the existing unverified user record
                user = existing_user
                user.full_name = form.cleaned_data["full_name"]
                user.username = user.email
                user.set_password(password)
            else:
                # Create a new user record
                user = form.save(commit=False)
                user.username = user.email
                user.set_password(password)

            # Referral logic
            referral_code = form.cleaned_data.get("referral_code")
            if referral_code and not user.referred_by:
                referrer = ProfileUser.objects.filter(
                    referral_code=referral_code
                ).first()
                if referrer and referrer != user:
                    user.referred_by = referrer

            # Crucial: user remains unverified and inactive until OTP is verified  # noqa: E501
            user.is_active = False
            user.is_verified = False
            user.save()

            OTPVerification.objects.filter(
                user=user, is_verified=False
            ).delete()

            otp_code = str(random.randint(1000, 9999))
            OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=1),
            )

            send_otp_email(request, user, otp_code)
            # in signup view — SAVE the email before redirecting
            request.session["email"] = (
                user.email
            )  # it will store in broswer session
            request.session["otp_msg"] = "OTP sent! Check your email."

            return redirect("signup_otp_verify")
    else:
        # if the page is opened normally (GET request), create an empty form
        form = SignupForm()

    return render(request, "signup.html", {"form": form})


@never_cache
def signup_otp_verify(request):
    email = request.session.get("email")
    otp_msg = request.session.pop("otp_msg", None)

    try:
        user = ProfileUser.objects.get(email=email)
        # Ensure security profile exists
        UserSecurity.objects.get_or_create(user=user)
    except ProfileUser.DoesNotExist:
        return redirect("signup")

    # get the latest unverified OTP record for this user
    otp_record = OTPVerification.objects.filter(
        user=user, is_verified=False
    ).first()

    if not otp_record:
        return redirect("signup")

    # seconds remaining for the timer start with remaing
    seconds_left = max(
        0, round((otp_record.expires_at - timezone.now()).total_seconds())
    )
    # delete expired OTP records
    OTPVerification.objects.filter(
        is_verified=False,
        created_at__lt=timezone.now()
        - timedelta(minutes=5),  # to keep database clean (5m)
    ).delete()

    if request.method == "POST":
        entered_otp = request.POST.get("otp")  # get otp entered by user

        # check if OTP  expired ayyo — current time
        if timezone.now() > otp_record.expires_at:
            return render(
                request,
                "signup_otp_verify.html",
                {
                    "error": "OTP has expired. Please resend again.",
                    "seconds_left": 0,
                    "submitted_otp": entered_otp,
                },
            )

        if otp_record.otp_code == entered_otp:

            with transaction.atomic():
                # mark as verfied
                otp_record.is_verified = True
                otp_record.save()

                if not user.is_verified:
                    user.is_verified = True
                    user.is_active = True
                    user.security.resend_count = 0  # reset resend count
                    user.security.resend_blocked_until = None  # reset block
                    user.security.save()
                    user.save()

                    # Create wallet automatically
                    Wallet.objects.get_or_create(user=user)

                    # Give referral bonus if applicable
                    if user.referred_by:
                        referrer = user.referred_by
                        referrer_wallet, _ = Wallet.objects.get_or_create(
                            user=referrer
                        )

                        referrer_wallet.balance += 500
                        referrer_wallet.save()

                        WalletTransaction.objects.create(
                            wallet=referrer_wallet,
                            transaction_type="ADD",
                            amount=500,
                            status="COMPLETED",
                            description="referral bonus",
                        )

                        referrer.referral_count += 1
                        referrer.save()

            request.session["success_msg"] = "Account created Successfully  !"
            return redirect("signin")
        else:
            return render(
                request,
                "signup_otp_verify.html",
                {
                    "error": "Invalid OTP",
                    "seconds_left": seconds_left,
                    "submitted_otp": entered_otp,
                },
            )

    return render(
        request,
        "signup_otp_verify.html",
        {
            "seconds_left": seconds_left,
            "otp_msg": otp_msg,
        },
    )


def signup_resend_otp(request):
    email = request.session.get("email")

    try:
        user = ProfileUser.objects.get(email=email)
        # Ensure security profile exists
        UserSecurity.objects.get_or_create(user=user)
    except ProfileUser.DoesNotExist:
        return redirect("signup")

    # check if blocked
    if (
        user.security.resend_blocked_until
        and timezone.now() < user.security.resend_blocked_until
    ):
        remaining = round(
            (user.security.resend_blocked_until - timezone.now()).total_seconds() / 60
        )
        return render(
            request,
            "signup_otp_verify.html",
            {
                "error": f"Too many attempts. Try again after {remaining} minute(s).",  # noqa: E501
                "seconds_left": 0,
            },
        )

    # Check if currently block and reset
    if (
        user.security.resend_blocked_until
        and timezone.now() >= user.security.resend_blocked_until
    ):
        user.security.resend_blocked_until = None
        user.security.resend_count = 0
        user.security.save()

    if user.security.resend_count >= 3:
        user.security.resend_blocked_until = timezone.now() + timedelta(minutes=10)
        user.security.resend_count = 0
        user.security.save()

        return render(
            request,
            "signup_otp_verify.html",
            {
                "error": "Too many attempts. Try again after 10 minutes.",
                "seconds_left": 0,
            },
        )

    OTPVerification.objects.filter(user=user, is_verified=False).delete()

    otp_code = str(random.randint(1000, 9999))
    OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=1),
    )

    user.is_active = False
    user.security.resend_count += 1
    user.security.save()
    user.save()

    send_otp_email(request, user, otp_code)

    request.session["otp_msg"] = "New OTP sent to your email."
    return redirect("signup_otp_verify")


@never_cache
@unauthenticated_user
def signin_page(request):
    try:
        if request.user.is_authenticated:
            return redirect("home")
        success_msg = request.session.pop("success_msg", None)
        update_password = request.session.pop("update_password", None)
        if request.method == "POST":
            # 1. Honeypot check (Spam protection)
            if request.POST.get("website_url"):
                # If this hidden field is filled, it's a bot
                return redirect("signin")

            email = request.POST.get("email", "").strip().lower()
            password = request.POST.get("password")
            client_ip = get_client_ip(request)

            # 2. Rate Limiting Check (Brute-force protection)
            # Check failed attempts from this IP in the last 15 minutes
            time_threshold = timezone.now() - timedelta(minutes=15)
            failed_attempts = LoginAttempt.objects.filter(
                ip_address=client_ip, is_successful=False, timestamp__gte=time_threshold
            ).count()

            if failed_attempts >= 5:
                return render(
                    request,
                    "signin.html",
                    {
                        "error": "Too many failed attempts from this IP. Please try again in 15 minutes.",
                        "submitted_email": email,
                    },
                )

            if not email:
                return render(
                    request, "signin.html", {"error": "Please enter your email."}
                )

            if not password:
                return render(
                    request,
                    "signin.html",
                    {
                        "error": "Please enter your password.",
                        "submitted_email": email,
                    },
                )

            try:  # check ifexist or not
                user_obb = ProfileUser.objects.get(email=email)
                # Ensure security profile exists for the user trying to sign in
                UserSecurity.objects.get_or_create(user=user_obb)
            except ProfileUser.DoesNotExist:
                return render(
                    request,
                    "signin.html",
                    {
                        "error": "No account found with this email.",
                        "submitted_email": email,
                    },
                )

            # email
            if not user_obb.is_verified:
                return render(
                    request,
                    "signin.html",
                    {
                        "error": "Your email is not verified. Please complete signup first.",  # noqa: E501
                        "submitted_email": email,
                    },
                )

            if not user_obb.is_active:
                return render(
                    request,
                    "signin.html",
                    {
                        "error": "Your account is disabled. Please contact support.",  # noqa: E501
                        "submitted_email": email,
                    },
                )

            user = authenticate(request, username=email, password=password)

            if user:
                # 3. Log successful attempt
                LoginAttempt.objects.create(
                    ip_address=client_ip, username=email, is_successful=True
                )
                # if  everything is correct   login
                login(request, user)  # it create the seesion
                request.session["welcome"] = "Welcome to Glowé.  !"
                return redirect("home")
            else:
                # 4. Log failed attempt
                LoginAttempt.objects.create(
                    ip_address=client_ip, username=email, is_successful=False
                )
                return render(
                    request,
                    "signin.html",
                    {
                        "error": "Invalid credentials.",
                        "submitted_email": email,
                    },
                )

        return render(
            request,
            "signin.html",
            {"success_msg": success_msg, "update_password": update_password},
        )
    except Exception as e:
        import traceback
        return render(request, "signin.html", {"error": f"SYSTEM ERROR: {str(e)} | {traceback.format_exc()}"})


@never_cache
def forget_password(request):
    # Allow authenticated users too (e.g. from change password page)
    # Pre-fill their email on GET so they don't have to type it
    prefill_email = request.user.email if request.user.is_authenticated else ""

    if request.method == "POST":
        #(Spam protection)
        if request.POST.get("website_url"):
            # If this hidden field is filled, it's a bot
            return redirect("forget_password")

        email = request.POST.get("email")

        try:
            user = ProfileUser.objects.get(email=email)
            # Ensure security profile exists
            UserSecurity.objects.get_or_create(user=user)

            if user.is_active and user.is_verified:  # both checks
                # check block FIRST before anything else
                if (
                    user.security.reset_block_until
                    and timezone.now() < user.security.reset_block_until
                ):

                    # still blocked  do not send email
                    remaining_minutes = round(
                        (
                            user.security.reset_block_until - timezone.now()
                        ).total_seconds()
                        / 60
                    )
                    return render(
                        request,
                        "forget_password.html",
                        {
                            "error": f"Too many attempts. Please try again after {remaining_minutes} minute(s).",  # noqa: E501
                            "submitted_email": email,
                        },
                    )

                # save user first before generating token
                user.security.reset_attempts = 0
                user.security.reset_block_until = (
                    None  # fresh request remove any existing block
                )
                user.security.save()

                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                user.security.reset_token = token
                user.security.reset_requested_at = timezone.now()
                user.security.save()

                #  reset link
                reset_link = request.build_absolute_uri(
                    reverse(
                        "reset_password",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )

                send_password_reset_email(request, user, reset_link)

                request.session["reset_email"] = user.email

                # Store a flag so reset_password knows to redirect to change_password  # noqa: E501
                if request.user.is_authenticated:
                    request.session["reset_from_change_password"] = True
                return redirect("forget_password_link")

            else:
                return render(
                    request,
                    "forget_password.html",
                    {
                        "error": "Please verify your email before resetting your password.",  # noqa: E501
                        "submitted_email": email,
                    },
                )

        except ProfileUser.DoesNotExist:
            return render(
                request,
                "forget_password.html",
                {
                    "error": "No account found with this email.",
                    "submitted_email": email,
                },
            )

    return render(
        request, "forget_password.html", {"prefill_email": prefill_email}
    )


def forget_password_link(request):
    email = request.session.get("reset_email", "")

    if not email:
        return redirect("forget_password")

    try:
        user = ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist:
        return redirect("forget_password")

    is_blocked = False
    remaining_minutes = 0
    max_reached = False

    # check if a block exists in the database for this user
    if user.security.reset_block_until:
        if timezone.now() < user.security.reset_block_until:

            is_blocked = True
            remaining_minutes = round(
                (user.security.reset_block_until - timezone.now()).total_seconds() / 60
            )
            max_reached = True
        else:

            user.security.reset_attempts = 0
            user.security.reset_block_until = None
            user.security.save()

    return render(
        request,
        "forget_password_link.html",
        {
            "email": email,
            "is_blocked": is_blocked,
            "remaining_minutes": remaining_minutes,
            "resent_count": user.security.reset_attempts,
            "max_reached": max_reached,
        },
    )


def resend_reset_email(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forget_password")

    try:
        user = ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist:
        return redirect("forget_password")

    if user.security.reset_block_until:
        if timezone.now() < user.security.reset_block_until:

            remaining_minutes = round(
                (user.security.reset_block_until - timezone.now()).total_seconds() / 60
            )
            messages.warning(
                request,
                f"Too many attempts. Try again after {remaining_minutes} minute(s).",  # noqa: E501
            )
            return redirect("forget_password_link")
        else:

            user.security.reset_attempts = 0
            user.security.reset_block_until = None
            user.security.save()

    if user.security.reset_attempts >= 3:
        user.security.reset_block_until = timezone.now() + timedelta(minutes=15)
        user.security.reset_attempts = 0
        user.security.save()
        messages.warning(
            request, "Too many attempts. Try again after 15 minutes."
        )
        return redirect("forget_password_link")

    user.security.reset_attempts += 1
    user.security.save()

    # generate new token and save in database
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    user.security.reset_token = token
    user.security.reset_requested_at = timezone.now()
    user.security.save()

    # reset link new
    reset_link = request.build_absolute_uri(
        reverse("reset_password", kwargs={"uidb64": uid, "token": token})
    )

    send_password_reset_email(request, user, reset_link)
    messages.success(request, "Reset link sent to your email.")
    return redirect("forget_password_link")


@never_cache
def reset_password(request, uidb64, token):

    # Do NOT block authenticated users — they arrive here from the change password flow  # noqa: E501

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = ProfileUser.objects.get(pk=uid)
    except ProfileUser.DoesNotExist:
        return redirect("reset_password_invalid")

    if user.security.reset_token is None or user.security.reset_token != token:
        return redirect("reset_password_invalid")

    if user.security.reset_requested_at is None:
        return redirect("reset_password_invalid")

    expiry_time = user.security.reset_requested_at + timedelta(minutes=15)
    if timezone.now() > expiry_time:

        user.security.reset_token = None
        user.security.reset_requested_at = None
        user.security.save()
        return redirect("reset_password_invalid")

    if request.method == "POST":

        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # password validation
        pattern_password = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"
        if not re.match(pattern_password, new_password):
            return render(
                request,
                "reset_password.html",
                {
                    "error": "Password must contain upper,lower,number(8+ chars)",  # noqa: E501
                    "uidb64": uidb64,
                    "token": token,
                },
            )

        if new_password != confirm_password:
            return render(
                request,
                "reset_password.html",
                {
                    "error": "Passwords do not match.",
                    "uidb64": uidb64,
                    "token": token,
                },
            )

        # Store authentication status before password change
        is_authenticated = request.user.is_authenticated
        from_change_password = request.session.get(
            "reset_from_change_password", False
        )

        user.set_password(new_password)

        # clear reset token
        user.security.reset_token = None
        user.security.reset_requested_at = None
        user.security.reset_attempts = 0
        user.security.reset_block_until = None
        user.security.save()
        user.save()

        # If user was authenticated, keep them logged in (password change invalidates session otherwise)  # noqa: E501
        if is_authenticated:
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully.")

            # Clean up session flag
            request.session.pop("reset_from_change_password", None)

            # Redirect to change_password if they came from there, otherwise profile  # noqa: E501
            if from_change_password:
                return redirect("change_password")
            return redirect("profile_overview")

        messages.success(
            request,
            "Password reset successful. Please sign in with your new password.",  # noqa: E501
        )
        return redirect("signin")

    return render(
        request,
        "reset_password.html",
        {
            "uidb64": uidb64,
            "token": token,
        },
    )


def reset_password_invalid(request):
    return render(request, "reset_password_invalid.html")


@login_required(login_url="signin")
def referral_page(request):
    user = request.user

    # saving the user will automatically generate one via the models.py save() method.  # noqa: E501
    if not user.referral_code:
        user.save()

    wallet, _ = Wallet.objects.get_or_create(user=user)

    referred_users = ProfileUser.objects.filter(referred_by=user).order_by(
        "-date_joined"
    )
    total_earned = user.referral_count * 500

    context = {
        "user": user,
        "wallet_balance": wallet.balance,
        "referred_users": referred_users,
        "total_earned": total_earned,
    }

    return render(request, "referral.html", context)
