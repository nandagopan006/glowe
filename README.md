<div align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&pause=1000&color=2563EB&center=true&vCenter=true&width=600&lines=Modern+Full-Stack+eCommerce+Platform;Built+with+Django+%26+Tailwind+CSS;A+Premium+Shopping+Experience" alt="Typing SVG" />
  
  <h1>✨ Glowé </h1>
  
  <p><strong>A fully-featured, production-ready online shopping system designed to simulate a real-world premium brand.</strong></p>

  <!-- Badges -->
  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white" alt="Python Version" />
    <img src="https://img.shields.io/badge/Django-5.0+-092E20.svg?logo=django&logoColor=white" alt="Django Version" />
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
    <img src="https://img.shields.io/github/last-commit/yourusername/glowe.svg" alt="Last Commit" />
    <img src="https://img.shields.io/github/repo-size/yourusername/glowe.svg" alt="Repo Size" />
  </p>
</div>

---

## 📸 Project Preview

Get a glimpse of the Glowé eCommerce platform. *(Replace placeholder paths with your actual images)*

| 🏠 Home Page | 📦 Product Details |
| :---: | :---: |
| <img src="docs/screenshots/home.png" alt="Home Page" width="400" /> | <img src="docs/screenshots/product.png" alt="Product Details" width="400" /> |

| 🛒 Shopping Cart | 📊 Admin Dashboard |
| :---: | :---: |
| <img src="docs/screenshots/cart.png" alt="Shopping Cart" width="400" /> | <img src="docs/screenshots/admin.png" alt="Admin Dashboard" width="400" /> |

---

## 📖 About The Project

**Glowé** is a complete, end-to-end eCommerce system engineered to emulate a real-world online storefront. 

Built with scalability and user experience in mind, this platform allows customers to effortlessly browse products, manage their cart, and complete purchases securely. Simultaneously, it provides store owners with a powerful, custom-built administrative backend to manage inventory, process orders, and oversee the entire user base.

---

## ✨ Core Features

### 👤 User Side
*   **Authentication:** Secure user registration, login, and Google OAuth integration.
*   **Discovery:** Browse products seamlessly by category with dynamic filtering.
*   **Immersive Views:** Detailed product pages featuring an interactive modal UI.
*   **Cart Management:** Effortlessly add to cart, update quantities, or remove items.
*   **Secure Checkout:** Smooth checkout process integrated with digital wallets and Razorpay.
*   **Order Tracking:** Comprehensive order history and status tracking.
*   **Community:** Built-in review and rating system for verified purchases.

### 🛠️ Admin Side
*   **Analytics Dashboard:** High-level overview of sales, active orders, and revenue.
*   **Inventory Control:** Comprehensive product management (add, edit, delete, and variant handling).
*   **Order Fulfillment:** Advanced order management system with status updates and return processing.
*   **Automated Invoicing:** Seamless PDF invoice generation for every transaction.
*   **User Management:** Oversee registered users, profiles, and wallet balances.

---

## 🛠️ Tech Stack

*   **Backend:** Python, Django
*   **Frontend:** HTML5, CSS3, JavaScript, Tailwind CSS
*   **Database:** PostgreSQL (Production) 
*   **Others:** Pillow (Image Processing), OpenPyXL (Excel Export), ReportLab (PDFs), Razorpay (Payments)

---

## 🚀 Installation Guide

Follow these steps to deploy the project locally:

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/glowe.git
cd glowe
```

**2. Create a virtual environment**
```bash
# Windows
python -m venv myenv

# macOS/Linux
python3 -m venv myenv
```

**3. Activate the environment**
```bash
# Windows
myenv\Scripts\activate

# macOS/Linux
source myenv/bin/activate
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Run database migrations**
```bash
cd glowe
python manage.py makemigrations
python manage.py migrate
```

**6. Start the server**
```bash
python manage.py runserver
```

---

## 🔄 Usage Flow

1.  **Discovery:** The user visits the site and browses the catalog or searches for specific items.
2.  **Selection:** The user views a product's details and adds their desired variant to the cart.
3.  **Checkout:** The user proceeds to checkout, applying any available coupons and completing payment.
4.  **Fulfillment:** The admin receives the order on the dashboard, updates its status to "Shipped", and eventually "Delivered".
5.  **Completion:** The user receives their automated PDF invoice and tracks the delivery status in their profile.

---

## 📁 Project Structure

```text
glowe/
├── accounts/         # User authentication & profiles
├── adminpanel/       # Custom backend management dashboard
├── cart/             # Shopping cart functionality
├── order/            # Checkout, invoices, & tracking
├── payment/          # Razorpay & wallet integrations
├── product/          # Catalog, variants, & categories
├── static/           # CSS, JavaScript, & Tailwind assets
├── templates/        # HTML templates
└── manage.py         # Django application entry point
```

---

## 🔐 Environment Variables

Create a `.env` file in the root directory and configure it as follows:

```env
# Core Django
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database Configuration (PostgreSQL)
DB_NAME=glowe_db
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Razorpay Integration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

---

## 🚀 Future Improvements

*   ✅ Multi-Payment Gateway Integration (Stripe/PayPal)
*   ✅ Advanced Filtering & Full-Text Search Optimization
*   ✅ Image Caching & Performance Optimization
*   ✅ AI intergration(for product recommendations and also to make our website more interactive)

---

<div align="center">
  <i>If you found this project helpful, please give it a ⭐️ on GitHub!</i>
</div>