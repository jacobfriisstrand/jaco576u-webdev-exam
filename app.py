from flask import Flask, session, render_template, redirect, url_for, request, make_response
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import x
import json
import uuid 
import time
import os
import json
import random
import constants
from faker import Faker
from werkzeug.utils import secure_filename
from functools import wraps

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user"):
                return redirect(url_for("view_login"))
                
            if session["user"].get("role") != required_role:
                return redirect(url_for("view_index"))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

fake = Faker()


from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  #
Session(app)


app.secret_key = 'your-secret-key-here'  # Add this near your app initialization

##############################
##############################
##############################

def _________GET_________(): pass

##############################
##############################


##############################
@app.get("/")
@x.no_cache
def view_index():
    try:
        # Redirect restaurant/partner users
        if session.get("user"):
            role = session["user"].get("role")
            if role == "restaurant":
                return redirect(url_for("view_restaurant_dashboard"))
            elif role == "partner":
                return redirect(url_for("view_profile"))
        
        db, cursor = x.db()
        
        # Get restaurants with pagination
        restaurants_per_page = 8
        cursor.execute("""
            SELECT * FROM restaurants 
            WHERE restaurant_deleted_at = 0 
            ORDER BY restaurant_name
            LIMIT %s
        """, (restaurants_per_page,))
        restaurants = cursor.fetchall()
        
        # Get featured items with their restaurant info
        cursor.execute("""
            SELECT i.*, r.restaurant_name 
            FROM items i
            JOIN restaurants r ON i.item_restaurant_fk = r.restaurant_pk
            WHERE i.item_deleted_at = 0 
            AND r.restaurant_deleted_at = 0
            ORDER BY RAND()  -- Random selection for featured items
            LIMIT 12
        """)
        items = cursor.fetchall()

        # Fetch images for each item
        for item in items:
            cursor.execute("""
                SELECT * FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item['item_pk'],))
            item['images'] = cursor.fetchall()
        
        # Check if there are more restaurants
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM restaurants 
            WHERE restaurant_deleted_at = 0
        """)
        total_restaurants = cursor.fetchone()['total']
        has_more = total_restaurants > restaurants_per_page
        
        return render_template(
            "view_index.html",
            title="Home",
            x=x,
            restaurants=restaurants,
            items=items,
            has_more=has_more,
            next_page=2
        )
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return render_template(
            "view_index.html",
            title="Home",
            x=x,
            restaurants=[],
            items=[],
            error="Unable to load content"
        )
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/page/<page_number>")
def get_restaurant_pagination(page_number):
    try:
        # Validate page_number
        page_number = int(page_number)
        if page_number < 1:
            raise x.CustomException("Invalid page number", 400)

        db, cursor = x.db()
        restaurants_per_page = 8
        total_restaurants_with_hanging = restaurants_per_page + 1
        offset = (page_number - 1) * restaurants_per_page

        # Updated query to include restaurant owner information
        cursor.execute("""
            SELECT r.*, u.user_name as owner_name 
            FROM restaurants r
            JOIN users u ON r.restaurant_owner_fk = u.user_pk
            WHERE r.restaurant_deleted_at = 0 
            ORDER BY r.restaurant_name
            LIMIT %s OFFSET %s
        """, (total_restaurants_with_hanging, offset))
        
        restaurants = cursor.fetchall()

        if not restaurants:
            return """
                <template mix-target="#btn_next_page" mix-replace>
                    <sl-button variant='secondary' disabled>No more items</sl-button>
                </template>
            """

        html = "" # Server side rendering
        for restaurant in restaurants[:restaurants_per_page]:
            html_item = render_template("__restaurant.html", restaurant=restaurant)
            html = html + html_item

        # Determine if there are more restaurants
        has_more = len(restaurants) > restaurants_per_page
        
        # Prepare next page button
        next_page = page_number + 1
        button_html = render_template(
            "___btn_get_more_restaurants.html", 
            next_page=next_page
        ) if has_more else "<sl-button variant='secondary' disabled>No more items</sl-button>"

        return f"""
            <template mix-target="#restaurants" mix-bottom>
                {html}
            </template>
            <template mix-target="#btn_next_page" mix-replace>
                {button_html}
            </template>
        """

    except Exception as ex:
        ic("Error in get_restaurant_pagination:", ex)
        if "db" in locals(): 
            db.rollback()
        
        if isinstance(ex, x.CustomException):
            return {"error": ex.message}, ex.code
            
        return {"error": "System under maintenance. Please try again"}, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/items/<page_number>")
def get_item_pagination(page_number):
    try:
        # TODO: Validate page_number
        page_number = int(page_number)
        db, cursor = x.db()
        items_per_page = 6  # Match the initial load in view_dishes
        total_items_with_hanging = items_per_page + 1
        offset = (page_number - 1) * items_per_page
        
        # Update query to include restaurant name
        cursor.execute("""
            SELECT items.*, restaurants.restaurant_name 
            FROM items 
            JOIN restaurants ON items.item_restaurant_fk = restaurants.restaurant_pk 
            WHERE items.item_deleted_at = 0 OR items.item_blocked_at = 0
            AND restaurants.restaurant_deleted_at = 0 
            ORDER BY item_title ASC
            LIMIT %s OFFSET %s
        """, (total_items_with_hanging, offset))
        
        items = cursor.fetchall()

        # Add this section to fetch images for each item
        for item in items:
            cursor.execute("""
                SELECT * FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item['item_pk'],))
            item['images'] = cursor.fetchall()
        
        html = "" # Server side rendering
        
        # Render only up to items_per_page
        for item in items[:items_per_page]:
            html_item = render_template("__item.html", item=item)
            html = html + html_item
        
        db.commit()
        next_page = int(page_number) + 1
        
        # Determine if there are more items
        new_button = render_template("___btn_get_more_items.html", next_page=next_page)
        if len(items) <= items_per_page:
            new_button = "<sl-button variant='secondary' disabled>No more items</sl-button>"
 
        return f"""
            <template mix-target="#items" mix-bottom>
                {html}
            </template>
            <template mix-target="#btn_next_page_item" mix-replace>
                {new_button}
            </template>
        """

    except Exception as ex:
        print("#"*1000)
        print(ex)
        try:
            if "db" in locals():db.rollback()
            if len(ex.args) >= 2: # own created exception
                return {"error":ex.args[0]}, ex.args[1]  # Return response and status code
            else: # python exception, not under our control
                error = "System under maintenance. Please try again"
                return {"error":f"{error}"}, 500  # Return response and status code
        except Exception as e:
            print("#"*50)
            print(e)
            toast = render_template("__toast", message="System crashed")
            return f"<template mix-target='#toast' mix-bottom>{toast}</template>", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/get-restaurant-locations")
def get_restaurant_locations():
    try:
        db, cursor = x.db()
        cursor.execute("SELECT restaurant_pk, restaurant_name, restaurant_lat, restaurant_long, restaurant_image FROM restaurants")
        restaurants = cursor.fetchall()

        restaurant_locations = [
            {
                'restaurant_pk': str(restaurant['restaurant_pk']),
                'restaurant_name': str(restaurant['restaurant_name']),
                'latitude': float(restaurant['restaurant_lat']),
                'longitude': float(restaurant['restaurant_long']),
                'restaurant_image': str(restaurant['restaurant_image']),
            } for restaurant in restaurants
        ]
        
        response = make_response(json.dumps(restaurant_locations))
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as ex:
        if "db" in locals():db.rollback()
        if len(ex.args) >= 2: # own created exception
            return {"error":ex.args[0]}, ex.args[1]  # Return response and status code
        else: # python exception, not under our control
            error = "System under maintenance. Please try again"
            return {"error":f"{error}"}, 500  # Return response and status code
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/restaurant/<restaurant_pk>")
def view_restaurant(restaurant_pk):
    try:
        db, cursor = x.db()
        
        # Fetch restaurant details
        cursor.execute("""
            SELECT * FROM restaurants 
            WHERE restaurant_pk = %s 
            AND restaurant_deleted_at = 0
        """, (restaurant_pk,))
        restaurant = cursor.fetchone()
        
        # Fetch items for this restaurant with a new cursor
        items_cursor = db.cursor(dictionary=True)
        items_cursor.execute("""
            SELECT items.*, restaurants.restaurant_name 
            FROM items 
            JOIN restaurants ON items.item_restaurant_fk = restaurants.restaurant_pk 
            WHERE items.item_restaurant_fk = %s
            AND items.item_deleted_at = 0 
            AND items.item_blocked_at = 0  -- Ensure only non-blocked items are fetched
        """, (restaurant_pk,))
        items = items_cursor.fetchall()

        # Fetch images for each item with a new cursor
        for item in items:
            images_cursor = db.cursor(dictionary=True)
            images_cursor.execute("""
                SELECT * FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item['item_pk'],))
            item['images'] = images_cursor.fetchall()
            images_cursor.close()
        
        items_cursor.close()
        
        return render_template("view_restaurant.html", title="Restaurant Details", restaurant=restaurant, items=items)
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # My own exception
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast" mix-bottom>{ex.message}</template>""", ex.code
        
        # Database exception
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            if "restaurants.restaurant_pk" in str(ex):
                return """<template mix-target="#toast" mix-bottom>page not available</template>""", 400
            return "<template>System upgrading</template>", 500  
    
        # Any other exception
        return """<template mix-target="#toast" mix-bottom>System under maintenance</template>""", 500  
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/dishes")
def view_dishes():
    try:
        # Redirect restaurant/partner users
        if session.get("user"):
            role = session["user"].get("role")
            if role in ["restaurant", "partner"]:
                return redirect(url_for("view_index"))

        db, cursor = x.db()
        cursor.execute("""
        SELECT items.*, restaurants.restaurant_name 
        FROM items  
        JOIN restaurants ON items.item_restaurant_fk = restaurants.restaurant_pk 
        WHERE items.item_deleted_at = 0 OR items.item_blocked_at = 0
        AND restaurants.restaurant_deleted_at = 0 
        ORDER BY item_title ASC
        LIMIT 0,12
        """)
        items = cursor.fetchall()
        
        # Fetch images for each item
        for item in items:
            cursor.execute("""
                SELECT * FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item['item_pk'],))
            item['images'] = cursor.fetchall()
        
        return render_template("view_dishes.html", title="Dishes", items=items, next_page=2)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/restaurants")
def view_restaurants():
    try:
        # Redirect restaurant/partner users
        if session.get("user"):
            role = session["user"].get("role")
            if role in ["restaurant", "partner"]:
                return redirect(url_for("view_index"))

        db, cursor = x.db()
        cursor.execute("SELECT * FROM restaurants LIMIT 0,8")
        restaurants = cursor.fetchall()
        return render_template("view_restaurants.html", title="Restaurants", restaurants=restaurants, next_page=2)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/restaurant-dashboard") 
@x.no_cache
def view_restaurant_dashboard():
    try:
        if not session.get("user"):
            return redirect(url_for("view_login"))
            
        if session["user"].get("role") != "restaurant":
            return redirect(url_for("view_index"))
            
        db, cursor = x.db()
        
        # Get restaurant data
        cursor.execute("""
            SELECT * FROM restaurants 
            WHERE restaurant_owner_fk = %s 
            AND restaurant_deleted_at = 0
        """, (session["user"]["user_pk"],))
        
        restaurant = cursor.fetchone()
        
        if not restaurant:
            return render_template(
                "view_restaurant_dashboard.html",
                title="Restaurant Dashboard",
                x=x,
                restaurant={"restaurant_image": "default_restaurant.jpg"},
                items=[],
                error="No restaurant found"
            )
            
        # Get items and their images in one query
        cursor.execute("""
            SELECT i.*, GROUP_CONCAT(im.image_filename ORDER BY im.image_order) as item_images
            FROM items i
            LEFT JOIN item_images im ON i.item_pk = im.image_item_fk
            WHERE i.item_restaurant_fk = %s 
            AND i.item_deleted_at = 0
            GROUP BY i.item_pk
            ORDER BY i.item_title
        """, (restaurant["restaurant_pk"],))
        
        items = cursor.fetchall()

        # Process items to ensure proper image handling
        processed_items = []
        for item in items:
            processed_item = dict(item)
            if item['item_images']:
                processed_item['images'] = [{'image_filename': img} for img in item['item_images'].split(',')]
            else:
                processed_item['images'] = [{'image_filename': 'default_dish.jpg'}]
            del processed_item['item_images']
            processed_items.append(processed_item)

        return render_template(
            "view_restaurant_dashboard.html",
            title="Restaurant Dashboard",
            x=x,
            restaurant=restaurant,
            items=processed_items
        )
        
    except Exception as ex:
        ic(ex)
        return render_template(
            "view_restaurant_dashboard.html",
            title="Restaurant Dashboard",
            x=x,
            restaurant={"restaurant_image": "default_restaurant.jpg"},
            items=[],
            error="Error loading data"
        )
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

    

##############################
@app.get("/signup")
@x.no_cache
def view_signup():
    try:
        # role = request.args.get("role", "").lower()

        # if role not in ["partner", "customer", "restaurant"]:
        #     # Handle invalid or missing role
        #     return redirect(url_for("view_choose_role"))

        # Render the appropriate signup form based on the role
        return render_template("view_signup.html", title="Sign Up", x=x)

    except Exception as ex:
        ic(ex)
        # Return a generic error page for unexpected issues
        return "System under maintenance", 500

##############################
@app.get("/login")
@x.no_cache
def view_login():
    # # If user is already logged in, redirect to appropriate page
    # if session.get("user"):
    #     if session["user"].get("active_role") == "restaurant":
    #         return redirect(url_for("view_restaurant_dashboard"))
    #     elif session["user"].get("active_role") == "partner":
    #         return redirect(url_for("view_partner_dashboard"))
    #     else:
    #         return redirect(url_for("view_index"))
            
    return render_template(
        "view_login.html",
        title="Login",
        x=x,
        message=request.args.get("message", "")
    )

##############################
@app.get("/search")
def view_search():
    try:
        # Check if user is restaurant or partner
        if session.get("user"):
            role = session["user"].get("role")
            if role in ["restaurant", "partner"]:
                return redirect(url_for("view_index"))

        search_query = request.args.get('q', '').strip()
        if not search_query:
            return render_template("view_search.html", title="Search", items=[], restaurants=[], x=x)

        db, cursor = x.db()
        
        # Search in items
        cursor.execute("""
            SELECT items.*, restaurants.restaurant_name 
            FROM items 
            JOIN restaurants ON items.item_restaurant_fk = restaurants.restaurant_pk 
            WHERE (items.item_deleted_at = 0 OR items.item_blocked_at = 0)
            AND (restaurants.restaurant_deleted_at = 0 OR restaurants.restaurant_blocked_at = 0)
            AND (LOWER(item_title) LIKE LOWER(%s)
            OR LOWER(item_desc) LIKE LOWER(%s))
            LIMIT 12
        """, (f"%{search_query}%", f"%{search_query}%"))
        items = cursor.fetchall()

        # Fetch images for each item
        for item in items:
            cursor.execute("""
                SELECT * FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item['item_pk'],))
            item['images'] = cursor.fetchall()

        # Search in restaurants
        cursor.execute("""
            SELECT * FROM restaurants 
            WHERE LOWER(restaurant_name) LIKE LOWER(%s)
            OR LOWER(restaurant_description) LIKE LOWER(%s)
            OR LOWER(restaurant_cuisine_types) LIKE LOWER(%s)
            LIMIT 8
        """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
        restaurants = cursor.fetchall()

        return render_template("view_search.html", 
                             title="Search Results", 
                             items=items, 
                             restaurants=restaurants,
                             search_query=search_query, 
                             x=x)

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return render_template("view_search.html", 
                             title="Search Error", 
                             error="An error occurred while searching")
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.get("/admin-dashboard")
@x.no_cache
def view_admin():
    try:    
        if session["user"].get("role") != "admin":
            return redirect(url_for("view_login"))
        
        user = session.get("user")
        db, cursor = x.db()
        
        # Get users
        cursor.execute("""
            SELECT u.*, r.role_name
            FROM users u
            JOIN users_roles ur ON u.user_pk = ur.user_role_user_fk
            JOIN roles r ON ur.user_role_role_fk = r.role_pk
            WHERE r.role_name != 'admin' 
            AND u.user_deleted_at = 0
        """)
        users = cursor.fetchall()

        # Get items
        cursor.execute("""
            SELECT i.*, r.restaurant_name 
            FROM items i
            JOIN restaurants r ON i.item_restaurant_fk = r.restaurant_pk
            WHERE i.item_deleted_at = 0 
            AND r.restaurant_deleted_at = 0
        """)
        items = cursor.fetchall()
        
        # Get restaurants
        cursor.execute("""
            SELECT r.*, u.user_name as owner_name 
            FROM restaurants r
            JOIN users u ON r.restaurant_owner_fk = u.user_pk
            WHERE r.restaurant_deleted_at = 0
        """)
        restaurants = cursor.fetchall()
        
        # Fetch images for each item
        for item in items:
            cursor.execute("""
                SELECT image_filename FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item['item_pk'],))
            item['images'] = cursor.fetchall()

        message = "No users found." if not users else ""
        return render_template("view_admin.html", 
                             title="Admin Dashboard",
                             users=users, 
                             user=user, 
                             items=items, 
                             restaurants=restaurants,
                             message=message)

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "<template>System upgrading</template>", 500
        return "<template>System under maintenance</template>", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


@app.get("/profile")
@x.no_cache
def view_profile():
    try:
        if not session.get("user"):
            return redirect(url_for("view_login"))
            
        db, cursor = x.db()
        
        # Get user data with role - simplified query
        cursor.execute("""
            SELECT u.*, r.role_name
            FROM users u
            JOIN users_roles ur ON u.user_pk = ur.user_role_user_fk
            JOIN roles r ON ur.user_role_role_fk = r.role_pk
            WHERE u.user_pk = %s 
            AND u.user_deleted_at = 0
        """, (session["user"]["user_pk"],))
        
        user = cursor.fetchone()
        
        if user:
            return render_template(
                "view_profile.html",
                title="Profile",
                x=x,
                user=user
            )
        else:
            return render_template(
                "view_profile.html",
                title="Profile",
                x=x,
                user=session.get("user", {})
            )
        
    except Exception as ex:
        ic(ex)
        return render_template(
            "view_profile.html",
            title="Profile",
            x=x,
            user=session.get("user", {})
        )
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/checkout")
def view_checkout():
    # Check if user is restaurant or partner
    if session.get("user"):
        user_roles = session.get("user").get("roles", [])
        if "restaurant" in user_roles or "partner" in user_roles:
            return redirect(url_for("view_index"))

    if not session.get("user", ""): 
        # Store the intended destination in the session
        session['intended_destination'] = '/checkout'
        return redirect(url_for("view_login", message="You need to be logged in to make a purchase"))
    
    user_email = session.get("user_email", "")
    user_name = session.get("user_name", "")
    cart_cookie = request.cookies.get("cart", "[]")
    cart = json.loads(cart_cookie) if cart_cookie else []
    cart_total = sum(float(item.get('item_price', 0)) for item in cart)
    
    return render_template("view_checkout.html", 
                           title="Checkout",
                           user_email=user_email, 
                           user_name=user_name,
                           cart=cart, 
                           cart_total=cart_total)


##############################
@app.get("/thank-you")
def view_thank_you():
    if not session.get("user", ""): 
        return redirect(url_for("view_login"))
    
    return render_template("view_thank_you.html", title="Thank You")



##############################
##############################
##############################

def _________POST_________(): pass

##############################
##############################
##############################

@app.post("/logout")
def logout():
    # ic("#"*30)
    # ic(session)
    session.pop("user", None)
    # session.clear()
    # session.modified = True
    # ic("*"*30)
    # ic(session)
    return redirect(url_for("view_login"))

##############################
@app.post("/forgot-password")
def forgot_password():
    try:
        email = x.validate_email()
        reset_key = str(uuid.uuid4())
        reset_expires_at = int(time.time()) + (60 * 30)  # 30 minutes from now
        
        db, cursor = x.db()
        
        # First check if the email exists in either table
        cursor.execute("""
            SELECT 'user' as type FROM users 
            WHERE user_email = %s AND user_deleted_at = 0
            UNION
            SELECT 'restaurant' as type FROM restaurants 
            WHERE restaurant_email = %s AND restaurant_deleted_at = 0
        """, (email, email))
        
        result = cursor.fetchone()
        
        if not result:
            toast = render_template("___toast.html", message="No account found with this email address")
            return f"""<template mix-target="#toast">{toast}</template>""", 400
            
        # Update the appropriate table
        if result['type'] == 'user':
            cursor.execute("""
                UPDATE users 
                SET user_password_reset_key = %s, 
                    user_password_reset_expires_at = %s 
                WHERE user_email = %s 
                AND user_deleted_at = 0
            """, (reset_key, reset_expires_at, email))
        else:
            cursor.execute("""
                UPDATE restaurants 
                SET restaurant_verification_key = %s,  # Using existing verification key field
                    restaurant_verified_at = %s 
                WHERE restaurant_email = %s 
                AND restaurant_deleted_at = 0
            """, (reset_key, reset_expires_at, email))
        
        # Send reset email
        x.send_reset_password_email(email=email, reset_key=reset_key)
        
        db.commit()
        return """<template mix-redirect="/login?message=Please+check+your+email+to+reset+your+password"></template>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        toast = render_template("___toast.html", message="Unable to process your request. Please try again later.")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/search/<search_query>")
def search():
    q = request.args.get('q', '')
    return render_template("view_search.html", title="Search", x=x, q=q)

##############################
@app.get("/forgot-password")
@x.no_cache
def view_forgot_password():
    return render_template("view_forgot_password.html", title="Reset Password", x=x)

##############################
@app.get("/reset-password/<reset_key>")
@x.no_cache
def view_reset_password(reset_key):
    try:
        db, cursor = x.db()
        current_time = int(time.time())
        
        # Check users table first
        q_user = """SELECT user_pk FROM users 
                    WHERE user_password_reset_key = %s 
                    AND user_password_reset_expires_at > %s"""
        cursor.execute(q_user, (reset_key, current_time))
        user = cursor.fetchone()
        
        # If not in users table, check restaurants
        if not user:
            q_restaurant = """SELECT restaurant_pk FROM restaurants 
                             WHERE restaurant_password_reset_key = %s 
                             AND restaurant_password_reset_expires_at > %s"""
            cursor.execute(q_restaurant, (reset_key, current_time))
            restaurant = cursor.fetchone()
            
            if not restaurant:
                return redirect(url_for("view_login", message="Invalid or expired reset link"))
        
        reset_key = x.validate_uuid4(reset_key)
        return render_template("view_reset_password.html", title="Set New Password", reset_key=reset_key, x=x)
        
    except Exception as ex:
        ic(ex)
        return redirect(url_for("view_login", message="Invalid reset link"))
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/reset-password/<reset_key>")
def reset_password(reset_key):
    try:
        reset_key = x.validate_uuid4(reset_key)
        password = x.validate_password()
        current_time = int(time.time())
        hashed_password = generate_password_hash(password)
        
        db, cursor = x.db()
        
        # Try users table first
        q_user = """UPDATE users 
                    SET user_password = %s,
                        user_password_reset_key = NULL,
                        user_password_reset_expires_at = NULL
                    WHERE user_password_reset_key = %s 
                    AND user_password_reset_expires_at > %s"""
        cursor.execute(q_user, (hashed_password, reset_key, current_time))
        
        # If no user found, try restaurants table
        if cursor.rowcount == 0:
            q_restaurant = """UPDATE restaurants 
                             SET restaurant_password = %s,
                                 restaurant_password_reset_key = NULL,
                                 restaurant_password_reset_expires_at = NULL
                             WHERE restaurant_password_reset_key = %s 
                             AND restaurant_password_reset_expires_at > %s"""
            cursor.execute(q_restaurant, (hashed_password, reset_key, current_time))
            
            if cursor.rowcount == 0:
                raise x.CustomException("Invalid or expired reset link", 400)
        
        db.commit()
        return """<template mix-redirect="/login?message=Password+successfully+reset"></template>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/signup")
@x.no_cache
def signup():
    try:
        # Validate role first
        role = x.validate_role()
        
        # Common user validations
        email = x.validate_email()
        password = x.validate_password()
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        
        # Additional restaurant validations if needed
        if role == "restaurant":
            restaurant_name = x.validate_restaurant_name()
            restaurant_address = x.validate_address()
            x.validate_cuisine_types()
        
        db, cursor = x.db()
        
        # Create user
        user_pk = str(uuid.uuid4())
        verification_key = str(uuid.uuid4())
        hashed_password = generate_password_hash(password)
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (
                user_pk, user_name, user_last_name, user_email, 
                user_password, user_avatar, user_created_at, 
                user_deleted_at, user_blocked_at, user_updated_at, 
                user_verified_at, user_verification_key
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_pk, user_name, user_last_name, email,
            hashed_password, f"image_{random.randint(1, 100)}.jpg",
            int(time.time()), 0, 0, 0, 0, verification_key
        ))

        # Assign single role
        role_pk = {
            "customer": x.CUSTOMER_ROLE_PK,
            "partner": x.PARTNER_ROLE_PK,
            "restaurant": x.RESTAURANT_ROLE_PK
        }[role]
        
        cursor.execute("""
            INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, role_pk))

        # Send verification email
        x.send_verify_email(
            email=email,
            user_verification_key=verification_key,
            role=role
        )

        # If restaurant role, create restaurant with additional data
        if role == "restaurant":
            restaurant_pk = str(uuid.uuid4())
            
            # Get user-provided restaurant data
            restaurant_name = x.validate_restaurant_name()
            restaurant_address = x.validate_address()
            # Replace underscores with spaces before applying title case
            cuisine_types = [cuisine.replace('_', ' ').title() for cuisine in request.form.getlist("restaurant_cuisine_types")]
            price_level = request.form.get("price_level", "$$")
            
            # Add default/random data for other fields
            restaurant = {
                "restaurant_pk": restaurant_pk,
                "restaurant_owner_fk": user_pk,
                "restaurant_name": restaurant_name,
                "restaurant_email": email,  # Use same email as user
                "restaurant_catchphrase": random.choice(constants.catchphrases),
                "restaurant_description": random.choice(constants.descriptions),
                "restaurant_rating": round(random.uniform(3.0, 5.0) * 2) / 2,
                "restaurant_total_ratings": 0,
                "restaurant_price_level": price_level,
                "restaurant_estimated_delivery_time": f"{random.randint(15, 60)} min",
                "restaurant_delivery_fee": random.randint(50, 70),
                "restaurant_minimum_order": random.randint(80, 100),
                "restaurant_address": restaurant_address,
                "restaurant_lat": 55.676098,  # Default Copenhagen coordinates
                "restaurant_long": 12.568337,
                "restaurant_image": f"restaurant_{random.randint(1, 50)}.jpg",
                "restaurant_cuisine_types": ", ".join(cuisine_types),  # Join the properly formatted cuisines
                "restaurant_features": ", ".join(random.sample(constants.features, k=random.randint(3, 8))),
                "restaurant_created_at": int(time.time()),
                "restaurant_deleted_at": 0,
                "restaurant_blocked_at": 0,
                "restaurant_updated_at": 0,
                "restaurant_verified_at": 0
            }

            # Insert restaurant
            cursor.execute("""
                INSERT INTO restaurants (
                    restaurant_pk, restaurant_owner_fk, restaurant_name, restaurant_email,
                    restaurant_catchphrase, restaurant_description, restaurant_rating,
                    restaurant_total_ratings, restaurant_price_level, restaurant_estimated_delivery_time,
                    restaurant_delivery_fee, restaurant_minimum_order, restaurant_address,
                    restaurant_lat, restaurant_long, restaurant_image, restaurant_cuisine_types,
                    restaurant_features, restaurant_created_at, restaurant_deleted_at,
                    restaurant_blocked_at, restaurant_updated_at, restaurant_verified_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, tuple(restaurant.values()))

            # Add some default menu items
            default_items = [
                {"title": "House Special", "price": 129.00},
                {"title": "Chef's Choice", "price": 149.00},
                {"title": "Daily Special", "price": 99.00}
            ]

            for item in default_items:
                # Create the item first
                item_pk = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO items (
                        item_pk, item_restaurant_fk, item_title, 
                        item_desc, item_price
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    item_pk,
                    restaurant_pk,
                    item["title"],
                    f"Our delicious {item['title'].lower()}",
                    item["price"]
                ))
                
                # Then add a default image for the item
                cursor.execute("""
                    INSERT INTO item_images (
                        image_pk, image_item_fk, image_filename, 
                        image_order, image_created_at
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    item_pk,
                    f"dish_{random.randint(1, 100)}.jpg",
                    0,  # First image
                    int(time.time())
                ))

        db.commit()
        return """<template mix-redirect="/login?message=Please+check+your+email+to+verify+your+account"></template>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            if "users.user_email" in str(ex):
                toast = render_template("___toast.html", message="Email not available")
                return f"""<template mix-target="#toast">{toast}</template>""", 400
            toast = render_template("___toast.html", message="System upgrading")
            return f"""<template mix-target="#toast">{toast}</template>""", 500
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.post("/login")
def login():
    try:
        user_email = x.validate_email()
        user_password = x.validate_password()

        db, cursor = x.db()
        # Get user with their single role
        cursor.execute("""
            SELECT u.*, r.role_name
            FROM users u
            JOIN users_roles ur ON u.user_pk = ur.user_role_user_fk
            JOIN roles r ON ur.user_role_role_fk = r.role_pk
            WHERE u.user_email = %s 
            AND u.user_deleted_at = 0
        """, (user_email,))
        
        user = cursor.fetchone()
        if not user:
            toast = render_template("___toast.html", message="User not registered")
            return f"""<template mix-target="#toast">{toast}</template>""", 400     
        
        if not check_password_hash(user["user_password"], user_password):
            toast = render_template("___toast.html", message="Invalid credentials")
            return f"""<template mix-target="#toast">{toast}</template>""", 401

        # Create simplified session data with single role
        session["user"] = {
            "user_pk": user["user_pk"],
            "user_name": user["user_name"],
            "user_last_name": user["user_last_name"],
            "user_email": user["user_email"],
            "user_avatar": user["user_avatar"],
            "role": user["role_name"]  # Single role
        }

        # Redirect based on role
        if user["role_name"] == "customer":
            return """<template mix-redirect="/"></template>"""
        elif user["role_name"] == "partner":
            return """<template mix-redirect="/profile"></template>"""
        elif user["role_name"] == "restaurant":
            return """<template mix-redirect="/restaurant-dashboard"></template>"""
        elif user["role_name"] == "admin":
            return """<template mix-redirect="/admin-dashboard"></template>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "<template>System upgrading</template>", 500        
        return "<template>System under maintenance</template>", 500  
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.post("/items")
def create_item():
    try:
        if not session.get("user") or session["user"].get("role") != "restaurant":
            raise x.CustomException("Unauthorized", 401)

        db, cursor = x.db()
        
        # Get restaurant info if not in session
        if "restaurant" not in session["user"]:
            cursor.execute("""
                SELECT restaurant_pk, restaurant_name 
                FROM restaurants 
                WHERE restaurant_owner_fk = %s 
                AND restaurant_deleted_at = 0
            """, (session["user"]["user_pk"],))
            
            restaurant = cursor.fetchone()
            if not restaurant:
                raise x.CustomException("No restaurant found", 404)
                
            session["user"]["restaurant"] = {
                "restaurant_pk": restaurant["restaurant_pk"],
                "restaurant_name": restaurant["restaurant_name"]
            }
            session.modified = True

        try:
            # Validate inputs - these will now raise CustomException if invalid
            item_title = x.validate_item_title()
            item_desc = x.validate_item_description()
            item_price = x.validate_item_price()
        except x.CustomException as validation_error:
            return f"""<template mix-target="#toast" mix-bottom>{validation_error.message}</template>""", validation_error.code
        
        # Ensure upload directory exists
        os.makedirs(x.UPLOAD_ITEM_FOLDER, exist_ok=True)
        
        # Validate files
        validated_files = {}
        for key in request.files:
            file = request.files[key]
            if file and file.filename:
                if not x.allowed_file(file.filename):
                    raise x.CustomException("Invalid file type", 400)
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                validated_files[key] = (file, filename)
        
        if not validated_files:
            raise x.CustomException("At least one image is required", 400)
            
        # Create item
        item_pk = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO items (
                item_pk, item_restaurant_fk, item_title, 
                item_desc, item_price, item_created_at, 
                item_deleted_at, item_updated_at, item_blocked_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            item_pk,
            session["user"]["restaurant"]["restaurant_pk"],
            item_title,
            item_desc,
            item_price,
            int(time.time()),
            0, 0, 0
        ))
        
        # Handle validated image uploads
        for file_key, (file, filename) in validated_files.items():
            # Save file to disk
            file.save(os.path.join(x.UPLOAD_ITEM_FOLDER, filename))
            
            # Get image order from the file key (item_image_1 -> 0, item_image_2 -> 1, etc.)
            image_order = int(file_key.split('_')[-1]) - 1
            
            cursor.execute("""
                INSERT INTO item_images (
                    image_pk, image_item_fk, image_filename, 
                    image_order, image_created_at
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()),
                item_pk,
                filename,
                image_order,
                int(time.time())
            ))
        
        db.commit()
        
        return f"""
            <template mix-target="#toast">Item created successfully</template>
            <template mix-redirect="/restaurant-dashboard"></template>
            
        """

    except Exception as ex:
        ic("Error in create_item:", ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        toast = render_template("___toast.html", message="System error")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/checkout/confirmed")
def process_checkout():
    try:
        # Ensure user is logged in
        if not session["user"].get("role") == "customer":
            return redirect(url_for("view_login"))
        
        # Get cart from cookies
        cart_cookie = request.cookies.get("cart", "[]")
        cart = json.loads(cart_cookie) if cart_cookie else []
        
        # Check if cart is empty
        if not cart:
            toast = render_template("___toast.html", message="Your cart is empty")
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
        
        # Get email and name directly from the session
        user_email = session["user"]["user_email"]
        user_name = session["user"]["user_name"]
        
        # Send checkout confirmation email
        x.send_checkout_email(user_email, user_name, cart)

        # Create response with redirect and clear cart cookie
        response_html = """
        <template mix-redirect="/thank-you"></template>
        """
        response = make_response(response_html)
        response.set_cookie('cart', '[]', max_age=0)  # Expire the cart cookie

        return response

    except Exception as ex:
        ic(ex)
        # Handle any errors
        toast = render_template("___toast.html", message="Error processing checkout")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500


##############################
##############################
##############################

def _________PUT_________(): pass

##############################
##############################
##############################

@app.put("/items/<item_pk>")
def update_item(item_pk):
    try:
        if not session.get("user") or session["user"].get("role") != "restaurant":
            raise x.CustomException("Unauthorized", 401)

        try:
            # Validate all inputs first
            item_title = x.validate_item_title()
            item_desc = x.validate_item_description()
            item_price = x.validate_item_price()
        except x.CustomException as validation_error:
            return f"""<template mix-target="#toast" mix-bottom>{validation_error.message}</template>""", validation_error.code

        db, cursor = x.db()
        
        # Get restaurant info for the logged-in user
        cursor.execute("""
            SELECT restaurant_pk 
            FROM restaurants 
            WHERE restaurant_owner_fk = %s 
            AND restaurant_deleted_at = 0
        """, (session["user"]["user_pk"],))
        
        restaurant = cursor.fetchone()
        if not restaurant:
            raise x.CustomException("Restaurant not found", 404)
        
        # Check for files with proper validation
        files = {}  # Changed to dict to track which position each file is for
        for key in request.files:
            file = request.files[key]
            ic(f"Processing file: {key}", file.filename if file else "No file")
            if file and file.filename:
                # Validate file type and size
                if not x.allowed_file(file.filename):
                    raise x.CustomException("Invalid file type", 400)
                # Extract position from key (item_image_1 -> 0, item_image_2 -> 1, etc.)
                position = int(key.split('_')[-1]) - 1
                files[position] = file
        
        # Verify item belongs to restaurant
        cursor.execute("""
            SELECT * FROM items 
            WHERE item_pk = %s AND item_restaurant_fk = %s
        """, (item_pk, restaurant["restaurant_pk"]))
        
        if not cursor.fetchone():
            raise x.CustomException("Item not found", 404)
        
        # Update item basic info
        cursor.execute("""
            UPDATE items 
            SET item_title = %s, 
                item_desc = %s, 
                item_price = %s,
                item_updated_at = %s
            WHERE item_pk = %s
        """, (
            item_title, 
            item_desc, 
            item_price,
            int(time.time()),
            item_pk
        ))
        
        # Handle image updates if any files were uploaded
        if files:
            ic(f"Processing {len(files)} files")
            
            # Get current images
            cursor.execute("""
                SELECT * FROM item_images 
                WHERE image_item_fk = %s 
                ORDER BY image_order
            """, (item_pk,))
            current_images = cursor.fetchall()
            
            # Update or insert images
            for position, file in files.items():
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                file_path = os.path.join(x.UPLOAD_ITEM_FOLDER, filename)
                ic(f"Saving file to: {file_path}")
                file.save(file_path)
                
                # Check if we're updating an existing image position
                existing_image = None
                for img in current_images:
                    if img['image_order'] == position:
                        existing_image = img
                        break
                
                if existing_image:
                    # Update existing image
                    ic(f"Updating image at position {position}")
                    # Delete old file
                    try:
                        old_file_path = os.path.join(x.UPLOAD_ITEM_FOLDER, existing_image['image_filename'])
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    except Exception as e:
                        ic("Error removing old file:", e)
                    
                    cursor.execute("""
                        UPDATE item_images 
                        SET image_filename = %s
                        WHERE image_pk = %s
                    """, (filename, existing_image['image_pk']))
                else:
                    # Insert new image
                    ic(f"Inserting new image at position {position}")
                    cursor.execute("""
                        INSERT INTO item_images (
                            image_pk, image_item_fk, image_filename, 
                            image_order, image_created_at
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        str(uuid.uuid4()),
                        item_pk,
                        filename,
                        position,
                        int(time.time())
                    ))
        
        db.commit()
        
        return f"""
            <template mix-target="#toast">Item updated successfully</template>
            <template mix-redirect="/restaurant-dashboard"></template>
        """

    except Exception as ex:
        ic("Error in update_item:", ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast">{ex.message}</template>""", ex.code
        toast = render_template("___toast.html", message="System error")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.put("/items/<item_pk>/delete")
def delete_item(item_pk):
    try:
        # Verify user is logged in and is a restaurant owner
        if not session.get("user") or session["user"].get("role") != "restaurant":
            raise x.CustomException("Unauthorized", 401)

        db, cursor = x.db()
        
        # Verify item belongs to this restaurant
        cursor.execute("""
            SELECT * FROM items 
            WHERE item_pk = %s 
            AND item_restaurant_fk = %s
            AND item_deleted_at = 0
        """, (item_pk, session["user"]["restaurant"]["restaurant_pk"]))
        
        item = cursor.fetchone()
        if not item:
            raise x.CustomException("Item not found", 404)
        
        # Get all image filenames before deleting
        cursor.execute("SELECT image_filename FROM item_images WHERE image_item_fk = %s", (item_pk,))
        images = cursor.fetchall()
        
        # Delete physical image files
        for image in images:
            try:
                file_path = os.path.join(x.UPLOAD_ITEM_FOLDER, image['image_filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                ic("Error removing image file:", e)
        
        # Delete image records
        cursor.execute("DELETE FROM item_images WHERE image_item_fk = %s", (item_pk,))
        
        # Soft delete the item by updating item_deleted_at
        cursor.execute("""
            UPDATE items 
            SET item_deleted_at = %s 
            WHERE item_pk = %s
        """, (int(time.time()), item_pk))
        
        db.commit()
        
        return f"""
            <template mix-target="#toast">Item deleted successfully</template>
            <template mix-redirect="/restaurant-dashboard"></template>
        """

    except Exception as ex:
        ic("Error in delete_item:", ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast">{ex.message}</template>""", ex.code
        return f"""<template mix-target="#toast">System error</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.put("/items/block/<item_pk>")
def item_block(item_pk):
    try:
        # Check if user is logged in and has admin role
        if not session.get("user") or session["user"].get("role") != "admin":
            raise x.CustomException("Unauthorized", 401)

        # Validate UUID and prepare item data
        item_pk = x.validate_uuid4(item_pk)
        current_time = int(time.time())
        item_data = {
            "item_pk": item_pk,
            "item_blocked_at": current_time
        }

        db, cursor = x.db()
        
        # First check if item exists and is not already blocked
        cursor.execute('SELECT item_blocked_at FROM items WHERE item_pk = %s', (item_pk,))
        existing_item = cursor.fetchone()
        
        if not existing_item:
            raise x.CustomException("Item not found", 404)
        
        # Update item block status
        cursor.execute("""
            UPDATE items 
            SET item_blocked_at = %s, 
                item_updated_at = %s 
            WHERE item_pk = %s
        """, (current_time, current_time, item_pk))
        
        if cursor.rowcount != 1:
            raise x.CustomException("Cannot block item", 400)

        # Get item and restaurant details for notification
        cursor.execute("""
            SELECT i.item_title, r.restaurant_email, r.restaurant_name,
                   u.user_name as restaurant_owner 
            FROM items i
            JOIN restaurants r ON i.item_restaurant_fk = r.restaurant_pk
            JOIN users u ON r.restaurant_owner_fk = u.user_pk
            WHERE i.item_pk = %s
        """, (item_pk,))
        item_info = cursor.fetchone()
        
        if item_info:
            # Send email notification to restaurant owner
            x.send_item_blocked_email(
                to_email=item_info['restaurant_email'], 
                item_title=item_info['item_title'],
                user_name=item_info['restaurant_owner']
            )
            
            # Return both the button update and email confirmation toast
            btn_unblock = render_template("___btn_unblock_item.html", item=item_data)
            toast = render_template("___toast.html", message=f"Notification email sent to {item_info['restaurant_owner']}")
            
            return f"""
                <template mix-target="#frm_item_block" mix-replace>{btn_unblock}</template>
                <template mix-target="#toast" mix-bottom>{toast}</template>
            """

        # If no item_info, just return the button update
        btn_unblock = render_template("___btn_unblock_item.html", item=item_data)
        return f"""<template mix-target="#frm_item_block" mix-replace>{btn_unblock}</template>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


@app.put("/items/unblock/<item_pk>")
def item_unblock(item_pk):
    try:
        if not session.get("user") or session["user"].get("role") != "admin":
            raise x.CustomException("Unauthorized", 401)

        item_pk = x.validate_uuid4(item_pk)
        item_blocked_at = 0
        item = {
            "item_pk": item_pk,
            "item_blocked_at": item_blocked_at
        }

        db, cursor = x.db()
        cursor.execute("""
            UPDATE items 
            SET item_blocked_at = %s,
                item_updated_at = %s
            WHERE item_pk = %s
        """, (item_blocked_at, int(time.time()), item_pk))

        if cursor.rowcount != 1:
            raise x.CustomException("Cannot unblock item", 400)
 
        btn_block = render_template("___btn_block_item.html", item=item)
        toast = render_template("___toast.html", message="Item has been unblocked")
 
        db.commit()
        return f"""
            <template mix-target="#frm_item_unblock" mix-replace>{btn_block}</template>
            <template mix-target="#toast" mix-bottom>{toast}</template>
        """
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
            
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.put("/users")
def user_update():
    try:
        if not session.get("user"): 
            x.raise_custom_exception("please login", 401)

        user_pk = session.get("user").get("user_pk")
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_updated_at = int(time.time())

        db, cursor = x.db()
        # Update user in database
        cursor.execute("""
            UPDATE users
            SET user_name = %s, user_last_name = %s, user_email = %s, user_updated_at = %s
            WHERE user_pk = %s
        """, (user_name, user_last_name, user_email, user_updated_at, user_pk))
        
        if cursor.rowcount != 1: 
            x.raise_custom_exception("cannot update user", 401)
            
        # Fetch updated user data including roles
        cursor.execute("""
            SELECT 
                u.*,
                GROUP_CONCAT(r.role_name) as role_names
            FROM users u
            LEFT JOIN users_roles ur ON u.user_pk = ur.user_role_user_fk
            LEFT JOIN roles r ON ur.user_role_role_fk = r.role_pk
            WHERE u.user_pk = %s 
            GROUP BY u.user_pk
        """, (user_pk,))
        
        updated_user = cursor.fetchone()
        
        # Update session with new user data
        roles = updated_user["role_names"].split(",") if updated_user["role_names"] else []
        session["user"].update({
            "user_email": updated_user["user_email"],
            "user_name": updated_user["user_name"],
            "user_last_name": updated_user["user_last_name"],
            "user_avatar": updated_user["user_avatar"],
            "roles": roles,
            "active_role": roles[0] if roles else None
        })
        session.modified = True
        
        db.commit()
        return """<template>user updated</template>"""
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            return f"""<template mix-target="#toast" mix-bottom>{ex.message}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            if "users.user_email" in str(ex): 
                return "<template>email not available</template>", 400
            return "<template>System upgrading</template>", 500        
        return "<template>System under maintenance</template>", 500    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.put("/users/block/<user_pk>")
def user_block(user_pk):
    try:
        if not session.get("user") or session["user"].get("role") != "admin":
            raise x.CustomException("Unauthorized", 401)

        user_pk = x.validate_uuid4(user_pk)
        current_time = int(time.time())
        user = {
            "user_pk": user_pk,
            "user_blocked_at": current_time
        }

        db, cursor = x.db()
        
        # First check if user exists and is not already blocked
        cursor.execute('SELECT user_blocked_at FROM users WHERE user_pk = %s', (user_pk,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            raise x.CustomException("User not found", 404)
        
        # Update user block status
        cursor.execute("""
            UPDATE users 
            SET user_blocked_at = %s, 
                user_updated_at = %s 
            WHERE user_pk = %s
        """, (current_time, current_time, user_pk))
        
        if cursor.rowcount != 1:
            raise x.CustomException("Cannot block user", 400)

        # Get user details for email notification
        cursor.execute('SELECT user_name, user_email FROM users WHERE user_pk = %s', (user_pk,))
        user_data = cursor.fetchone()
        
        if user_data:
            # Send email notification
            x.send_user_blocked_email(user_data['user_email'], user_data['user_name'])
            
            # Return both button update and email confirmation toast
            btn_unblock = render_template("___btn_unblock_user.html", user=user)
            toast = render_template("___toast.html", message=f"Notification email sent to {user_data['user_name']}")
            
            db.commit()
            return f"""
                <template mix-target="#frm_user_block_{user_pk}" mix-replace>{btn_unblock}</template>
                <template mix-target="#toast" mix-bottom>{toast}</template>
            """

        db.commit()
        btn_unblock = render_template("___btn_unblock_user.html", user=user)
        return f"""<template mix-target="#frm_user_block_{user_pk}" mix-replace>{btn_unblock}</template>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.put("/users/unblock/<user_pk>")
def user_unblock(user_pk):
    try:
        if not session.get("user") or session["user"].get("role") != "admin":
            raise x.CustomException("Unauthorized", 401)

        user_pk = x.validate_uuid4(user_pk)
        user_blocked_at = 0
        user = {
            "user_pk": user_pk,
            "user_blocked_at": user_blocked_at
        }

        db, cursor = x.db()
        
        # First check if user exists and is blocked
        cursor.execute('SELECT user_blocked_at FROM users WHERE user_pk = %s', (user_pk,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            raise x.CustomException("User not found", 404)
            
        if existing_user['user_blocked_at'] == 0:
            raise x.CustomException("User is already unblocked", 400)

        cursor.execute("""
            UPDATE users 
            SET user_blocked_at = %s,
                user_updated_at = %s
            WHERE user_pk = %s
        """, (user_blocked_at, int(time.time()), user_pk))
 
        btn_block = render_template("___btn_block_user.html", user=user)
        toast = render_template("___toast.html", message="User has been unblocked")
 
        db.commit()
        return f"""
            <template mix-target="#frm_user_unblock_{user_pk}" mix-replace>{btn_block}</template>
            <template mix-target="#toast" mix-bottom>{toast}</template>
        """
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
            
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.put("/users/profile")
def update_profile():
    try:
        if not session.get("user"):
            raise x.CustomException("Please login", 401)

        user_pk = session.get("user").get("user_pk")
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_email()
        
        db, cursor = x.db()
        
        # Check if email exists for any other user
        cursor.execute("""
            SELECT user_pk FROM users 
            WHERE user_email = %s 
            AND user_pk != %s 
            AND user_deleted_at = 0
        """, (user_email, user_pk))
        
        if cursor.fetchone():
            raise x.CustomException("Email already exists", 400)
        
        # Handle avatar upload if provided
        avatar_filename = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                if not x.allowed_file(file.filename):
                    raise x.CustomException("Invalid file type", 400)
                avatar_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                file.save(os.path.join(x.UPLOAD_AVATAR_FOLDER, avatar_filename))

        # Update user info
        if avatar_filename:
            cursor.execute("""
                UPDATE users 
                SET user_name = %s, user_last_name = %s, 
                    user_email = %s, user_avatar = %s, 
                    user_updated_at = %s
                WHERE user_pk = %s
            """, (user_name, user_last_name, user_email, 
                  avatar_filename, int(time.time()), user_pk))
        else:
            cursor.execute("""
                UPDATE users 
                SET user_name = %s, user_last_name = %s, 
                    user_email = %s, user_updated_at = %s
                WHERE user_pk = %s
            """, (user_name, user_last_name, user_email, 
                  int(time.time()), user_pk))

        if cursor.rowcount != 1:
            raise x.CustomException("Could not update profile", 400)

        # Update session data
        session["user"].update({
            "user_name": user_name,
            "user_last_name": user_last_name,
            "user_email": user_email
        })
        if avatar_filename:
            session["user"]["user_avatar"] = avatar_filename

        db.commit()
        toast = render_template("___toast.html", message="Profile updated successfully")
        return f"""<template mix-target="#toast">{toast}</template>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            if "users.user_email" in str(ex):
                toast = render_template("___toast.html", message="Email already exists")
                return f"""<template mix-target="#toast">{toast}</template>""", 400
            toast = render_template("___toast.html", message="System error")
            return f"""<template mix-target="#toast">{toast}</template>""", 500
        return """<template mix-target="#toast">System error</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
        

@app.put("/users/delete")
def delete_account():
    try:
        if not session.get("user"):
            raise x.CustomException("Please login", 401)

        password = x.validate_password()
        user_pk = session.get("user").get("user_pk")
        user_email = session.get("user").get("user_email")

        db, cursor = x.db()
        
        # Verify password
        cursor.execute("SELECT user_password FROM users WHERE user_pk = %s", (user_pk,))
        user = cursor.fetchone()
        if not user or not check_password_hash(user["user_password"], password):
            raise x.CustomException("Invalid password", 401)

        # Soft delete user
        deleted_at = int(time.time())
        cursor.execute("""
            UPDATE users 
            SET user_deleted_at = %s
            WHERE user_pk = %s
        """, (deleted_at, user_pk))

        if cursor.rowcount != 1:
            raise x.CustomException("Could not delete account", 400)

        # Send deletion confirmation email
        x.send_account_deletion_email(user_email)

        db.commit()
        session.clear()
        
        return """
            <template mix-redirect="/login?message=Account+deleted+successfully"></template>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast">{ex.message}</template>""", ex.code
        return """<template mix-target="#toast">System error</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()





##############################
##############################
##############################

def _________BRIDGE_________(): pass

##############################
##############################
##############################

##############################

@app.post("/cart/add")
def add_to_cart():
    try:

        # Get item details with detailed logging
        item_pk = request.form.get('item_pk')
        item_title = request.form.get('item_title')
        item_price = request.form.get('item_price')

        # Log received values
        ic("Received values:")
        ic({
            "item_pk": item_pk,
            "item_title": item_title,
            "item_price": item_price
        })

        # Validate inputs with specific error messages
        if not item_pk:
            return {"error": "Missing item_pk"}, 400
        if not item_title:
            return {"error": "Missing item_title"}, 400
        if not item_price:
            return {"error": "Missing item_price"}, 400

        db, cursor = x.db()
        
        # Get the first image (image_order = 0) for this item
        cursor.execute("""
            SELECT image_filename 
            FROM item_images 
            WHERE image_item_fk = %s 
            ORDER BY image_order ASC 
            LIMIT 1
        """, (item_pk,))
        image_result = cursor.fetchone()
        
        if not image_result:
            toast = render_template("___toast.html", message="No image found for item")
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
            
        item_image = image_result['image_filename']

        # Get restaurant name
        cursor.execute("SELECT restaurant_name FROM restaurants WHERE restaurant_pk = (SELECT item_restaurant_fk FROM items WHERE item_pk = %s)", (item_pk,))
        restaurant_result = cursor.fetchone()
        item_restaurant = restaurant_result['restaurant_name'] if restaurant_result else 'Unknown Restaurant'

        # Get existing cart from cookie
        cart_cookie = request.cookies.get('cart', '[]')
        cart = json.loads(cart_cookie)

        # Generate a unique cart item ID
        cart_item_id = str(uuid.uuid4())

        # Add new item to cart
        new_item = {
            'cart_item_id': cart_item_id,
            'item_pk': item_pk,
            'item_title': item_title,
            'item_price': float(item_price),
            'item_image': item_image,
            'item_restaurant': item_restaurant
        }
        cart.append(new_item)

        # Prepare response with updated cart cookie
        response_html = f"""
        <template mix-target="#cart">{render_template("__cart_items.html", cart=cart)}</template>
        <template mix-target="#cart-count">{len(cart)}</template>
        <template mix-target="#cart-total">{sum(float(item['item_price']) for item in cart):.2f}</template>
        <template mix-target="#toast" mix-bottom>{render_template("___toast.html", message=f"{item_title} added to cart")}</template>
        """

        # Create response with cookie
        response = make_response(response_html)
        response.set_cookie('cart', json.dumps(cart), max_age=86400*7)  # 7 days
        return response

    except Exception as ex:
        ic("Error in add_to_cart:")
        ic(ex)
        ic("Request form data:", request.form)
        toast = render_template("___toast.html", message="Error adding to cart")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/cart/remove")
def remove_from_cart():
    try:

        cart_item_id = request.form.get('cart_item_id')
        ic(f"Attempting to remove cart item with ID: {cart_item_id}")

        # Get existing cart from cookie
        cart_cookie = request.cookies.get('cart')
        
        ic(f"Current cart cookie: {cart_cookie}")
        
        cart = json.loads(cart_cookie) if cart_cookie else []
        
        # Debugging: print out all cart item IDs
        ic("Cart item IDs before removal:")
        for item in cart:
            ic(item.get('cart_item_id'))
        
        # Remove the item with the matching cart_item_id
        cart = [item for item in cart if item.get('cart_item_id') != cart_item_id]
        
        ic(f"Cart length after removal: {len(cart)}")

        # Prepare response with updated cart
        response_html = f"""
        <template mix-target="#cart">{render_template("__cart_items.html", cart=cart)}</template>
        <template mix-target="#cart-count">{len(cart)}</template>
        <template mix-target="#cart-total">{sum(float(item['item_price']) for item in cart):.2f}</template>
        """

        # Create response with cookie
        response = make_response(response_html)
        response.set_cookie('cart', json.dumps(cart), max_age=86400*7)  # 7 days
        return response

    except Exception as ex:
        ic(f"Error in remove_from_cart: {ex}")
        toast = render_template("___toast.html", message="Error removing from cart")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500


##############################
@app.template_filter('from_json')
def from_json(value):
    """
    Safely parse JSON and ensure cart_item_id
    
    :param value: JSON string
    :return: Parsed JSON or empty list
    """
    if not value:
        return []
    
    try:
        parsed = json.loads(value)
        # Add cart_item_id to existing items if not present
        for item in parsed:
            if 'cart_item_id' not in item:
                item['cart_item_id'] = str(uuid.uuid4())
        return parsed
    except (TypeError, json.JSONDecodeError):
        return []
    
@app.template_filter('cart_total')
def cart_total_filter(cart):
    """
    Calculate cart total safely
    
    :param cart: List of cart items or None
    :return: Total cart value
    """
    if not cart:
        return 0.0
    
    try:
        return sum(float(item.get('item_price', 0)) for item in cart)
    except (TypeError, ValueError):
        return 0.0


##############################
@app.get("/verify/<verification_key>")
@x.no_cache
def verify(verification_key):
    try:
        ic(verification_key)
        verification_key = x.validate_uuid4(verification_key)
        verified_at = int(time.time())

        db, cursor = x.db()
        
        # Check user verification
        q_user = """ UPDATE users 
                     SET user_verified_at = %s 
                     WHERE user_verification_key = %s 
                     AND user_verified_at = 0"""
        cursor.execute(q_user, (verified_at, verification_key))
        
        # If no user was updated, try restaurant
        if cursor.rowcount == 0:
            q_restaurant = """ UPDATE restaurants 
                               SET restaurant_verified_at = %s 
                               WHERE restaurant_verification_key = %s 
                               AND restaurant_verified_at = 0"""
            cursor.execute(q_restaurant, (verified_at, verification_key))
            
            # If still no rows updated, raise an exception
            if cursor.rowcount != 1:
                x.raise_custom_exception("Invalid or already verified verification key", 400)
            
            # If restaurant verification is successful
            db.commit()
            return redirect(url_for("view_login", message="Restaurant verified, please login"))
        
        # If user verification is successful
        db.commit()
        return redirect(url_for("view_login", message="Your email has been verified, please login"))

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        # Handle specific exceptions
        if isinstance(ex, x.CustomException): 
            return ex.message, ex.code    
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "Database under maintenance", 500        
        
        return "System under maintenance", 500  
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    

@app.get("/restaurant/items/new")
def get_new_item_form():
    try:
        if not session.get("user") or "restaurant" not in session["user"]["roles"]:
            raise x.CustomException("Unauthorized", 401)
            
        return f"""
        <template mix-target="#dialog-container">
            {render_template("__add_item_form.html", x=x)}
        </template>
        """
    except Exception as ex:
        ic(ex)
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast">{ex.message}</template>""", ex.code
        return """<template mix-target="#toast">System error</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/restaurant/items/<item_pk>/edit")
def get_edit_item_data(item_pk):
    try:
        if not session.get("user") or "restaurant" not in session["user"]["roles"]:
            raise x.CustomException("Unauthorized", 401)
            
        db, cursor = x.db()
        cursor.execute("""
            SELECT * FROM items 
            WHERE item_pk = %s 
            AND item_restaurant_fk = %s
            AND item_deleted_at = 0
        """, (item_pk, session["user"]["restaurant"]["restaurant_pk"]))
        item = cursor.fetchone()
        
        if not item:
            raise x.CustomException("Item not found", 404)
            
        # Fetch images for the item
        cursor.execute("""
            SELECT * FROM item_images 
            WHERE image_item_fk = %s 
            ORDER BY image_order
        """, (item_pk,))
        item['images'] = cursor.fetchall()

        return f"""
        <template mix-target="#dialog-container">
            {render_template("__edit_item_form.html", 
                           title="Edit Item",
                           item=item,
                           x=x)}
        </template>
        """
    except Exception as ex:
        ic(ex)
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast">{ex.message}</template>""", ex.code
        return """<template mix-target="#toast">System error</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.post("/restaurant/items/<item_pk>/images")
def add_item_images(item_pk):
    try:
        if not session.get("user") or "restaurant" not in session["user"]["roles"]:
            raise x.CustomException("Unauthorized", 401)
            
        # Get uploaded files
        files = request.files.getlist('item_images[]')
        
        db, cursor = x.db()
        
        # Get current max order
        cursor.execute("""
            SELECT COALESCE(MAX(image_order), 0) as max_order 
            FROM item_images 
            WHERE image_item_fk = %s
        """, (item_pk,))
        current_max_order = cursor.fetchone()['max_order']
        
        # Save each image
        for i, file in enumerate(files, start=1):
            if file and x.allowed_file(file.filename):
                # Generate unique filename
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                
                # Save file
                file.save(os.path.join(x.UPLOAD_ITEM_FOLDER, filename))
                
                # Save to database
                cursor.execute("""
                    INSERT INTO item_images (
                        image_pk, image_item_fk, image_filename, 
                        image_order, image_created_at
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    item_pk,
                    filename,
                    current_max_order + i,
                    int(time.time())
                ))
        
        db.commit()
        
        # Return updated image grid
        cursor.execute("""
            SELECT * FROM item_images 
            WHERE image_item_fk = %s 
            ORDER BY image_order
        """, (item_pk,))
        images = cursor.fetchall()
        
        return render_template("__image_grid.html", images=images)
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            return f"""<template mix-target="#toast">{ex.message}</template>""", ex.code
        return """<template mix-target="#toast">System error</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()





##############################



