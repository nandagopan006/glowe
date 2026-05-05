/**
 * Glowé E-Commerce AJAX Handlers
 * Handles Cart, Wishlist, Coupons, and dynamic UI updates
 */

$(document).ready(function() {
    // ── ADD TO CART ──
    $(document).on('click', '.btn-add-to-cart', function(e) {
        e.preventDefault();
        const $btn = $(this);
        const variantId = $btn.data('variant-id');
        const quantity = $('#qtyInput').val() || $('#qty-input').val() || 1;
        const url = $btn.data('url') || '/cart/add/' + variantId + '/';

        if ($btn.hasClass('ajax-loading')) return;

        setButtonLoading($btn, true);

        $.ajax({
            url: url,
            type: 'POST',
            data: {
                'variant_id': variantId,
                'quantity': quantity,
                'ajax': 'true'
            },
            success: function(response) {
                setButtonLoading($btn, false);
                if (response.success) {
                    Toast.success(response.message || 'Added to cart!');
                    if (response.data && response.data.cart_count !== undefined) {
                        updateCartBadge(response.data.cart_count);
                    }
                } else {
                    Toast.error(response.message || 'Failed to add to cart');
                }
            },
            error: function() {
                setButtonLoading($btn, false);
                Toast.error('An error occurred. Please try again.');
            }
        });
    });

    // ── TOGGLE WISHLIST ──
    $(document).on('click', '.btn-wishlist', function(e) {
        e.preventDefault();
        const $btn = $(this);
        const url = $btn.data('url');

        if ($btn.hasClass('ajax-loading')) return;
        $btn.addClass('ajax-loading');

        $.ajax({
            url: url,
            type: 'POST',
            data: { 'ajax': 'true' },
            success: function(response) {
                $btn.removeClass('ajax-loading');
                if (response.success) {
                    Toast.success(response.message);
                    // Update icon state and classes
                    if (response.data.action === 'added') {
                        $btn.addClass('wishlisted pop').find('svg').attr('fill', 'currentColor');
                    } else {
                        $btn.removeClass('wishlisted').addClass('pop').find('svg').attr('fill', 'none');
                    }
                    setTimeout(() => $btn.removeClass('pop'), 500);

                    if (response.data.wishlist_count !== undefined) {
                        $('.wishlist-count').text(response.data.wishlist_count);
                    }
                } else {
                    if (response.message.includes('login')) {
                        window.location.href = '/accounts/signin/';
                    } else {
                        Toast.error(response.message);
                    }
                }
            },
            error: function() {
                $btn.removeClass('ajax-loading');
                Toast.error('An error occurred.');
            }
        });
    });

    // ── CART QUANTITY UPDATE ──
    $(document).on('change', '.cart-qty-input', function() {
        const $input = $(this);
        const cartId = $input.data('cart-id');
        const qty = $input.val();
        const url = $input.data('url') || '/cart/update/' + cartId + '/';

        if (qty < 1) return;

        $.ajax({
            url: url,
            type: 'POST',
            data: { 'quantity': qty, 'ajax': 'true' },
            success: function(response) {
                if (response.success) {
                    // Update row subtotal and total
                    $(`#item-total-${cartId}`).text('₹' + response.data.item_total);
                    $('#cart-subtotal').text('₹' + response.data.cart_total);
                    $('#cart-total').text('₹' + response.data.cart_total);
                    updateCartBadge(response.data.cart_count);
                } else {
                    Toast.error(response.message);
                    // Reset input to previous value if provided
                    if (response.data.current_qty) {
                        $input.val(response.data.current_qty);
                    }
                }
            }
        });
    });
});
