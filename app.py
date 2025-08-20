from flask import Flask, request, jsonify, send_from_directory,session,Blueprint
import smtplib
from utilis import send_email
from sqlalchemy import func
import os
import traceback
from dotenv import load_dotenv
import jwt
from flask_mail import Message as MailMessage,Mail
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime, date
from flask import jsonify, send_file
from flask import Blueprint
from routes import auth_bp
import secrets
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from flask_cors import CORS
from email.message import EmailMessage
from werkzeug.utils import secure_filename
from models import (
    db,
    GodownItem,
    Order,
    Admin,
    ManualOrder,
    Subscriber,
    WorkshopItem,
    ContactMessage,
    Employee,
    Video,
)  # Hakikisha model yako ina field category_type
import os
import json


load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)


# Database config
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///furniture.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False




db.init_app(app)
migrate = Migrate(app, db)


@app.route("/")
def home():
    return jsonify({"message": "Flask backend is live!"})


# Create Admin
@app.route('/api/admins/register', methods=['POST'])
def register_admin():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    is_superadmin = data.get("is_superadmin", False)

    # check kama email tayari ipo
    existing = Admin.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Email already registered"}), 400

    if Admin.query.count() >= 4:
        return jsonify({"error": "Maximum 4 admins allowed"}), 400

    new_admin = Admin(
        username=username,
        email=email,
        is_superadmin=is_superadmin
    )
    new_admin.set_password(password)
    db.session.add(new_admin)
    db.session.commit()

    return jsonify({"message": "Admin registered successfully"}), 201


# Login Admin
@app.route('/api/admins/login', methods=['POST'])
def login_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    admin = Admin.query.filter_by(username=username).first()
    if admin and admin.check_password(password):
        session['admin_id'] = admin.id
        session['is_superadmin'] = admin.is_superadmin
        return jsonify({"message": "Login success", "is_superadmin": admin.is_superadmin})
    return jsonify({"error": "Invalid credentials"}), 401

# Logout
@app.route('/api/admins/logout', methods=['POST'])
def logout_admin():
    session.clear()
    return jsonify({"message": "Logged out"})


# Create the tables if they don’t exist
with app.app_context():
    db.create_all()


# Register Blueprint
app.register_blueprint(auth_bp)


UPLOAD_FOLDER = "videos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Create folders if not exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Configuration ya Gmail SMTP
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "mbarouktechcreation@gmail.com"  # tumia Gmail yako
app.config["MAIL_PASSWORD"] = "guyh frqc xqnw krfy"  # App Password ya Gmail

mail = Mail(app)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS




# Add new item to godown
@app.route("/api/godown", methods=["POST"])
def add_to_godown():
    data = request.form
    file = request.files.get("image")

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    else:
        filename = None

    try:
        # Parse tarehe kutoka form data (inakuwa "YYYY-MM-DD")
        date_str = data.get("date_added")
        date_added = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else datetime.utcnow().date()
        )

        item = GodownItem(
            product_name=data.get("product_name"),
            product_type=data.get("product_type"),
            quantity=int(data.get("quantity", 0)),
            unit_price=float(data.get("unit_price", 0)),
            image_filename=filename,
            discount_percentage=int(data.get("discount_percentage") or 0),
            discount_expiry=data.get("discount_expiry") or None,
            category_type=data.get("category_type") or "normal",
            is_posted=False,
            date_added=date_added,  # ✅ Tumetumia hapa
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Imeongezwa kwenye godown"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/godown", methods=["GET"])
def get_all_items():
    items = GodownItem.query.all()
    output = []
    for item in items:
        output.append(
            {
                "id": item.id,
                "product_name": item.product_name,
                "product_type": item.product_type,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "image": item.image_filename,
                "discount_percentage": item.discount_percentage,
                "discount_expiry": (
                    item.discount_expiry.isoformat() if item.discount_expiry else None
                ),
                "category_type": item.category_type,
                "is_posted": item.is_posted,
                "date_added": item.date_added.isoformat() if item.date_added else None,
            }
        )
    return jsonify(output)


# Post product to homepage (publish it)


@app.route("/api/godown/post/<int:item_id>", methods=["PATCH"])
def post_to_homepage(item_id):
    item = db.session.get(GodownItem, item_id)
    if not item:
        return jsonify({"error": "Product not found"}), 404

    data = request.json or {}
    item.is_posted = True
    item.category_type = data.get("category_type")
    item.unit_price = data.get("unit_price", item.unit_price)

    # Handle discount if applicable
    if item.category_type == "discount":
        item.discount_percentage = data.get("discount_percentage", 0)
        expiry_str = data.get("discount_expiry")
        if expiry_str:
            try:
                item.discount_expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                return (
                    jsonify(
                        {"error": "Invalid discount_expiry format. Use YYYY-MM-DD."}
                    ),
                    400,
                )
        else:
            item.discount_expiry = None
    else:
        item.discount_percentage = 0
        item.discount_expiry = None

    try:
        db.session.commit()

        # ⏩ After committing, send email to all subscribers
        subscribers = Subscriber.query.all()
        subject = f"📢 Bidhaa Mpya: {item.product_name}"
        message_body = f"""
Habari!

Bidhaa mpya imeongezwa kwenye duka letu: {item.product_name}
Aina: {item.product_type}
Bei: {item.unit_price} TZS

Tembelea tovuti yetu kuona zaidi. Usikose ofa kama ipo!

Asante kwa kuwa sehemu ya wateja wetu.
"""

        for sub in subscribers:
            try:
                msg = MailMessage(
                    subject=subject,
                    sender="mbarouktechcreation@gmail.com",  # 🔁 badilisha kwa email yako
                    recipients=[sub.email],
                    body=message_body,
                )
                mail.send(msg)
            except Exception as e:
                print(f"Failed to send email to {sub.email}: {str(e)}")

        return jsonify({"message": "Product posted successfully and emails sent!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Get all posted items (published products)


@app.route("/api/godown/posted", methods=["GET"])
def get_posted_items():
    now = datetime.utcnow()

    # Step 1: Safisha discount zilizopitwa
    expired_items = GodownItem.query.filter(
        GodownItem.is_posted == True,
        GodownItem.discount_expiry != None,
        GodownItem.discount_expiry < now,
    ).all()

    for item in expired_items:
        item.discount_percentage = 0
        item.category_type = "normal"
        item.discount_expiry = None
    db.session.commit()

    # Step 2: Rudi bidhaa zote zilizo-postiwa
    items = GodownItem.query.filter_by(is_posted=True).all()
    result = []
    for item in items:
        result.append(item.to_dict())
    return jsonify(result)


# Get all godown items (not necessarily posted)


@app.route("/api/godown/<int:id>", methods=["DELETE"])
def delete_godown_item(id):
    item = db.session.get(GodownItem, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@app.route("/api/godown/<int:id>", methods=["PUT"])
def edit_item(id):
    item = db.session.get(GodownItem, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    data = request.form
    image = request.files.get("image")

    # Update fields
    item.product_name = data.get("product_name", item.product_name)
    item.product_type = data.get("product_type", item.product_type)
    item.quantity = int(data.get("quantity", item.quantity))
    item.unit_price = float(data.get("unit_price", item.unit_price))
    item.date_added = data.get("date_added", item.date_added)

    if image:
        # Save image to uploads folder
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        item.image = image_filename

    try:
        db.session.commit()
        return jsonify(item.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# Uploads serving
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)






# #  WORKSHOP ROUTES
# =========================

WORKSHOP_UPLOAD_FOLDER = "uploads_workshop"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg","gif"}

app.config["WORKSHOP_UPLOAD_FOLDER"] = WORKSHOP_UPLOAD_FOLDER
os.makedirs(WORKSHOP_UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads_workshop/<filename>')
def uploaded_workshop_file(filename):
    return send_from_directory(app.config['WORKSHOP_UPLOAD_FOLDER'], filename)


# =========================
# Add new workshop item
# =========================
@app.route("/api/workshop", methods=["POST"])
def add_workshop_item():
    data = request.form
    file = request.files.get("image")

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["WORKSHOP_UPLOAD_FOLDER"], filename))
    else:
        filename = None

    try:
        date_str = data.get("date_added")
        date_added = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()

        item = WorkshopItem(
            product_name=data.get("product_name"),
            product_type=data.get("product_type"),
            quantity=int(data.get("quantity", 0)),
            unit_price=float(data.get("unit_price", 0)),
            image_filename=filename,
            discount_percentage=int(data.get("discount_percentage") or 0),
            discount_expiry=data.get("discount_expiry") or None,
            category_type=data.get("category_type") or "normal",
            is_posted=False,
            date_added=date_added
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# =========================
# Get all workshop items
# =========================
@app.route("/api/workshop", methods=["GET"])
def get_all_workshop_items():
    items = WorkshopItem.query.order_by(WorkshopItem.date_added.desc()).all()
    result = []
    for item in items:
        data = item.to_dict()
        data["image"] = f"/uploads_workshop/{item.image_filename}" if item.image_filename else None
        result.append(data)
    return jsonify(result)


# =========================
# Post workshop item
# =========================
@app.route("/api/workshop/post/<int:item_id>", methods=["PATCH"])
def post_workshop_item(item_id):
    item = db.session.get(WorkshopItem, item_id)
    if not item:
        return jsonify({"error": "Product not found"}), 404

    data = request.json or {}
    item.is_posted = True
    item.category_type = data.get("category_type")
    item.unit_price = data.get("unit_price", item.unit_price)

    # Handle discount if applicable
    if item.category_type == "discount":
        item.discount_percentage = data.get("discount_percentage", 0)
        expiry_str = data.get("discount_expiry")
        if expiry_str:
            try:
                item.discount_expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                return (
                    jsonify({"error": "Invalid discount_expiry format. Use YYYY-MM-DD."}),
                    400,
                )
        else:
            item.discount_expiry = None
    else:
        item.discount_percentage = 0
        item.discount_expiry = None

    try:
        db.session.commit()

        # ⏩ After committing, send email to all subscribers
        subscribers = Subscriber.query.all()
        subject = f"📢 Bidhaa Mpya: {item.product_name}"
        message_body = f"""
Habari!

Bidhaa mpya imeongezwa kwenye duka letu: {item.product_name}
Aina: {item.product_type}
Bei: {item.unit_price} TZS

Tembelea tovuti yetu kuona zaidi. Usikose ofa kama ipo!

Asante kwa kuwa sehemu ya wateja wetu.
"""

        for sub in subscribers:
            try:
                msg = MailMessage(
                    subject=subject,
                    sender="mbarouktechcreation@gmail.com",  # badilisha kama inahitajika
                    recipients=[sub.email],
                    body=message_body,
                )
                mail.send(msg)
            except Exception as e:
                print(f"Failed to send email to {sub.email}: {str(e)}")

        return jsonify({"message": "Workshop item posted successfully and emails sent!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =========================
# Get all posted workshop items
# =========================
@app.route("/api/workshop/posted", methods=["GET"])
def get_posted_workshop_items():
    now = datetime.utcnow()

    # 1️⃣ Safisha discount zilizopitwa
    expired_items = WorkshopItem.query.filter(
        WorkshopItem.is_posted == True,
        WorkshopItem.discount_expiry != None,
        WorkshopItem.discount_expiry < now,
    ).all()

    for item in expired_items:
        item.discount_percentage = 0
        item.category_type = "normal"
        item.discount_expiry = None

    db.session.commit()

    # 2️⃣ Rudi bidhaa zote zilizo-postiwa
    items = WorkshopItem.query.filter_by(is_posted=True).all()
    results = []
    for item in items:
        item_data = item.to_dict()  # Hakikisha to_dict() inatoa jina, type, unit_price, quantity, image_filename
        # Add image path + cache buster
        if getattr(item, "image_filename", None):
            item_data["image"] = f"/uploads_workshop/{item.image_filename}?v={datetime.utcnow().timestamp()}"
        else:
            item_data["image"] = None
        
        # Include source for frontend usage (UI haionyeshi)
        item_data["source"] = "workshop"

        results.append(item_data)  # 🔹 append lazima iwe ndani ya loop

    return jsonify(results)


# =========================
# Delete workshop item
# =========================
@app.route("/api/workshop/<int:id>", methods=["DELETE"])
def delete_workshop_item(id):
    item = db.session.get(WorkshopItem, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200













# Orders endpoints


# ✅ ENDPOINT: Thibitisha Oda
@app.route("/api/orders/confirm/<int:order_id>", methods=["POST"])
def confirm_order(order_id):
    try:
        # Pata online order pekee
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        if order.status == "paid":
            return jsonify({"message": "Order already confirmed"}), 400

        # Thibitisha malipo
        order.status = "paid"

        # Punguza stock kulingana na source ya kila item
        try:
            order_items = json.loads(order.order_items or "[]")
        except Exception:
            return jsonify({"error": "Invalid order_items format"}), 400

        print(f"Confirming Order #{order.id}, total items: {len(order_items)}")

        for item in order_items:
            product_name = item.get("product_name")
            quantity = int(item.get("quantity", 0))
            item_source = item.get("source", "").lower()  # godown au workshop

            stock_item = None
            if item_source == "godown":
                stock_item = GodownItem.query.filter_by(product_name=product_name).first()
            elif item_source == "workshop":
                stock_item = WorkshopItem.query.filter_by(product_name=product_name).first()

            if stock_item and stock_item.quantity is not None:
                before_qty = stock_item.quantity
                stock_item.quantity = max(stock_item.quantity - quantity, 0)
                print(f"Reduced {quantity} of '{product_name}' from {item_source}. Stock: {before_qty} -> {stock_item.quantity}")
            else:
                print(f"Item '{product_name}' not found in {item_source} or quantity is None")

        # Tuma email kwa mteja
        try:
            email_body = f"""
Habari {order.customer_name},

Malipo yako kwa oda #{order.id} yamepokelewa kwa mafanikio.

Jumla: {order.total_price:,} TZS

Asante kwa kununua kwetu!

---
Timu ya Duka
"""
            send_email(
                to=order.customer_address,
                subject=f"Uthibitisho wa Malipo ya Oda #{order.id}",
                body=email_body,
            )
        except Exception as e:
            print("Email sending error:", str(e))

        db.session.commit()
        print(f"Order #{order.id} confirmed successfully!")
        return jsonify({"message": "Online order confirmed and email sent", "status": "paid"}), 200

    except Exception as e:
        db.session.rollback()
        print("Confirm order failed:", str(e))
        return jsonify({"error": str(e)}), 500



# hapa ni kucreate order
@app.route("/api/orders", methods=["POST"])
def create_order():
    try:
        data = request.get_json()

        # Hakikisha input zote muhimu zipo
        required_fields = [
            "customer_name",
            "customer_phone",
            "customer_address",  # Email
            "location",
            "delivery_option",
            "order_items",
            "total_price",
        ]
        for field in required_fields:
            if field not in data or str(data[field]).strip() == "":
                return jsonify({"error": f"Field '{field}' is required"}), 400

        # Hakikisha email inaishia na @gmail.com
        if not str(data["customer_address"]).lower().endswith("@gmail.com"):
            return jsonify({"error": "Email lazima iishie na @gmail.com"}), 400

        # Hakikisha order_items iko kama list
        if not isinstance(data["order_items"], list):
            return jsonify({"error": "order_items must be a list"}), 400

        # Unda order mpya
        order = Order(
            customer_name=data["customer_name"].strip(),
            customer_phone=data["customer_phone"].strip(),
            customer_address=data["customer_address"].strip(),
            location=data["location"].strip(),
            delivery_option=str(data.get("delivery_option", "No")).strip(),
            order_items=json.dumps(data.get("order_items", [])),
            total_price=float(data.get("total_price", 0)),
            status="pending",  # default status
            date_ordered=datetime.utcnow(),  # default timestamp
        )
        db.session.add(order)
        db.session.commit()

        # Optional: email sending
        try:
            items_desc = "\n".join(
                [
                    f"{item['product_name']} x {item['quantity']} = TZS {item['price'] * item['quantity']:,}"
                    for item in data["order_items"]
                ]
            )

            subject = "Oda Yako Imepokelewa - Asante kwa kununua!"
            body = (
                f"Habari {data['customer_name']},\n\n"
                f"Oda yako imepokelewa!\n\n"
                f"Mahali pa kufikisha: {data['location']}\n"
                f"Chaguo la delivery: {data['delivery_option']}\n\n"
                f"Bidhaa:\n{items_desc}\n\n"
                f"Jumla ya malipo: TZS {data['total_price']:,}\n"
                f"Malipo yafanyike kwa namba: 0712345678\n\n"
                f"Asante, Karibu Sana Mkombozi Furniture"
            )

            sender_email = "mbarouktechcreation@gmail.com"
            sender_password = "guyh frqc xqnw krfy"
            receiver_email = data["customer_address"]

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
        except Exception as e:
            print("Email sending failed:", str(e))

        return jsonify({
            "message": "Order received successfully",
            "order_id": order.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders", methods=["GET"])
def get_orders():
    try:
        online_orders = Order.query.all()


        result = []

        # Online Orders
        for order in online_orders:
            result.append({
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_address": order.customer_address or "",
                "location": order.location or "Haijatajwa",
                "delivery_option": order.delivery_option.strip().capitalize() if order.delivery_option else "No",
                "order_items": json.loads(order.order_items or "[]"),
                "total_price": order.total_price,
                "status": order.status or "pending",
                "date_ordered": (order.date_ordered.strftime("%Y-%m-%d %H:%M") 
                                 if order.date_ordered else datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
                "source": "online",
            })

        return jsonify({"orders": result})

    except Exception as e:
        print("GET orders failed:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders/<int:order_id>/update-delivery", methods=["POST"])
def update_delivery_fee(order_id):
    data = request.get_json()
    fee = data.get("delivery_fee", 0)
    
    order = Order.query.get(order_id) or ManualOrder.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    order.delivery_fee = float(fee)
    order.total_price = float(order.total_price) + float(fee)  # optional: update total in db
    db.session.commit()
    
    return jsonify({"message": "Delivery fee updated successfully", "total_price": order.total_price})




@app.route("/api/products", methods=["GET"])
def get_filtered_products():
    category_type = request.args.get("category_type")
    query = GodownItem.query.filter_by(is_posted=True)

    if category_type:
        query = query.filter_by(category_type=category_type)

    items = query.all()

    result = [
        {
            "id": item.id,
            "product_name": item.product_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "category_type": item.category_type,
            "product_type": item.product_type,
            "discount_percentage": item.discount_percentage,
            "discount_expiry": item.discount_expiry,
            "image_filename": item.image_filename,
            "is_posted": item.is_posted,
        }
        for item in items
    ]

    return jsonify(result)

    # Route za Video


# Get all videos from DB
@app.route("/api/videos/all", methods=["GET"])
def get_all_videos_db():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": v.id,
                "title": v.title,
                "url": v.url,
                "views": v.views,
                "created_at": v.created_at.isoformat(),
            }
            for v in videos
        ]
    )


# Get latest video from DB
@app.route("/api/videos/latest", methods=["GET"])
def get_latest_video_db():
    latest_video = Video.query.order_by(Video.created_at.desc()).first()
    if latest_video:
        return jsonify(
            {
                "id": latest_video.id,
                "title": latest_video.title,
                "url": latest_video.url,
                "views": latest_video.views,
                "created_at": latest_video.created_at.isoformat(),
            }
        )
    return jsonify({"error": "No video found"}), 404


# Upload video and save to DB & filesystem
@app.route("/upload-video", methods=["POST"])
def upload_video():
    video = request.files.get("video")
    title = request.form.get("title", "Untitled")

    if not video:
        return jsonify({"error": "No video provided"}), 400

    filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + video.filename
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    video.save(filepath)

    new_video = Video(title=title, url=f"/videos/{filename}")
    db.session.add(new_video)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Video uploaded and saved to database successfully",
                "video": {
                    "id": new_video.id,
                    "title": new_video.title,
                    "url": new_video.url,
                    "views": new_video.views,
                    "created_at": new_video.created_at.isoformat(),
                },
            }
        ),
        201,
    )


@app.route("/api/videos/<int:video_id>", methods=["DELETE"])
def delete_video(video_id):
    try:
        video = Video.query.get(video_id)
        if not video:
            return jsonify({"error": "Video haipo"}), 404

        db.session.delete(video)
        db.session.commit()

        return jsonify({"message": "Video imefutwa kikamilifu"}), 200
    except Exception as e:
        print("Error deleting video:", str(e))
        return jsonify({"error": "Imeshindikana kufuta video"}), 500



# Serve uploaded video files
@app.route("/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Increment view count
@app.route("/api/videos/<int:video_id>/view", methods=["POST"])
def increment_video_views(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()
    return jsonify({"message": "View counted"})


#   Generate daily report
@app.route("/api/reports/daily/export-pdf", methods=["GET"])
def export_daily_report_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    import io

    today = request.args.get("date")
    if today:
        try:
            today = datetime.strptime(today, "%Y-%m-%d").date()
        except:
            return jsonify({"error": "Tarehe si sahihi, tumia YYYY-MM-DD"}), 400
    else:
        today = date.today()

    orders_today = Order.query.filter(func.date(Order.date_ordered) == today).all()

    # --- Pata Bidhaa zilizonunuliwa --- 
    workshop_items = {}
    godown_items_purchased = {}

    for order in orders_today:
        try:
            items = json.loads(order.order_items)
            for item in items:
                name = item.get("product_name", "Haijulikani")
                qty = item.get("quantity", 0)
                price = item.get("unit_price", None)
                source = item.get("source", "").strip().lower()  # workshop or godown
                product_type = item.get("product_type", "-")

                if price is None or price == 0:
                    godown_item = GodownItem.query.filter_by(product_name=name).first()
                    price = godown_item.unit_price if godown_item else 0.0
                price = float(price)
                subtotal = qty * price

                target_dict = workshop_items if source == "workshop" else godown_items_purchased

                if name not in target_dict:
                    target_dict[name] = {
                        "quantity": qty,
                        "unit_price": price,
                        "subtotal": subtotal,
                        "product_type": product_type,
                    }
                else:
                    target_dict[name]["quantity"] += qty
                    target_dict[name]["subtotal"] += subtotal
        except Exception as e:
            print("Error parsing order_items:", e)
            continue

    # --- Stock ---
    godown_stock_items = GodownItem.query.all()
    in_stock = []
    out_of_stock = []
    for item in godown_stock_items:
        entry = {
            "product_name": item.product_name,
            "product_type": item.product_type,
            "quantity": item.quantity,
            "status": "Imeisha" if item.quantity == 0 else "Inapatikana",
        }
        if item.quantity > 0:
            in_stock.append(entry)
        else:
            out_of_stock.append(entry)

    # --- PDF ---
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2*cm, height-2*cm, "📊 Ripoti ya Mauzo ya Siku")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(2*cm, height-3*cm, f"Tarehe: {today.strftime('%d/%m/%Y')}")

    y = height - 4*cm

    # Function to draw table
    def draw_table(items_dict, title, y_start):
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(colors.lightgrey)
        pdf.rect(1.5*cm, y_start-0.3*cm, width-3*cm, 0.8*cm, fill=1)
        pdf.setFillColor(colors.black)
        pdf.drawString(2*cm, y_start, title)
        pdf.drawString(7*cm, y_start, "Aina")
        pdf.drawString(10*cm, y_start, "Idadi")
        pdf.drawString(13*cm, y_start, "Bei/Unit")
        pdf.drawString(16*cm, y_start, "Jumla")
        y_curr = y_start - 1*cm
        pdf.setFont("Helvetica", 11)
        total = 0
        for name, data in items_dict.items():
            if y_curr < 3*cm:
                pdf.showPage()
                y_curr = height - 2*cm
            pdf.drawString(2*cm, y_curr, name)
            pdf.drawString(7*cm, y_curr, data["product_type"])
            pdf.drawString(10*cm, y_curr, str(data["quantity"]))
            pdf.drawString(13*cm, y_curr, f"{data['unit_price']:.2f}")
            pdf.drawString(16*cm, y_curr, f"{data['subtotal']:.2f}")
            total += data["subtotal"]
            y_curr -= 0.8*cm
        # Total
        y_curr -= 0.5*cm
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(12*cm, y_curr, "Jumla Kuu:")
        pdf.drawString(16*cm, y_curr, f"{total:.2f}")
        return y_curr - 1*cm

    # Draw Workshop Purchases
    y = draw_table(workshop_items, "🛠 Bidhaa Zilizopatikana Workshop", y)

    # Draw Godown Purchases
    y = draw_table(godown_items_purchased, "🏭 Bidhaa Zilizopatikana Godown", y)

    # Stock
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2*cm, y, "📦 Bidhaa Zilizopo Stoo")
    y -= 0.8*cm
    pdf.setFont("Helvetica", 11)
    for item in in_stock:
        if y < 3*cm:
            pdf.showPage()
            y = height - 2*cm
        pdf.drawString(2*cm, y, f"{item['product_name']} ({item['product_type']}) - {item['quantity']} pcs")
        y -= 0.6*cm

    y -= 0.5*cm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2*cm, y, "❌ Bidhaa Zilizomalizika")
    y -= 0.8*cm
    pdf.setFont("Helvetica", 11)
    for item in out_of_stock:
        if y < 3*cm:
            pdf.showPage()
            y = height - 2*cm
        pdf.drawString(2*cm, y, f"{item['product_name']} ({item['product_type']}) - Imeisha")
        y -= 0.6*cm

    # Signatures and Stamp
    y -= 2*cm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2*cm, y, "Saini Msimamizi: ____________________")
    y -= 1.5*cm
    pdf.setFillColor(colors.lightgrey)
    pdf.rect(2*cm, y, 4*cm, 2*cm, fill=1)
    pdf.setFillColor(colors.black)
    pdf.drawString(2.2*cm, y+1*cm, "Muhuri wa Ofisi")

    pdf.save()
    buffer.seek(0)
    filename = f"daily_report_{today.isoformat()}.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)

# Kutuma ujumbe


@app.route("/api/contact", methods=["POST"])
def contact():

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    subject = data.get("subject")
    message = data.get("message")

    if not all([name, email, subject, message]):
        return jsonify({"error": "Taarifa zote zinahitajika"}), 400

    new_msg = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        content=message,
        date_sent=datetime.utcnow(),
    )

    db.session.add(new_msg)
    db.session.commit()

    return jsonify({"message": "Ujumbe umetumwa kwa mafanikio"}), 200


# kupokea ujumbe kwa admin
@app.route("/api/messages", methods=["GET"])
def get_messages():
    messages = ContactMessage.query.order_by(ContactMessage.date_sent.desc()).all()
    return jsonify(
        [
            {
                "id": m.id,
                "name": m.name,
                "email": m.email,
                "subject": m.subject,
                "content": m.content,
                "date_sent": m.date_sent.isoformat(),
            }
            for m in messages
        ]
    )


@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Barua pepe inahitajika"}), 400

    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        return jsonify({"message": "Umeshajiunga tayari"}), 200

    new_sub = Subscriber(email=email, subscribed_on=datetime.utcnow())
    db.session.add(new_sub)
    db.session.commit()

    return jsonify({"message": "Umejiunga kwa mafanikio!"}), 200


# Admin: Pata subscribers wote


@app.route("/api/subscribers", methods=["GET"])
def get_subscribers():
    all_subs = Subscriber.query.order_by(Subscriber.subscribed_on.desc()).all()
    result = [
        {
            "id": sub.id,
            "email": sub.email,
            "subscribed_on": sub.subscribed_on.isoformat(),
        }
        for sub in all_subs
    ]
    return jsonify(result)


# Sajili Mfanyakazi


@app.route("/api/employees", methods=["POST"])
def add_employee():
    data = request.get_json()
    name = data.get("name")
    gender = data.get("gender")
    phone = data.get("phone")
    position = data.get("position")
    salary = data.get("salary")

    if not all([name, gender, phone, position, salary]):
        return jsonify({"error": "Taarifa zote zinahitajika"}), 400

    new_emp = Employee(
        name=name, gender=gender, phone=phone, position=position, salary=salary
    )
    db.session.add(new_emp)
    db.session.commit()
    return jsonify({"message": "Mfanyakazi amesajiliwa"}), 201


# List ya Wafanyakazi


@app.route("/api/employees", methods=["GET"])
def get_employees():
    employees = Employee.query.order_by(Employee.date_added.desc()).all()
    return jsonify(
        [
            {
                "id": emp.id,
                "name": emp.name,
                "gender": emp.gender,
                "phone": emp.phone,
                "position": emp.position,
                "salary": emp.salary,
                "is_paid": emp.is_paid,
                "month_paid": emp.month_paid,
                "date_added": emp.date_added.isoformat(),
            }
            for emp in employees
        ]
    )

# Confirm payment


@app.route("/api/employees/<int:emp_id>/pay", methods=["PATCH"])
def mark_as_paid(emp_id):
    emp = db.session.get(Employee, emp_id)
    if not emp:
        return jsonify({"error": "Mfanyakazi hayupo"}), 404

    emp.is_paid = True
    emp.month_paid = datetime.utcnow().strftime("%B %Y")
    db.session.commit()
    return jsonify({"message": "Malipo yamethibitishwa"})




@app.route("/api/godown/posted", methods=["GET"])
def get_posted_godown_items():
    items = GodownItem.query.filter_by(is_posted=True).all()
    results = []
    for item in items:
        data = item.to_dict()
        data["image"] = f"/uploads/{item.image_filename}" if item.image_filename else None
        results.append(data)
    return jsonify(results)






# POST Manual Order
# --------------------------
@app.route("/api/manual-order", methods=["POST"])
def create_manual_order():
    try:
        data = request.get_json()
        print("Data received:", data)

        # Sanitize fields if needed
        customer_name = data.get("customer_name", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip()
        location = data.get("location", "").strip()
        items = data.get("items", [])
        payment_method = data.get("payment_method", "cash").strip()
        total_price = data.get("total_price", 0.0)
        notes = data.get("notes", "").strip()
        delivery_option = data.get("delivery_option", "").strip()
        delivery_location = data.get("delivery_location", "").strip()

        # Convert items to JSON string for storage
        items_json = json.dumps(items, ensure_ascii=False)

        new_order = ManualOrder(
            customer_name=customer_name,
            phone=phone,
            email=email,
            location=location,
            items=items_json,
            payment_method=payment_method,
            total_price=total_price,
            notes=notes,
            status="pending",
            delivery_option=delivery_option,
            delivery_location=delivery_location
        )

        db.session.add(new_order)
        db.session.commit()

        return jsonify({
            "message": "Manual order created successfully.",
            "order_id": new_order.id
        }), 201

    except Exception:
        # Print full traceback to console
        traceback.print_exc()
        return jsonify({"error": "Failed to create manual order"}), 500


# --------------------------
# GET Manual Orders
# --------------------------
@app.route("/api/manual-orders", methods=["GET"])
def get_manual_orders():
    orders = ManualOrder.query.order_by(ManualOrder.created_at.desc()).all()
    order_list = []

    for order in orders:
        try:
            items = json.loads(order.items)
        except:
            items = []

        order_list.append({
            "id": order.id,
            "customer_name": order.customer_name,
            "phone": order.phone,
            "email": order.email,
            "location": order.location,
            "delivery_option": order.delivery_option,
            "delivery_location": order.delivery_location,
            "items": items,
            "payment_method": order.payment_method,
            "total_price": order.total_price,
            "notes": order.notes,
            "status": order.status,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(order_list), 200




# Route ya kuthibitisha malipo
@app.route("/api/manual-orders/<int:order_id>/confirm-payment", methods=["POST"])
def confirm_payment(order_id):
    try:
        order = ManualOrder.query.get(order_id)
        if not order:
            return jsonify({"error": "Order haipo"}), 404

        if order.status == "paid":
            return jsonify({"status": "paid"}), 200

        order.status = "paid"

        # Punguza stock kwa kila bidhaa
        try:
            items = json.loads(order.items)
        except:
            items = []

        for item in items:
            product_id = item.get("product_id")  # lazima iwe na product_id
            quantity = item.get("quantity", 0)
            source = item.get("source", "").lower()  # "godown" au "workshop"

            if source == "godown":
                stock = GodownItem.query.get(product_id)
                if stock:
                    stock.quantity = max(stock.quantity - quantity, 0)
            elif source == "workshop":
                stock = WorkshopItem.query.get(product_id)
                if stock:
                    stock.quantity = max(stock.quantity - quantity, 0)

        db.session.commit()
        return jsonify({"status": "paid"}), 200

    except Exception as e:
        print(f"Error confirming payment: {e}")
        db.session.rollback()
        return jsonify({"error": "Imeshindikana kuthibitisha malipo"}), 500
    

@app.route("/api/manual-orders/<int:order_id>/update-delivery", methods=["POST"])
def update_manual_order_delivery(order_id):
    data = request.json
    fee = data.get("delivery_fee", 0)
    order = ManualOrder.query.get_or_404(order_id)
    order.delivery_fee = fee
    db.session.commit()
    return jsonify({"message": "Delivery fee updated", "delivery_fee": fee})
   




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
