from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    is_superadmin = db.Column(db.Boolean, default=False)  # True = Admin Mkuu

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class GodownItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    product_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)

    is_posted = db.Column(db.Boolean, default=False)  # Has been posted to homepage
    is_published = db.Column(db.Boolean, default=False)
    is_new_arrival = db.Column(db.Boolean, default=False)
    is_best_seller = db.Column(db.Boolean, default=False)
    discount_percentage = db.Column(db.Integer, default=0)  # e.g., 15 means 15% off
    discount_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    date_added = db.Column(db.Date, default=datetime.utcnow) 

    # NEW: Add category_type column
    category_type = db.Column(
        db.String(20), default="normal"
    )  # normal, new, best, discount

    def to_dict(self):
        return {
            "id": self.id,
            "product_name": self.product_name,
            "product_type": self.product_type,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "image_filename": self.image_filename,
            "is_posted": self.is_posted,
            "is_published": self.is_published,
            "is_new_arrival": self.is_new_arrival,
            "is_best_seller": self.is_best_seller,
            "discount_percentage": self.discount_percentage,
            "date_added":self.date_added,
            "discount_expiry": (
                self.discount_expiry.isoformat() if self.discount_expiry else None
            ),
            "created_at": self.created_at.isoformat(),
            "category_type": self.category_type,  # Include category_type in dict
        }
  

class WorkshopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(200), nullable=False)
    product_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float, default=0.0)
    date_added = db.Column(db.Date, nullable=True)
    image_filename = db.Column(db.String(300), nullable=True)

    is_posted = db.Column(db.Boolean, default=False)

    # Posting info
    category_type = db.Column(db.String(50), default='normal')  # normal, new, best, discount
    discount_percentage = db.Column(db.Integer, default=0)
    discount_expiry = db.Column(db.Date, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "product_name": self.product_name,
            "product_type": self.product_type,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "date_added": self.date_added.isoformat() if self.date_added else None,
            "image_filename": self.image_filename,
            "category_type": self.category_type,
            "discount_percentage": self.discount_percentage,
            "discount_expiry": self.discount_expiry.isoformat() if self.discount_expiry else None,
        } 

  




class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.String(200), nullable=False)  # Email ya mteja
    location = db.Column(db.String(255), nullable=True)  # Location mpya
    delivery_option = db.Column(db.String(10), nullable=True)  # Yes / No
    order_items = db.Column(db.Text, nullable=False)  # JSON string ya bidhaa
    total_price = db.Column(db.Float, nullable=False)
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, confirmed, paid, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_address": self.customer_email,
            "location": self.location,
            "delivery_option": self.delivery_option,
            "order_items": self.order_items,
            "total_price": self.total_price,
            "status": self.status,
            "date_ordered": (
                self.date_ordered.isoformat() if self.date_ordered else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ManualOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # ✅ auto-increment
    customer_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(200), default="")
    items = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), default="cash")
    total_price = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="pending")
    
    # Delivery fields
    delivery_option = db.Column(db.String(10), default="")
    delivery_location = db.Column(db.String(200), default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ fixed

    def __repr__(self):
        return f"<ManualOrder {self.id} - {self.customer_name}>"



class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    subject = db.Column(db.String(150))
    content = db.Column(db.Text)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)


class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    subscribed_on = db.Column(db.DateTime, default=datetime.utcnow)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.Float, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    month_paid = db.Column(db.String(20), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)


# model mpya

