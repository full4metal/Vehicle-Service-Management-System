
# 🚗 Vehicle Service Management System (VSMS)

A web-based application built using **Python Flask** and **MySQL** that automates and streamlines the process of managing vehicle service requests. This system allows service centers to manage customers, mechanics, service histories, invoices, and parts inventory efficiently.

---

## 🧾 Project Overview

The **Vehicle Service Management System** is designed to eliminate the need for manual record-keeping and provide a centralized platform where:
- **Admins** manage users, service assignments, invoices, and reports.
- **Customers** book service requests, track progress, and manage their vehicle profiles.
- **Mechanics** handle assigned jobs, update statuses, and request parts.

The system enhances service quality, improves transparency, and reduces administrative overhead in vehicle service centers.

---

## ✨ Features

### 🔐 Authentication
- Secure login and registration for Admin, Customer, and Mechanic roles

### 👥 User Roles
- **Admin:** Manage customers, mechanics, services, invoices, and reports
- **Customer:** Add vehicles, request services, view history and invoices
- **Mechanic:** View assigned services, update progress, request part replacements

### 🧾 Service & Invoice Management
- Create and manage service requests
- Auto-generate and view invoices
- Approve part replacements

### 📊 Reporting
- Generate reports for services, invoices, payments, and mechanic performance

### 📍 Location Services
- Integrated with Google Maps API for roadside assistance requests

---

## 🛠️ Tech Stack

| Layer         | Technology            |
|---------------|------------------------|
| Frontend      | HTML, CSS, JavaScript |
| Backend       | Python Flask           |
| Database      | MySQL (WAMP Server)    |
| APIs          | Google Maps API        |
| IDE           | VS Code                |
| OS            | Windows 11             |

---

## 🧩 Database Schema Overview

Tables include:
- `admin`
- `customer`
- `mechanic`
- `vehicle`
- `service_request`
- `service_cost`
- `invoice`

All tables are linked using primary/foreign key constraints to maintain relational integrity.

---


## 🚀 Getting Started

### 🔧 Prerequisites
- Python 3.x
- MySQL (WAMP/XAMPP)
- Flask (`pip install flask`)
- Flask-MySQLdb (`pip install flask-mysqldb`)

### 🔌 Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/vehicle-service-management-system.git
   cd vehicle-service-management-system
````

2. **Set Up the Database**

   * Import the `vsms.sql` file into your MySQL server.
   * Update the database credentials in `app.py`.

3. **Run the Application**

   ```bash
   python app.py
   ```

4. **Open in Browser**

   * Visit `http://localhost:5000`

---

## 🧪 Testing

The system has been tested with:

* Valid/invalid login credentials
* Duplicate and missing data entries
* Service request workflows
* Invoice generation and approval

---

## 🧠 Lessons Learned

This project gave me hands-on experience in full-stack development, user authentication, CRUD operations, database modeling, and real-world deployment using Flask and MySQL.

---

## 📌 Project Status

✅ Fully functional and tested
🔧 Future improvements: Add multilingual support, and mobile responsiveness

---

## 📸 Screenshots

Screenshots:

![image](https://github.com/user-attachments/assets/b3729acd-65a9-48ea-8aa4-04d7e67b9c09)

![image](https://github.com/user-attachments/assets/90999ab4-ae13-4556-8814-309b90e19ae0)

![image](https://github.com/user-attachments/assets/72c90003-6655-4946-9da2-33264c689bda)

![image](https://github.com/user-attachments/assets/07bda548-bcce-4b77-b974-e096f93dd72b)
