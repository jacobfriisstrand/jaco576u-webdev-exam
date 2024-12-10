import x
import uuid
import time
import random
import json
import constants
from werkzeug.security import generate_password_hash
from faker import Faker

fake = Faker()

from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)

db, cursor = x.db()

def insert_user(user):       
    user["user_password_reset_key"] = None
    user["user_password_reset_expires_at"] = None
    
    q = f"""
        INSERT INTO users
        VALUES (%s, %s ,%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s, %s, %s)        
        """
    values = tuple(user.values())
    cursor.execute(q, values)

# function to insert restaurant
def insert_restaurant(restaurant):
    q = """
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
    """
    values = (
        restaurant["restaurant_pk"],
        restaurant["restaurant_owner_fk"],
        restaurant["restaurant_name"],
        restaurant["restaurant_email"],
        restaurant["restaurant_catchphrase"],
        restaurant["restaurant_description"],
        restaurant["restaurant_rating"],
        restaurant["restaurant_total_ratings"],
        restaurant["restaurant_price_level"],
        restaurant["restaurant_estimated_delivery_time"],
        restaurant["restaurant_delivery_fee"],
        restaurant["restaurant_minimum_order"],
        restaurant["restaurant_address"],
        restaurant["restaurant_lat"],
        restaurant["restaurant_long"],
        restaurant["restaurant_image"],
        restaurant["restaurant_cuisine_types"],
        restaurant["restaurant_features"],
        restaurant["restaurant_created_at"],
        restaurant["restaurant_deleted_at"],
        restaurant["restaurant_blocked_at"],
        restaurant["restaurant_updated_at"],
        restaurant["restaurant_verified_at"]
    )
    cursor.execute(q, values)

try:
    ##############################
    # Drop tables in reverse order of dependency
    cursor.execute("DROP TABLE IF EXISTS item_images")
    cursor.execute("DROP TABLE IF EXISTS items")
    cursor.execute("DROP TABLE IF EXISTS restaurants")
    cursor.execute("DROP TABLE IF EXISTS users_roles")
    cursor.execute("DROP TABLE IF EXISTS roles")
    cursor.execute("DROP TABLE IF EXISTS users")
    
    ##############################
    # Create roles table first
    q = """
        CREATE TABLE roles (
            role_pk CHAR(36),
            role_name VARCHAR(10) NOT NULL UNIQUE,
            PRIMARY KEY(role_pk)
        );
        """
    cursor.execute(q)

    # Insert roles
    q = f"""
        INSERT INTO roles (role_pk, role_name)
        VALUES 
        ("{x.ADMIN_ROLE_PK}", "admin"), 
        ("{x.CUSTOMER_ROLE_PK}", "customer"), 
        ("{x.PARTNER_ROLE_PK}", "partner"), 
        ("{x.RESTAURANT_ROLE_PK}", "restaurant")
        """
    cursor.execute(q)

    ##############################
    # Create users table
    q = """
       CREATE TABLE users (
            user_pk CHAR(36),
            user_name VARCHAR(20) NOT NULL,
            user_last_name VARCHAR(20) NOT NULL,
            user_email VARCHAR(100) NOT NULL UNIQUE,
            user_password VARCHAR(255) NOT NULL,
            user_avatar VARCHAR(50),
            user_created_at INTEGER UNSIGNED,
            user_deleted_at INTEGER UNSIGNED,
            user_blocked_at INTEGER UNSIGNED,
            user_updated_at INTEGER UNSIGNED,
            user_verified_at INTEGER UNSIGNED,
            user_verification_key CHAR(36),
            user_password_reset_key VARCHAR(255),
            user_password_reset_expires_at BIGINT,
            PRIMARY KEY(user_pk)
        )
        """        
    cursor.execute(q)

    ##############################
    # Create users_roles table with cascade
    q = """
        CREATE TABLE users_roles (
            user_role_user_fk CHAR(36),
            user_role_role_fk CHAR(36),
            PRIMARY KEY(user_role_user_fk, user_role_role_fk),
            FOREIGN KEY (user_role_user_fk) REFERENCES users(user_pk) ON DELETE CASCADE,
            FOREIGN KEY (user_role_role_fk) REFERENCES roles(role_pk) ON DELETE CASCADE
        )
        """
    cursor.execute(q)

    ##############################
    # Create restaurants table with cascade
    q = """
        CREATE TABLE restaurants (
            restaurant_pk CHAR(36),
            restaurant_owner_fk CHAR(36),
            restaurant_name VARCHAR(50) NOT NULL,
            restaurant_email VARCHAR(100) NOT NULL UNIQUE,
            restaurant_catchphrase VARCHAR(50),
            restaurant_description VARCHAR(255),
            restaurant_rating DECIMAL(2,1),
            restaurant_total_ratings INTEGER UNSIGNED,
            restaurant_price_level VARCHAR(4),
            restaurant_estimated_delivery_time VARCHAR(20),
            restaurant_delivery_fee INTEGER UNSIGNED,
            restaurant_minimum_order INTEGER UNSIGNED,
            restaurant_address VARCHAR(100),
            restaurant_lat DECIMAL(12,6),
            restaurant_long DECIMAL(12,6),
            restaurant_image VARCHAR(50),
            restaurant_cuisine_types VARCHAR(100),
            restaurant_features VARCHAR(255),
            restaurant_created_at INTEGER UNSIGNED,
            restaurant_deleted_at INTEGER UNSIGNED,
            restaurant_blocked_at INTEGER UNSIGNED,
            restaurant_updated_at INTEGER UNSIGNED,
            restaurant_verified_at INTEGER UNSIGNED,
            PRIMARY KEY(restaurant_pk),
            FOREIGN KEY (restaurant_owner_fk) REFERENCES users(user_pk) ON DELETE CASCADE
        )
    """
    cursor.execute(q)

    ##############################
    # Create items table with cascade
    q = """
        CREATE TABLE items (
            item_pk CHAR(36),
            item_restaurant_fk CHAR(36),
            item_title VARCHAR(50) NOT NULL,
            item_desc VARCHAR(255),
            item_price DECIMAL(5,2) NOT NULL,
            item_created_at INTEGER UNSIGNED,
            item_deleted_at INTEGER UNSIGNED,
            item_updated_at INTEGER UNSIGNED,
            item_blocked_at INTEGER UNSIGNED,
            PRIMARY KEY(item_pk),
            FOREIGN KEY (item_restaurant_fk) REFERENCES restaurants(restaurant_pk) ON DELETE CASCADE
        )
    """
    cursor.execute(q)

    ##############################
    # Create item_images table with cascade
    q = """
        CREATE TABLE item_images (
            image_pk CHAR(36),
            image_item_fk CHAR(36),
            image_filename VARCHAR(255) NOT NULL,
            image_order INTEGER NOT NULL,
            image_created_at INTEGER UNSIGNED,
            PRIMARY KEY(image_pk),
            FOREIGN KEY (image_item_fk) REFERENCES items(item_pk) ON DELETE CASCADE
        )
    """
    cursor.execute(q)

    ############################## 
    # Create admin user
    user_pk = str(uuid.uuid4())
    user = {
        "user_pk": user_pk,
        "user_name": "Jacob",
        "user_last_name": "Friis",
        "user_email": "admin@exam.com",
        "user_password": generate_password_hash("password"),
        "user_avatar": "image_10.jpg",
        "user_created_at": int(time.time()),
        "user_deleted_at": 0,
        "user_blocked_at": 0,
        "user_updated_at": 0,
        "user_verified_at": int(time.time()),
        "user_verification_key": str(uuid.uuid4()) 
    }            
    insert_user(user)
    cursor.execute("""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
        VALUES (%s, %s)
    """, (user_pk, x.ADMIN_ROLE_PK))

    ############################## 
    # Create single customer
    user_pk = str(uuid.uuid4())
    user = {
        "user_pk": user_pk,
        "user_name": "Customer",
        "user_last_name": "Test",
        "user_email": "customer@exam.com",
        "user_password": generate_password_hash("password"),
        "user_avatar": "image_1.jpg",
        "user_created_at": int(time.time()),
        "user_deleted_at": 0,
        "user_blocked_at": 0,
        "user_updated_at": 0,
        "user_verified_at": int(time.time()),
        "user_verification_key": str(uuid.uuid4())
    }
    insert_user(user)
    cursor.execute("""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
        VALUES (%s, %s)
    """, (user_pk, x.CUSTOMER_ROLE_PK))

    ############################## 
    # Create single partner
    user_pk = str(uuid.uuid4())
    user = {
        "user_pk": user_pk,
        "user_name": "Partner",
        "user_last_name": "Test",
        "user_email": "partner@exam.com",
        "user_password": generate_password_hash("password"),
        "user_avatar": "image_2.jpg",
        "user_created_at": int(time.time()),
        "user_deleted_at": 0,
        "user_blocked_at": 0,
        "user_updated_at": 0,
        "user_verified_at": int(time.time()),
        "user_verification_key": str(uuid.uuid4())
    }
    insert_user(user)
    cursor.execute("""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
        VALUES (%s, %s)
    """, (user_pk, x.PARTNER_ROLE_PK))

    ############################## 
    # Create single restaurant owner
    restaurant_owner_pk = str(uuid.uuid4())
    user = {
        "user_pk": restaurant_owner_pk,
        "user_name": "Restaurant",
        "user_last_name": "Owner",
        "user_email": "restaurant@exam.com",
        "user_password": generate_password_hash("password"),
        "user_avatar": "image_3.jpg",
        "user_created_at": int(time.time()),
        "user_deleted_at": 0,
        "user_blocked_at": 0,
        "user_updated_at": 0,
        "user_verified_at": int(time.time()),
        "user_verification_key": str(uuid.uuid4())
    }
    insert_user(user)
    cursor.execute("""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
        VALUES (%s, %s)
    """, (restaurant_owner_pk, x.RESTAURANT_ROLE_PK))

    # Create restaurant for the restaurant owner
    restaurant_pk = str(uuid.uuid4())
    restaurant = {
        "restaurant_pk": restaurant_pk,
        "restaurant_owner_fk": restaurant_owner_pk,
        "restaurant_name": "Test Restaurant",
        "restaurant_email": "restaurant@exam.com",
        "restaurant_catchphrase": "The Best Food in Town",
        "restaurant_description": "A cozy restaurant serving delicious meals",
        "restaurant_rating": 4.5,
        "restaurant_total_ratings": 100,
        "restaurant_price_level": "$$",
        "restaurant_estimated_delivery_time": "30 min",
        "restaurant_delivery_fee": 50,
        "restaurant_minimum_order": 100,
        "restaurant_address": "Test Street 123",
        "restaurant_lat": 55.676098,
        "restaurant_long": 12.568337,
        "restaurant_image": "restaurant_1.jpg",
        "restaurant_cuisine_types": "Italian, Pizza",
        "restaurant_features": "Delivery, Takeaway, Vegetarian Friendly",
        "restaurant_created_at": int(time.time()),
        "restaurant_deleted_at": 0,
        "restaurant_blocked_at": 0,
        "restaurant_updated_at": 0,
        "restaurant_verified_at": int(time.time())
    }
    insert_restaurant(restaurant)

    # Add some items to the test restaurant
    test_items = [
        {
            "title": "Margherita Pizza", 
            "price": 89.00, 
            "desc": "Classic tomato and mozzarella",
            "images": [f"dish_{random.randint(1, 100)}.jpg", f"dish_{random.randint(1, 100)}.jpg", f"dish_{random.randint(1, 100)}.jpg"]
        },
        {
            "title": "Pasta Carbonara", 
            "price": 109.00, 
            "desc": "Creamy pasta with bacon",
            "images": [f"dish_{random.randint(1, 100)}.jpg", f"dish_{random.randint(1, 100)}.jpg", f"dish_{random.randint(1, 100)}.jpg"]
        },
        {
            "title": "Tiramisu", 
            "price": 59.00, 
            "desc": "Classic Italian dessert",
            "images": [f"dish_{random.randint(1, 100)}.jpg", f"dish_{random.randint(1, 100)}.jpg", f"dish_{random.randint(1, 100)}.jpg"]
        }
    ]

    for item in test_items:
        item_pk = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO items (
                item_pk, item_restaurant_fk, item_title, item_desc, item_price, item_created_at,
                item_deleted_at, item_updated_at, item_blocked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            item_pk,
            restaurant_pk,
            item["title"],
            item["desc"],
            item["price"],
            int(time.time()),
            0,
            0,
            0
        ))

        # Add exactly 3 images for each item with proper ordering
        for i, image_name in enumerate(item["images"]):
            cursor.execute("""
                INSERT INTO item_images (
                    image_pk, image_item_fk, image_filename,
                    image_order, image_created_at
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()),
                item_pk,
                image_name,
                i,  # 0 for main, 1 for secondary, 2 for additional
                int(time.time())
            ))

    ############################## 
    # Create 50 additional restaurants 
    for _ in range(50):
        # First create a user that will own the restaurant
        user_pk = str(uuid.uuid4())
        user = {
            "user_pk": user_pk,
            "user_name": fake.first_name(),
            "user_last_name": fake.last_name(),
            "user_email": fake.unique.email(),
            "user_password": generate_password_hash("password"),
            "user_avatar": f"image_{random.randint(1, 100)}.jpg",
            "user_created_at": int(time.time()),
            "user_deleted_at": 0,
            "user_blocked_at": 0,
            "user_updated_at": 0,
            "user_verified_at": int(time.time()),
            "user_verification_key": str(uuid.uuid4())
        }
        insert_user(user)

        # Assign restaurant role to user
        cursor.execute("""
            INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, x.RESTAURANT_ROLE_PK))

        # Create restaurant
        restaurant_pk = str(uuid.uuid4())
        restaurant = {
            "restaurant_pk": restaurant_pk,
            "restaurant_owner_fk": user_pk,
            "restaurant_name": random.choice(constants.restaurant_names),
            "restaurant_email": fake.unique.email(),
            "restaurant_catchphrase": random.choice(constants.catchphrases),
            "restaurant_description": random.choice(constants.descriptions),
            "restaurant_rating": round(random.uniform(3.0, 5.0) * 2) / 2,
            "restaurant_total_ratings": random.randint(10, 1000),
            "restaurant_price_level": random.choice(constants.price_levels),
            "restaurant_estimated_delivery_time": f"{random.randint(15, 60)} min",
            "restaurant_delivery_fee": random.randint(50, 70),
            "restaurant_minimum_order": random.randint(80, 100),
            "restaurant_address": fake.street_address(),
            "restaurant_lat": round(random.uniform(55.6, 55.7), 6),
            "restaurant_long": round(random.uniform(12.5, 12.6), 6),
            "restaurant_image": f"restaurant_{random.randint(1, 50)}.jpg",
            "restaurant_cuisine_types": ", ".join(random.sample(constants.cuisine_types, k=random.randint(1, 3))),
            "restaurant_features": ", ".join(random.sample(constants.features, k=random.randint(3, 8))),
            "restaurant_created_at": int(time.time()),
            "restaurant_deleted_at": 0,
            "restaurant_blocked_at": 0,
            "restaurant_updated_at": 0,
            "restaurant_verified_at": int(time.time())
        }
        insert_restaurant(restaurant)

        # Add unique dishes to the restaurant
        used_restaurant_dishes = set()
        for _ in range(random.randint(5, 20)):
            while True:
                dish = random.choice(constants.dishes)
                if dish not in used_restaurant_dishes:
                    used_restaurant_dishes.add(dish)
                    break

            item_pk = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO items (
                    item_pk, item_restaurant_fk, item_title, item_desc, item_price, item_created_at,
                    item_deleted_at, item_updated_at, item_blocked_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                item_pk,
                restaurant_pk,
                dish,
                fake.paragraph(nb_sentences=3),
                round(random.uniform(50, 150) * 2) / 2,
                int(time.time()),
                0,
                0,
                0
            ))

            # Add exactly 3 images for each item
            for i in range(3):
                cursor.execute("""
                    INSERT INTO item_images (
                        image_pk, image_item_fk, image_filename,
                        image_order, image_created_at
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    item_pk,
                    f"dish_{random.randint(1, 100)}.jpg",
                    i,  # 0 for main, 1 for secondary, 2 for additional
                    int(time.time())
                ))

    ############################## 
    # Create 50 additional customers
    for _ in range(50):
        user_pk = str(uuid.uuid4())
        user = {
            "user_pk": user_pk,
            "user_name": fake.first_name(),
            "user_last_name": fake.last_name(),
            "user_email": fake.unique.email(),
            "user_password": generate_password_hash("password"),
            "user_avatar": f"image_{random.randint(1, 100)}.jpg",
            "user_created_at": int(time.time()),
            "user_deleted_at": 0,
            "user_blocked_at": 0,
            "user_updated_at": 0,
            "user_verified_at": int(time.time()),
            "user_verification_key": str(uuid.uuid4())
        }
        insert_user(user)

        # Assign customer role
        cursor.execute("""
            INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, x.CUSTOMER_ROLE_PK))

    ############################## 
    # Create 50 additional partners
    for _ in range(50):
        user_pk = str(uuid.uuid4())
        user = {
            "user_pk": user_pk,
            "user_name": fake.first_name(),
            "user_last_name": fake.last_name(),
            "user_email": fake.unique.email(),
            "user_password": generate_password_hash("password"),
            "user_avatar": f"image_{random.randint(1, 100)}.jpg",
            "user_created_at": int(time.time()),
            "user_deleted_at": 0,
            "user_blocked_at": 0,
            "user_updated_at": 0,
            "user_verified_at": int(time.time()),
            "user_verification_key": str(uuid.uuid4())
        }
        insert_user(user)

        # Assign partner role
        cursor.execute("""
            INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, x.PARTNER_ROLE_PK))

    db.commit()

except Exception as ex:
    ic(ex)
    if "db" in locals(): db.rollback()

finally:
    if "cursor" in locals(): cursor.close()
    if "db" in locals(): db.close()