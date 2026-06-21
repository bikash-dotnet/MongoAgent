"""
sample_data_generator.py
Generate sample Airbnb listings data for MongoDB
"""

from pymongo import MongoClient
import random
import datetime
import urllib
from faker import Faker
import os
from dotenv import load_dotenv
import json

# Initialize Faker for realistic data
fake = Faker()

# Load environment variables
load_dotenv()

# MongoDB Connection
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["sample_airbnb"]
collection = db["listingsAndReviews"]

# Clear existing data (optional)
collection.delete_many({})

# Sample data definitions
PROPERTY_TYPES = [
    "House", "Apartment", "Condominium", "Townhouse", "Villa", 
    "Cabin", "Loft", "Bungalow", "Chalet", "Farm stay"
]

ROOM_TYPES = [
    "Entire home/apt", "Private room", "Shared room", "Hotel room"
]

BED_TYPES = [
    "Real Bed", "Futon", "Pull-out Sofa", "Airbed", "Couch", "King Bed", "Queen Bed"
]

AMENITIES = [
    "WiFi", "Kitchen", "TV", "Heating", "Air conditioning", 
    "Washer", "Dryer", "Free parking", "Pool", "Hot tub",
    "Gym", "Pets allowed", "Smoking allowed", "Breakfast", 
    "Dishwasher", "Microwave", "Oven", "Coffee maker",
    "Hair dryer", "Iron", "Laptop friendly workspace",
    "Garden", "Patio", "BBQ grill", "Beach access"
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte",
    "San Francisco", "Indianapolis", "Seattle", "Denver", "Washington",
    "Boston", "El Paso", "Nashville", "Detroit", "Oklahoma City",
    "Portland", "Las Vegas", "Memphis", "Louisville", "Baltimore",
    "Milwaukee", "Albuquerque", "Tucson", "Fresno", "Sacramento",
    "Kansas City", "Mesa", "Atlanta", "Omaha", "Colorado Springs"
]

COUNTRIES = ["United States", "Canada", "United Kingdom", "Australia", "Germany", "France", "Spain", "Italy"]

HOST_NAMES = [
    "John", "Sarah", "Michael", "Emma", "David", "Lisa", "James", "Maria",
    "Robert", "Jennifer", "William", "Patricia", "Thomas", "Linda", "Charles",
    "Susan", "Christopher", "Barbara", "Daniel", "Margaret", "Matthew", "Jessica"
]

# Generate review scores
def generate_review_scores():
    return {
        "review_scores_accuracy": round(random.uniform(4.0, 5.0), 2),
        "review_scores_cleanliness": round(random.uniform(4.0, 5.0), 2),
        "review_scores_checkin": round(random.uniform(4.0, 5.0), 2),
        "review_scores_communication": round(random.uniform(4.0, 5.0), 2),
        "review_scores_location": round(random.uniform(4.0, 5.0), 2),
        "review_scores_value": round(random.uniform(4.0, 5.0), 2),
        "review_scores_rating": round(random.uniform(4.0, 5.0), 2)
    }

# Generate a single listing document
def generate_listing(i):
    # Generate dates
    first_review = fake.date_time_between(start_date='-2y', end_date='-6m')
    last_review = fake.date_time_between(start_date='-6m', end_date='now')
    host_since = fake.date_time_between(start_date='-5y', end_date='-1y')
    last_scraped = fake.date_time_between(start_date='-1m', end_date='now')
    calendar_last_scraped = fake.date_time_between(start_date='-1m', end_date='now')
    
    # Generate address
    city = random.choice(CITIES)
    country = random.choice(COUNTRIES)
    latitude = random.uniform(33.0, 45.0)  # US latitudes
    longitude = random.uniform(-124.0, -71.0)  # US longitudes
    
    # Generate random amenities
    num_amenities = random.randint(5, 15)
    amenities = random.sample(AMENITIES, num_amenities)
    
    # Generate reviews
    num_reviews = random.randint(0, 50)
    reviews = []
    for _ in range(num_reviews):
        review_date = fake.date_time_between(start_date='-2y', end_date='now')
        reviews.append({
            "_id": fake.uuid4(),
            "date": review_date.isoformat(),
            "listing_id": f"listing_{i}",
            "reviewer_id": fake.uuid4(),
            "reviewer_name": fake.name(),
            "comments": fake.text(max_nb_chars=200)
        })
    
    # Generate images
    images = {
        "thumbnail_url": f"https://images.airbnb.com/thumb_{i}.jpg",
        "medium_url": f"https://images.airbnb.com/medium_{i}.jpg",
        "picture_url": f"https://images.airbnb.com/picture_{i}.jpg",
        "xl_picture_url": f"https://images.airbnb.com/xl_{i}.jpg"
    }
    
    # Generate the document
    doc = {
        "_id": f"listing_{i:04d}",
        "listing_url": f"https://www.airbnb.com/rooms/{i}",
        "name": f"{fake.bs().title()} {'Condo' if random.random() > 0.5 else 'Loft'}",
        "summary": fake.paragraph(nb_sentences=3),
        "space": fake.paragraph(nb_sentences=2),
        "description": fake.paragraph(nb_sentences=5),
        "neighborhood_overview": fake.paragraph(nb_sentences=2),
        "notes": fake.paragraph(nb_sentences=1),
        "transit": fake.paragraph(nb_sentences=1),
        "access": fake.paragraph(nb_sentences=1),
        "interaction": fake.paragraph(nb_sentences=1),
        "house_rules": fake.paragraph(nb_sentences=2),
        
        # Basic info
        "property_type": random.choice(PROPERTY_TYPES),
        "room_type": random.choice(ROOM_TYPES),
        "bed_type": random.choice(BED_TYPES),
        "minimum_nights": random.randint(1, 14),
        "maximum_nights": random.randint(30, 365),
        "cancellation_policy": random.choice(["flexible", "moderate", "strict"]),
        
        # Dates
        "last_scraped": last_scraped.isoformat(),
        "calendar_last_scraped": calendar_last_scraped.isoformat(),
        "first_review": first_review.isoformat(),
        "last_review": last_review.isoformat(),
        
        # Capacity
        "accommodates": random.randint(1, 12),
        "bedrooms": random.randint(0, 6),
        "beds": random.randint(1, 8),
        "bathrooms": random.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]),
        "number_of_reviews": num_reviews,
        
        # Financials
        "price": round(random.uniform(25, 500), 2),
        "security_deposit": round(random.uniform(50, 500), 2) if random.random() > 0.3 else None,
        "cleaning_fee": round(random.uniform(10, 100), 2) if random.random() > 0.4 else None,
        "extra_people": round(random.uniform(10, 50), 2),
        "guests_included": random.randint(1, 4),
        
        # Amenities
        "amenities": amenities,
        
        # Images
        "images": images,
        
        # Host info
        "host": {
            "host_id": fake.uuid4(),
            "host_url": f"https://www.airbnb.com/users/{random.randint(1000, 9999)}",
            "host_name": random.choice(HOST_NAMES),
            "host_since": host_since.isoformat(),
            "host_location": f"{city}, {country}",
            "host_about": fake.paragraph(nb_sentences=1),
            "host_response_time": random.choice(["within an hour", "within a few hours", "within a day"]),
            "host_response_rate": f"{random.randint(80, 100)}%",
            "host_acceptance_rate": f"{random.randint(70, 100)}%",
            "host_is_superhost": random.random() > 0.7,
            "host_thumbnail_url": f"https://images.airbnb.com/host_thumb_{i}.jpg",
            "host_picture_url": f"https://images.airbnb.com/host_picture_{i}.jpg",
            "host_neighbourhood": city,
            "host_listings_count": random.randint(1, 10),
            "host_total_listings_count": random.randint(1, 15),
            "host_verifications": ["email", "phone", "facebook", "google"] if random.random() > 0.5 else ["email", "phone"],
            "host_has_profile_pic": True,
            "host_identity_verified": random.random() > 0.3
        },
        
        # Address
        "address": {
            "street": fake.street_address(),
            "suburb": fake.city(),
            "government_area": fake.state(),
            "market": city,
            "country": country,
            "country_code": country[:2].upper(),
            "location": {
                "type": "Point",
                "coordinates": [longitude, latitude],
                "is_location_exact": random.random() > 0.3
            }
        },
        
        # Availability
        "availability": {
            "availability_30": random.randint(0, 30),
            "availability_60": random.randint(0, 60),
            "availability_90": random.randint(0, 90),
            "availability_365": random.randint(0, 365)
        },
        
        # Review scores
        "review_scores": generate_review_scores(),
        
        # Reviews array
        "reviews": reviews
    }
    
    return doc

# Generate sample data
def generate_sample_data(num_documents=50):
    """Generate sample Airbnb listings"""
    
    print(f"🗄️ Generating {num_documents} sample documents...")
    
    documents = []
    for i in range(num_documents):
        doc = generate_listing(i)
        documents.append(doc)
        
        # Print progress
        if (i + 1) % 10 == 0:
            print(f"Generated {i + 1} documents...")
    
    return documents

# Insert data into MongoDB
def insert_sample_data(documents):
    """Insert generated documents into MongoDB"""
    
    try:
        # Clear existing data
        count = collection.count_documents({})
        if count > 0:
            print(f"⚠️ Found {count} existing documents. Clearing...")
            collection.delete_many({})
        
        # Insert new data
        print("📥 Inserting documents into MongoDB...")
        result = collection.insert_many(documents)
        
        print(f"✅ Successfully inserted {len(result.inserted_ids)} documents!")
        return True
        
    except Exception as e:
        print(f"❌ Error inserting data: {str(e)}")
        return False

# Generate sample queries to test
def generate_test_queries():
    """Generate some sample queries for testing"""
    
    test_queries = [
        "Show me top 5 most expensive listings in New York",
        "Find all superhosts with more than 100 reviews",
        "Find listings with WiFi and a pool in Los Angeles",
        "What is the average price for entire home/apt in Paris?",
        "Find hosts with the most listings",
        "Show me properties with 5 bedrooms and 3+ bathrooms",
        "Find listings with rating above 4.5",
        "Show me listings under $200 in London",
        "Find the most reviewed listings",
        "Show me properties with the best location scores",
        "Find listings that allow pets and have a pool",
        "Show me hosts who joined Airbnb in the last year",
        "Find listings with flexible cancellation policy",
        "Show me the cheapest listings in San Francisco",
        "Find listings with exactly 2 bedrooms and 2 bathrooms"
    ]
    
    return test_queries

# Main execution
if __name__ == "__main__":
    print("🚀 Starting Sample Data Generation")
    print("=" * 50)
    
    # Generate sample data
    num_docs = 100  # Generate 100 sample listings
    documents = generate_sample_data(num_docs)
    
    # Insert into MongoDB
    success = insert_sample_data(documents)
    
    if success:
        print("\n📊 Sample Data Summary:")
        print(f"Total documents inserted: {collection.count_documents({})}")
        
        # Show some sample documents
        print("\n📋 First 3 Sample Listings:")
        for doc in collection.find().limit(3):
            print(f"\nName: {doc['name']}")
            print(f"Price: ${doc['price']}")
            print(f"Location: {doc['address']['market']}, {doc['address']['country']}")
            print(f"Room Type: {doc['room_type']}")
            print(f"Superhost: {doc['host']['host_is_superhost']}")
            print("---")
        
        # Show test queries
        print("\n💡 Sample Queries to Test:")
        test_queries = generate_test_queries()
        for i, query in enumerate(test_queries[:5], 1):
            print(f"{i}. {query}")
        
        print("\n✅ Sample data generation complete!")
        print("\n🔧 To test your app, try these commands:")
        print("streamlit run main.py")
        
    else:
        print("\n❌ Failed to generate sample data")