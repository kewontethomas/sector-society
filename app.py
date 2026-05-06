from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models.user import db, User
from models.inventory import Inventory
import random
from datetime import datetime, timedelta
from models.marketplace import MarketplaceListing
from models.world_event import WorldEvent

app = Flask(__name__)

app.config["SECRET_KEY"] = "change-this-later"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def add_resource(user_id, resource_name, amount):
    inventory_item = Inventory.query.filter_by(
        user_id=user_id,
        resource_name=resource_name
    ).first()

    if inventory_item:
        inventory_item.quantity += amount
    else:
        inventory_item = Inventory(
            user_id=user_id,
            resource_name=resource_name,
            quantity=amount
        )

        db.session.add(inventory_item)

    db.session.commit()


def create_world_event(message):

    event = WorldEvent(
        message=message
    )

    db.session.add(event)
    db.session.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))
        
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("That username is already taken.")
            return redirect(url_for("register"))
        
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("dashboard"))
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.")
            return redirect(url_for("login"))
        
        login_user(user)

        return redirect(url_for("dashboard"))
    
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    events = WorldEvent.query.order_by(
        WorldEvent.created_at.desc()
    ).limit(8).all()

    return render_template(
        "dashboard.html",
        user=current_user,
        events=events
    )


RARE_DISCOVERIES = [
    "Ancient Blueprint Fragment",
    "Corrupted Data Chip",
    "Hollow Core Fragment",
    "Encrypted Transit Key",
    "Founder Relic",
    "Unknown Signal Device"
]


@app.route("/gather/<resource>")
@login_required
def gather(resource):
    allowed_resources = ["wood", "stone", "metal"]

    if resource not in allowed_resources:
        flash("Invalid resource.")
        return redirect(url_for("dashboard"))

    now = datetime.utcnow()

    if current_user.last_gather_time:
        cooldown = now - current_user.last_gather_time

        if cooldown < timedelta(seconds=30):
            remaining = 30 - int(cooldown.total_seconds())
            flash(f"You are tired. Wait {remaining} seconds.")
            return redirect(url_for("dashboard"))

    amount = random.randint(1, 5)

    add_resource(current_user.id, resource, amount)

    rare_roll = random.randint(1, 100)

    if rare_roll <= 5:

        rare_item = random.choice(RARE_DISCOVERIES)

        add_resource(
            current_user.id,
            rare_item,
            1
        )

        flash(f"⚡ Rare Discovery: {rare_item}")

        create_world_event(
            f"⚡ {current_user.username} discovered {rare_item}."
        )

    current_user.last_gather_time = now
    current_user.xp += amount * 2

    if current_user.xp >= current_user.level * 50:
        current_user.level += 1
        flash("⚡ Level Up!")

    db.session.commit()

    flash(f"You gathered {amount} {resource}.")

    create_world_event(
        f"{current_user.username} gathered {amount} {resource}."
    )
    return redirect(url_for("dashboard"))


@app.route("/inventory")
@login_required
def inventory():
    items = Inventory.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "inventory.html",
        items=items
    )


@app.route("/player/<username>")
@login_required
def player_profile(username):
    player = User.query.filter_by(username=username).first_or_404()

    inventory_items = Inventory.query.filter_by(
        user_id=player.id
    ).all()

    active_listings = MarketplaceListing.query.filter_by(
        seller_id=player.id,
        status="active"
    ).all()

    return render_template(
        "player_profile.html",
        player=player,
        inventory_items=inventory_items,
        active_listings=active_listings
    )


@app.route("/market")
@login_required
def market():
    listings = MarketplaceListing.query.filter_by(
        status="active"
    ).all()

    sellers = {}

    for listing in listings:
        sellers[listing.seller_id] = User.query.get(listing.seller_id)

    return render_template(
        "market.html",
        listings=listings,
        sellers=sellers
    )


@app.route("/sell/<resource>", methods=["GET", "POST"])
@login_required
def sell(resource):

    inventory_item = Inventory.query.filter_by(
        user_id=current_user.id,
        resource_name=resource
    ).first()

    if not inventory_item or inventory_item.quantity <= 0:
        flash("You do not have enough resources.")
        return redirect(url_for("inventory"))

    if request.method == "POST":

        quantity = int(request.form.get("quantity"))
        price = int(request.form.get("price"))

        if quantity <= 0 or price <= 0:
            flash("Values must be greater than zero.")
            return redirect(url_for("sell", resource=resource))

        if quantity > inventory_item.quantity:
            flash("Not enough resources.")
            return redirect(url_for("sell", resource=resource))

        inventory_item.quantity -= quantity

        listing = MarketplaceListing(
            seller_id=current_user.id,
            resource_name=resource,
            quantity=quantity,
            price=price
        )

        db.session.add(listing)
        db.session.commit()

        flash("Listing created.")

        create_world_event(
            f"🏗️ {current_user.username} listed {quantity} {resource} for {price} coins."
        )

        return redirect(url_for("market"))

    return render_template(
        "sell.html",
        resource=resource
    )


@app.route("/buy/<int:listing_id>")
@login_required
def buy(listing_id):

    listing = MarketplaceListing.query.get_or_404(listing_id)

    if listing.seller_id == current_user.id:
        flash("You cannot buy your own listing.")
        return redirect(url_for("market"))

    if listing.status != "active":
        flash("Listing unavailable.")
        return redirect(url_for("market"))

    if current_user.coins < listing.price:
        flash("Not enough coins.")
        return redirect(url_for("market"))

    seller = User.query.get(listing.seller_id)

    current_user.coins -= listing.price
    seller.coins += listing.price

    add_resource(
        current_user.id,
        listing.resource_name,
        listing.quantity
    )

    listing.status = "sold"

    db.session.commit()

    flash("Purchase successful.")

    create_world_event(
        f"💰 {current_user.username} bought {listing.quantity} {listing.resource_name}."
    )

    return redirect(url_for("market"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)